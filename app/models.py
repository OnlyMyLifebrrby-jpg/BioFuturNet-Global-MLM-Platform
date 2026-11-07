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

# 1. نظام المستخدمين والتحقق (SYSTEM A)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    country = Column(String(50), default="Algeria")
    
    # KYC & Security
    is_kyc_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER)
    two_factor_secret = Column(String(100), nullable=True)
    
    # Network Positioning (SYSTEM B)
    sponsor_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Unilevel Sponsor
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # Binary Parent
    binary_position = Column(String(10), nullable=True)                  # 'left' or 'right'
    
    # Volume & Ranks (SYSTEM F)
    rank = Column(String(50), default="Beginner")
    left_volume = Column(Float, default=0.0)
    right_volume = Column(Float, default=0.0)
    personal_sales_volume = Column(Float, default=0.0) # شرط البيع الحقيقي
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user")
    commissions = relationship("Commission", back_populates="user")

# 2. نظام المتجر والمنتجات - القاعدة القانونية Product-Based (SYSTEM C)
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price_usd = Column(Float, nullable=False)
    price_biofn = Column(Float, nullable=False) # 1 BioFN = 500 DZD equivalent
    pv_value = Column(Float, nullable=False)    # Personal/Product Volume for commissions
    stock = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="BioFN") # BioFN, USD, DZD
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

# 3. محرك العمولات المرتبط حصرياً بالمبيعات (SYSTEM D)
class Commission(Base):
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # من قام بشراء المنتج
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)     # ربط إلزامي برقم الطلب لضمان القانونية
    amount = Column(Float, nullable=False) # بالعملة الداخلية BioFN
    commission_type = Column(SQLEnum(CommissionType), nullable=False)
    is_paid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="commissions", foreign_keys=[user_id])

# 4. نظام المحفظة المالية (SYSTEM E)
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
    tx_type = Column(String(50), nullable=False) # deposit, withdrawal, transfer, commission
    status = Column(String(20), default="completed")
    reference_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)