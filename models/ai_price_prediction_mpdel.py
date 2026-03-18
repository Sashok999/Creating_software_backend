from pydantic import BaseModel
from datetime import datetime

'''Table ai_price_predictions {
  id integer [primary key]
  resource_id integer
  predicted_price decimal
  model_version varchar
  predicted_at timestamp
}'''

class AiPricePrediction(BaseModel):
    id: int
    resource_id: int
    predicted_price: float
    model_version: str
    predicted_at: datetime