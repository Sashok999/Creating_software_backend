from datetime import datetime
from pydantic import BaseModel

'''Table transactions {
  id integer [primary key]
  payment_id integer
  status varchar
  gateway_response text
  created_at timestamp
}'''

class Transaction(BaseModel):
    id: int
    payment_id: int
    status: str
    gateway_response: str
    created_at: datetime