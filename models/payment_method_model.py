from datetime import datetime
from pydantic import BaseModel

'''Table payment_methods {
  id integer [primary key]
  name varchar [unique, not null]
}'''

class PaymentMethod(BaseModel):
    id: int
    name: str