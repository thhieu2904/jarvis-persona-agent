from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class StudyMaterialResponse(BaseModel):
    id: str
    file_name: str
    file_url: str
    domain: str
    subject: Optional[str] = None
    processing_status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
