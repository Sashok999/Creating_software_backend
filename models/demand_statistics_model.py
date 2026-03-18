from pydantic import BaseModel
from datetime import datetime

'''Table demand_statistics {
  id integer [primary key]
  resource_id integer
  date date
  bookings_count integer
  occupancy_rate float
}'''

class DemandStatistics(BaseModel):
    id: int
    resource_id: int
    date: datetime
    bookings_count: int
    occupancy_rate: float