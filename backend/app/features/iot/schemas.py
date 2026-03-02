from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
from uuid import UUID

class IoTDeviceBase(BaseModel):
    name: str = Field(..., max_length=100)
    provider: str = Field("tuya", pattern="^(tuya|ezviz)$")
    ip_address: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    device_id: Optional[str] = Field(None, max_length=100)
    local_key: Optional[str] = Field(None, max_length=100)
    version: Optional[float] = Field(3.3)
    device_type: str = Field("single", pattern="^(single|multi|camera)$")
    dps_mapping: Optional[Dict[str, str]] = Field(default_factory=dict)
    config_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider_fields(self):
        """Validate bắt buộc theo từng provider để bảo vệ Code cũ."""
        if self.provider == "tuya":
            if not self.device_id:
                raise ValueError("Tuya devices bắt buộc phải có 'device_id'.")
            if not self.local_key:
                raise ValueError("Tuya devices bắt buộc phải có 'local_key'.")
            if not self.ip_address:
                raise ValueError("Tuya devices bắt buộc phải có 'ip_address'.")
        elif self.provider == "ezviz":
            if not self.config_data or not self.config_data.get("username"):
                raise ValueError("EZVIZ config bắt buộc phải có 'username' trong config_data.")
            if not self.config_data.get("password"):
                raise ValueError("EZVIZ config bắt buộc phải có 'password' trong config_data.")
        return self

class IoTDeviceCreate(IoTDeviceBase):
    pass

class IoTDeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    provider: Optional[str] = Field(None, pattern="^(tuya|ezviz)$")
    ip_address: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    device_id: Optional[str] = Field(None, max_length=100)
    local_key: Optional[str] = Field(None, max_length=100)
    version: Optional[float] = None
    device_type: Optional[str] = Field(None, pattern="^(single|multi|camera)$")
    dps_mapping: Optional[Dict[str, str]] = None
    config_data: Optional[Dict[str, Any]] = None

class IoTDeviceResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    provider: str = "tuya"
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    is_active: bool = True
    device_id: Optional[str] = None
    local_key: Optional[str] = None
    version: Optional[float] = 3.3
    device_type: str = "single"
    dps_mapping: Optional[Dict[str, str]] = None
    config_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class IoTDeviceTestRequest(BaseModel):
    ip_address: str
    device_id: str
    local_key: str
    version: float
    device_type: str = "single"
