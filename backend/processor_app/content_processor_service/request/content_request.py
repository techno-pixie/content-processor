from pydantic import BaseModel, Field

class ContentSubmissionRequest(BaseModel):
    content: str = Field(..., min_length=1, )
