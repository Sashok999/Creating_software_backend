from datetime import datetime
from pydantic import BaseModel

'''Table bookings {
  id integer [primary key]
  user_id integer
  resource_id integer
  start_time timestamp
  end_time timestamp
  status varchar // CREATED, CONFIRMED, PAID, CANCELLED
  price decimal
  created_at timestamp
}'''

class Booking(BaseModel):
    id: int
    user_id: int
    resource_id: int
    start_time: datetime
    end_time: datetime
    status: str
    price: float
    created_at: datetime