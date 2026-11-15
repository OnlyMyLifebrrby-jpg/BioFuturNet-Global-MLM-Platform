from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    LEADER = "leader"
    MEMBER = "member"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CommissionType(str, enum.Enum):
    DIRECT = "direct"
    UNILEVEL = "unilevel"
    BINARY_PAIRING = "binary_pairing"
    RANK_BONUS = "rank_bonus"
    LEADERSHIP_POOL = "leadership_pool"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    country = Column(String(50), default="Algeria")
    
    is_kyc_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER)
    two_factor_secret = Column(String(100), nullable=True)
    
    sponsor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    binary_position = Column(String(10), nullable=True)
    
    rank = Column(String(50), default="Beginner")
    left_volume = Column(Float, default=0.0)
    right_volume = Column(Float, default=0.0)
    personal_sales_volume = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    wallet = relationship("Wallet", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user")
    commissions = relationship("Commission", back_populates="user", foreign_keys="[Commission.user_id]")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price_usd = Column(Float, nullable=False, default=20.0)
    price_biofn = Column(Float, nullable=False)
    pv_value = Column(Float, nullable=False)
    stock = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="BioFN")
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price_at_purchase = Column(Float, nullable=False)
    pv_earned = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")

class Commission(Base):
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    commission_type = Column(SQLEnum(CommissionType), nullable=False)
    is_paid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="commissions", foreign_keys=[user_id])

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance_biofn = Column(Float, default=0.0)
    balance_dzd = Column(Float, default=0.0)
    balance_usd = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="wallet")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="BioFN")
    tx_type = Column(String(50), nullable=False)
    status = Column(String(20), default="completed")
    reference_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
