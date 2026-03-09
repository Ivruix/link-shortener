from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    links = relationship("Link", back_populates="user")
    expired_links = relationship("ExpiredLink", back_populates="user")

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True, nullable=False)
    original_url = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="links")

class ExpiredLink(Base):
    __tablename__ = "expired_links"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, nullable=False)
    original_url = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    expired_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deletion_reason = Column(String, nullable=False)

    user = relationship("User", back_populates="expired_links")
