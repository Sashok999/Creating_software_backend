from datetime import datetime
from pydantic import BaseModel

'''Table audit_logs {
  id integer [primary key]
  user_id integer
  entity varchar // booking, payment, resource
  entity_id integer
  action varchar
  created_at timestamp
}'''

class AudLtLog(BaseModel):
    id: int
    user_id: int
    entity: str
    entity_id: str
    action: str
    created_at: datetime