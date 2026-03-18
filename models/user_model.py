from datetime import datetime
from pydantic import BaseModel

'''
Table users {
  id integer [primary key]
  email varchar [unique, not null]
  password_hash varchar [not null]
  name varchar
  surname varchar
  role varchar // admin, employee, client
  created_at timestamp
}'''


class User(BaseModel):
    id: int
    email: str
    password_hash: str
    name: str
    surname: str
    role: str
    created_at: datetime