from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ContentSubmissionResponse(BaseModel):
    id: str
    content: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True