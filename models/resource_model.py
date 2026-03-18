from datetime import datetime
from pydantic import BaseModel

'''Table resources {
  id integer [primary key]
  name varchar
  type varchar // room, desk, car
  description text
  base_price decimal
  is_active boolean
}'''

class Resource(BaseModel):
    id: int
    name: str
    type: str
    description: str
    base_price: float
    is_active: bool
