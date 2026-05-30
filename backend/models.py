from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    files = relationship("UploadedFile", back_populates="owner")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    filename = Column(String)
    csv_data = Column(Text)
    columns = Column(String)
    row_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="files")

class QueryHistory(Base):
    __tablename__ = "query_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    file_id = Column(String, index=True)
    question = Column(String)
    generated_sql = Column(String)
    results = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)