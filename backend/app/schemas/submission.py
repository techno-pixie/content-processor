from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SubmissionCreate(BaseModel):
    content: str = Field(..., min_length=1, )


class SubmissionResponse(BaseModel):
    id: str
    content: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
