from sqlalchemy import Column, String, Float, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base

class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    mac_address = Column(String, nullable=True) # Lưu trữ để tự phục hồi IP
    is_active = Column(Boolean, default=True) # Trạng thái online/offline
    
    device_id = Column(String, nullable=False)
    local_key = Column(String, nullable=False)
    version = Column(Float, default=3.3)
    
    device_type = Column(String, default="single") # 'single' hoặc 'multi'
    dps_mapping = Column(JSON, nullable=True) # Ví dụ: {"1": "Quạt", "2": "Đèn"}
