# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.sql import expression
from .database import Base
from datetime import datetime

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(1024), nullable=True)
    description = Column(Text, nullable=True)
    price = Column(String(64), nullable=True)
    active = Column(Boolean, default=True, server_default=expression.true())
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow)


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    event = Column(String(128), nullable=False)
    enabled = Column(Boolean, default=True, server_default=expression.true())
