from sqlalchemy import Column, String, Float, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base

class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False)
    provider = Column(String, default="tuya")  # 'tuya' | 'ezviz'
    ip_address = Column(String, nullable=True)  # Nullable: EZVIZ dùng Cloud, không cần IP
    mac_address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Tuya-specific (nullable cho EZVIZ)
    device_id = Column(String, nullable=True)
    local_key = Column(String, nullable=True)
    version = Column(Float, default=3.3)
    
    device_type = Column(String, default="single")  # 'single', 'multi', 'camera'
    dps_mapping = Column(JSON, nullable=True)  # Tuya DPS: {"1": "Quạt", "2": "Đèn"}
    config_data = Column(JSON, nullable=True)  # Đa năng: EZVIZ {"username":"..","password":"..","region":".."}
