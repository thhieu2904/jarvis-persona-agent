from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID

class IoTDeviceBase(BaseModel):
    name: str = Field(..., max_length=100)
    ip_address: str = Field(..., max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    device_id: str = Field(..., max_length=100)
    local_key: str = Field(..., max_length=100)
    version: float = Field(3.3)
    device_type: str = Field("single", pattern="^(single|multi)$")
    dps_mapping: Optional[Dict[str, str]] = Field(default_factory=dict)

class IoTDeviceCreate(IoTDeviceBase):
    pass

class IoTDeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    device_id: Optional[str] = Field(None, max_length=100)
    local_key: Optional[str] = Field(None, max_length=100)
    version: Optional[float] = None
    device_type: Optional[str] = Field(None, pattern="^(single|multi)$")
    dps_mapping: Optional[Dict[str, str]] = None

class IoTDeviceResponse(IoTDeviceBase):
    id: UUID
    user_id: UUID

    class Config:
        from_attributes = True

class IoTDeviceTestRequest(BaseModel):
    ip_address: str
    device_id: str
    local_key: str
    version: float
    device_type: str = "single"
