from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi import Request
from models.user_model import User
import dotenv
import os
import asyncio
import asyncpg
from contextlib import asynccontextmanager
from datetime import datetime, date
import bcrypt

'''
1. главная +
2. регистрация +
3. вход +
4. страцница резултата - юзер нажимает найти, с фронта тянет json, обрабатываю его, делаю запрос в бд, и соответственно снова обрабатываю и отправляю то что мне пришло отправляю на фронт в json
5. карочка недвижимости
6. профиль юзера
7. создание недвидимости
'''

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - создаем соединение при запуске
    app.state.con = await asyncpg.connect(dsn=os.getenv("DB_URL"), ssl="require")
    print("Connected to database")
    yield
    # Shutdown - закрываем соединение при остановке
    await app.state.con.close()
    print("Disconnected from database")

app = FastAPI(lifespan=lifespan)
dotenv.load_dotenv()
now = datetime.now()
templates = Jinja2Templates(directory="pages")


async def get_db():
    global con
    con = await asyncpg.connect(dsn=os.getenv("DB_URL"), ssl="require")
    print("Connected to database")

@app.get("/")
async def main(request: Request):
    return templates.TemplateResponse(request, "main.html")

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/search")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "search.html")
'''
{"name" : Алексей,
"surname": Иванов,
"email": ivanov@mail.ru,
"password": Poll123!
}'''

@app.post("/register")
async def check_register(request: Request):
    con = request.app.state.con
    data = await request.json()

    a = await con.fetch("SELECT email FROM users WHERE email = $1", data["email"])
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(data["password"].encode("utf8"), salt)
    if a:
        return {"message": "почта занята"}
    f = await con.execute("INSERT INTO users (email, password_hash, salt, name, surname, role, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                       data["email"], str(password_hash), str(salt), data["name"], data["surname"], '"user"', date.today())
    return {"message": 'ok'}



'''
{"email": ivan123ov@mail.ru,
"password": Poll123!
}'''
@app.post("/login")
async def check_login(request: Request):
    con = request.app.state.con
    data = await request.json()
    a = await con.fetch("SELECT email, password_hash FROM users WHERE email = $1", data["email"])
    if a == None:
        return {"message": "не существует"}

    print(len(a))
    if bcrypt.checkpw(data["password"].encode("utf8"), password_hash):
            return {"message": "разрешен вход"}
    else:
        return {"message": "неправильный логин и пароль"}


@app.post("/search")
async def search(request: Request):
    con = request.app.state.con

    try:
        data = await request.json()
    except Exception:
        data = {}

    conditions = ["r.is_active = TRUE"]
    params = []
    i = 1

    if data.get("location"):
        conditions.append(f"r.location ILIKE ${i}")
        params.append(f"%{data['location']}%")
        i += 1

    if data.get("type"):
        conditions.append(f"r.type = ${i}")
        params.append(data["type"])
        i += 1

    if data.get("date_from") and data.get("date_to"):
        conditions.append(f"""
            r.id NOT IN (
                SELECT resource_id FROM bookings
                WHERE status NOT IN ('CANCELLED')
                AND NOT (end_time <= ${i} OR start_time >= ${i+1})
            )
        """)
        params.append(data["date_from"])
        params.append(data["date_to"])
        i += 2

    where = "WHERE " + " AND ".join(conditions)

    rows = await con.fetch(
        f"""
        SELECT r.id, r.name, r.type, r.description,
               r.address, r.location, r.base_price
        FROM resources r
        {where}
        ORDER BY r.id
        LIMIT 50
        """,
        *params
    )

    return {"results": [dict(row) for row in rows]}

@app.get("/v0/version")
async def api_version():
     return {"version": app_version}

if __name__ == '__main__':
    asyncio.run(get_db())