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
4. страцница резултата
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



if __name__ == '__main__':
    asyncio.run(get_db())