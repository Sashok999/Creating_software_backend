from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi import Request
from models.user_model import User
import dotenv
import os
import asyncio
import asyncpg
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

app = FastAPI()
dotenv.load_dotenv()
templates = Jinja2Templates(directory="pages")

global con
async def get_db():
    con = await asyncpg.connect(dsn=os.getenv("DB_URL"), ssl="require")
    print("Connected to database")

@app.get("/")
async def main(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/register")
async def say_hello(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login")
async def say_hello(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

'''
{"name" : Алексей,
"surname": Иванов,
"email": ivanov@mail,ru,
"password": Poll123!,
"created_at": 2026-03-12
}'''

@app.post("/register")
async def check_register(user: User, request: Request):
    a = await con.fetch("SELECT email FROM users WHERE email = $1", user.email)
    if user.email in a:
        print('qq')
        return {"message": "почта занята"}
    f = await con.execute("INSERT INTO user (email, password_hash, full_name, role, created_at) VALUES ($1, $2, $3, $4, $5)", user.email, user.password, user.full_name, user.role, user.created_at)
    print('ready')
    return {"message": 'ok'}


if __name__ == '__main__':
    asyncio.run(get_db())