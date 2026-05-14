from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import dotenv, os, asyncpg
from contextlib import asynccontextmanager
from datetime import datetime, date
import bcrypt
from typing import Optional
from ai_router import ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.con = await asyncpg.connect(dsn=os.getenv("DB_URL"), ssl="require")
    print("Connected to database")
    yield
    await app.state.con.close()
    print("Disconnected from database")

#22
app = FastAPI(lifespan=lifespan)
dotenv.load_dotenv()

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "secret"),
                   session_cookie="rental_session", max_age=60 * 60 * 24 * 7)

os.makedirs("pages", exist_ok=True)
os.makedirs("static", exist_ok=True)
templates = Jinja2Templates(directory="pages")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(ai_router, prefix="/ai", tags=["AI"])

def get_current_user(request: Request) -> Optional[dict]:
    return request.session.get("user")


@app.get("/")
async def main(request: Request):
    con = request.app.state.con
    return templates.TemplateResponse(request, "main.html")


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.post("/register")
async def check_register(request: Request):
    con = request.app.state.con
    data = await request.json()
    existing = await con.fetchrow("SELECT email FROM users WHERE email = $1", data["email"])
    if existing:
        return {"message": "почта занята", "status": "error"}
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(data["password"].encode("utf8"), salt)
    await con.execute("""
                      INSERT INTO users (email, password_hash, salt, name, surname, role, created_at)
                      VALUES ($1, $2, $3, $4, $5, $6, $7)
                      """, data["email"], password_hash.decode('utf8'), salt.decode('utf8'), data["name"],
                      data["surname"], 'user', date.today())
    return {"message": "Регистрация успешна", "status": "success"}


@app.post("/login")
async def check_login(request: Request):
    con = request.app.state.con
    data = await request.json()
    user = await con.fetchrow("""SELECT id, email, password_hash, name, surname, role FROM users
                              WHERE email = $1""", data["email"])
    if not user:
        return {"message": "Пользователь не найден", "status": "error"}
    if bcrypt.checkpw(data["password"].encode("utf8"), user["password_hash"].encode('utf8')):
        request.session["user"] = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "surname": user["surname"],
            "role": user["role"]
        }
        return {"message": "Вход выполнен", "status": "success", "redirect": "/profile"}
    return {"message": "Неверный пароль", "status": "error"}


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/profile")
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    con = request.app.state.con
    user_info = await con.fetchrow("SELECT * FROM users WHERE id = $1", user["id"])

    my_properties = []
    if user_info["role"] in ["owner", "admin"]:
        my_properties = await con.fetch("""SELECT * FROM properties WHERE owner_id = $1 ORDER BY created_at DESC""", user["id"])

    my_bookings = await con.fetch("""SELECT b.*, p.title, p.images, p.address, p.city
                                  FROM bookings b JOIN properties p ON b.property_id = p.id
                                  WHERE b.user_id = $1
                                  ORDER BY b.created_at DESC LIMIT 10""", user["id"])

    favorites = await con.fetch("""
                                SELECT p.*, u.name as owner_name, u.surname as owner_surname
                                FROM favorites f
                                         JOIN properties p ON f.property_id = p.id
                                         JOIN users u ON p.owner_id = u.id
                                WHERE f.user_id = $1
                                ORDER BY f.created_at DESC
                                """, user["id"])

    return templates.TemplateResponse(request, "profile.html", {
        "user": user_info,
        "my_properties": my_properties,
        "my_bookings": my_bookings,
        "favorites": favorites
    })


@app.get("/properties/create")
async def create_property_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "create_property.html", {"user": user})


@app.post("/properties")
async def create_property(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    con = request.app.state.con
    data = await request.json()

    required = ["title", "property_type", "price", "address", "city"]
    if not all(field in data for field in required):
        return {"message": "Заполните все обязательные поля", "status": "error"}

    await con.execute("""
                      UPDATE users
                      SET role = 'owner'
                      WHERE id = $1
                        AND role = 'user'
                      """, user["id"])

    await con.execute("""
                      INSERT INTO properties (owner_id, title, description, property_type, price, price_type,
                                              rooms, area, floor, total_floors, address, city,
                                              latitude, longitude, images, amenities)
                      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                      """, user["id"], data["title"], data.get("description"),
                      data["property_type"], data["price"], data.get("price_type", "month"),
                      data.get("rooms"), data.get("area"), data.get("floor"), data.get("total_floors"),
                      data["address"], data["city"], data.get("latitude"), data.get("longitude"),
                      data.get("images", []), data.get("amenities", []))

    return {"message": "Объект создан", "status": "success"}


@app.get("/properties/{property_id}")
async def property_detail(request: Request, property_id: int):
    con = request.app.state.con
    prop = await con.fetchrow("""
                              SELECT p.*,
                                     u.name    as owner_name,
                                     u.surname as owner_surname,
                                     u.email   as owner_email,
                                     u.phone   as owner_phone
                              FROM properties p
                                       JOIN users u ON p.owner_id = u.id
                              WHERE p.id = $1
                              """, property_id)

    if not prop:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    reviews = await con.fetch("""
                              SELECT r.*, u.name, u.surname
                              FROM reviews r
                                       JOIN users u ON r.user_id = u.id
                              WHERE r.property_id = $1
                              ORDER BY r.created_at DESC
                              """, property_id)

    user = get_current_user(request)
    is_favorite = False
    if user:
        fav = await con.fetchrow("""
                                 SELECT id
                                 FROM favorites
                                 WHERE user_id = $1
                                   AND property_id = $2
                                 """, user["id"], property_id)
        is_favorite = fav is not None

    similar = await con.fetch("""
                              SELECT p.*, u.name as owner_name, u.surname as owner_surname
                              FROM properties p
                                       JOIN users u ON p.owner_id = u.id
                              WHERE p.property_type = $1
                                AND p.id != $2
                                AND p.is_available = TRUE
                                  LIMIT 4
                              """, prop["property_type"], property_id)

    return templates.TemplateResponse(request, "property_detail.html", {
        "property": prop,
        "reviews": reviews,
        "is_favorite": is_favorite,
        "similar_properties": similar,
        "user": user
    })


@app.post("/favorites/{property_id}")
async def add_to_favorites(request: Request, property_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    con = request.app.state.con
    await con.execute("""
                      INSERT INTO favorites (user_id, property_id)
                      VALUES ($1, $2) ON CONFLICT (user_id, property_id) DO NOTHING
                      """, user["id"], property_id)
    return {"message": "Добавлено в избранное", "status": "success"}


@app.delete("/favorites/{property_id}")
async def remove_from_favorites(request: Request, property_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    con = request.app.state.con
    await con.execute("""DELETE FROM favorites WHERE user_id = $1 AND property_id = $2""", user["id"], property_id)
    return {"message": "Удалено из избранного", "status": "success"}


@app.get("/search")
async def search_properties(
        request: Request,
        city: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        rooms: Optional[int] = None,
        check_in: Optional[str] = None,
        check_out: Optional[str] = None
):
    con = request.app.state.con
    query = """
            SELECT p.*, u.name as owner_name, u.surname as owner_surname
            FROM properties p
                     JOIN users u ON p.owner_id = u.id
            WHERE p.is_available = TRUE \
            """
    params, i = [], 1

    if city:
        query += f" AND p.city ILIKE ${i}"
        params.append(f"%{city}%")
        i += 1
    if property_type:
        query += f" AND p.property_type = ${i}"
        params.append(property_type)
        i += 1
    if min_price is not None:
        query += f" AND p.price >= ${i}"
        params.append(min_price)
        i += 1
    if max_price is not None:
        query += f" AND p.price <= ${i}"
        params.append(max_price)
        i += 1
    if rooms is not None:
        query += f" AND p.rooms >= ${i}"
        params.append(rooms)
        i += 1

    query += " ORDER BY p.created_at DESC"
    properties = await con.fetch(query, *params)

    if check_in and check_out:
        available = []
        for prop in properties:
            booked = await con.fetchrow("""
                                        SELECT id
                                        FROM bookings
                                        WHERE property_id = $1
                                          AND status != 'cancelled'
                AND (($2 BETWEEN check_in
                                          AND check_out)
                                           OR
                                            ($3 BETWEEN check_in
                                          AND check_out)
                                           OR
                                            (check_in BETWEEN $2
                                          AND $3))
                                        """, prop["id"], check_in, check_out)
            if not booked:
                available.append(prop)
        properties = available

    return templates.TemplateResponse(request, "search_results.html", {
        "properties": properties,
        "filters": {
            "city": city,
            "property_type": property_type,
            "min_price": min_price,
            "max_price": max_price,
            "rooms": rooms
        },
        "user": get_current_user(request)
    })


@app.post("/bookings")
async def create_booking(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    con = request.app.state.con
    data = await request.json()

    prop = await con.fetchrow("""
                              SELECT price, owner_id
                              FROM properties
                              WHERE id = $1 AND is_available = TRUE""", data["property_id"])

    if not prop:
        return {"message": "Объект недоступен", "status": "error"}

    booked = await con.fetchrow("""
                                SELECT id
                                FROM bookings
                                WHERE property_id = $1
                                  AND status != 'cancelled'
        AND (($2 BETWEEN check_in
                                  AND check_out)
                                   OR
                                    ($3 BETWEEN check_in
                                  AND check_out)
                                   OR
                                    (check_in BETWEEN $2
                                  AND $3))
                                """, data["property_id"], data["check_in"], data["check_out"])

    if booked:
        return {"message": "Объект уже забронирован", "status": "error"}

    check_in = datetime.strptime(data["check_in"], "%Y-%m-%d").date()
    check_out = datetime.strptime(data["check_out"], "%Y-%m-%d").date()
    days = (check_out - check_in).days

    if days <= 0:
        return {"message": "Дата выезда должна быть позже даты заезда", "status": "error"}

    total_price = days * float(prop["price"])

    await con.execute("""
                      INSERT INTO bookings (property_id, user_id, check_in, check_out,
                                            total_price, guests_count, special_requests)
                      VALUES ($1, $2, $3, $4, $5, $6, $7)
                      """, data["property_id"], user["id"], check_in, check_out,
                      total_price, data.get("guests_count", 1), data.get("special_requests"))

    return {"message": "Бронирование создано", "status": "success"}


@app.get("/my-bookings")
async def my_bookings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    con = request.app.state.con

    upcoming = await con.fetch("""
                               SELECT b.*,
                                      p.title,
                                      p.images,
                                      p.address,
                                      p.city,
                                      u.name    as owner_name,
                                      u.surname as owner_surname
                               FROM bookings b
                                        JOIN properties p ON b.property_id = p.id
                                        JOIN users u ON p.owner_id = u.id
                               WHERE b.user_id = $1
                                 AND b.check_out >= CURRENT_DATE
                                 AND b.status IN ('pending', 'confirmed')
                               ORDER BY b.check_in ASC
                               """, user["id"])

    past = await con.fetch("""
                           SELECT b.*,
                                  p.title,
                                  p.images,
                                  p.address,
                                  p.city,
                                  u.name    as owner_name,
                                  u.surname as owner_surname
                           FROM bookings b
                                    JOIN properties p ON b.property_id = p.id
                                    JOIN users u ON p.owner_id = u.id
                           WHERE b.user_id = $1
                             AND (b.check_out < CURRENT_DATE OR b.status IN ('cancelled', 'completed'))
                           ORDER BY b.created_at DESC LIMIT 20
                           """, user["id"])

    return templates.TemplateResponse(request, "my_bookings.html", {
        "upcoming_bookings": upcoming,
        "past_bookings": past,
        "user": user
    })


@app.post("/reviews")
async def create_review(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    con = request.app.state.con
    data = await request.json()

    booking = await con.fetchrow("""
                                 SELECT id
                                 FROM bookings
                                 WHERE user_id = $1
                                   AND property_id = $2
                                   AND status = 'completed'
                                 """, user["id"], data["property_id"])

    if not booking:
        return {"message": "Отзыв можно оставить только после завершения бронирования", "status": "error"}

    existing = await con.fetchrow("""
                                  SELECT id
                                  FROM reviews
                                  WHERE user_id = $1
                                    AND property_id = $2
                                  """, user["id"], data["property_id"])

    if existing:
        return {"message": "Вы уже оставляли отзыв", "status": "error"}

    await con.execute("""
                      INSERT INTO reviews (property_id, user_id, rating, comment)
                      VALUES ($1, $2, $3, $4)
                      """, data["property_id"], user["id"], data["rating"], data.get("comment"))

    return {"message": "Отзыв добавлен", "status": "success"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)