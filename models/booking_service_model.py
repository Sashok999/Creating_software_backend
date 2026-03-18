from pydantic import BaseModel
from datetime import datetime

'''Table booking_services {
  id integer primary key
  booking_id integer
  service_id integer
  quantity integer
  total_price decimal
}
'''

class BookingService(BaseModel):
    id: int
    booking_id: int
    service_id: int
    quantity: int
    total_price: float