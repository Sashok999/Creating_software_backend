from datetime import datetime
from pydantic import BaseModel

'''Table services {
  id integer [primary key]
  name varchar
  description text
  price decimal
  is_active boolean
}'''

class Service(BaseModel):
    id: int
    name: str
    description: str
    price: float
    is_active: bool