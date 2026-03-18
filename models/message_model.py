from pydantic import BaseModel
from datetime import datetime

'''Table messenges {
  id integer [primary key]
  id_sender integer
  id_recipient integer
  text_message text
  created_at timestamp
}
'''

class Message(BaseModel):
    id: int
    id_sender: int
    id_recipient: int
    text_message: str
    created_at: datetime