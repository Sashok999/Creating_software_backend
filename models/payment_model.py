from datetime import datetime
from pydantic import BaseModel

'''
Table payments {
  id integer [primary key]
  booking_id integer
  method_id integer
  amount decimal
  status varchar // PENDING, SUCCESS, FAILED
  paid_at timestamp
}'''



class Payment(BaseModel):
    id: int
    booking_id: int
    method_id: int
    amount: float
    status: str
    paid_at: datetime