# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

from app.models import Base, User, Product, Order, OrderItem, Wallet, Transaction, OrderStatus
from app.tree import TreeEngine
from app.commissions import CommissionEngine
from app.wallet import WalletEngine

# إعداد قاعدة البيانات عبر متغير البيئة DATABASE_URL في Render
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/biofn_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(
    title="BioFuturNet (BioFN) Global Platform",
    description="منصة تسويق شبكي 100% تعتمد على المنتجات الحقيقية Product-Based بتقنية FastAPI السريعة",
    version="1.0.0"
)

# إعداد قوالب HTML ومجلد templates
templates = Jinja2Templates(directory="templates")

# إنشاء الجداول تلقائياً عند الإقلاع الأول
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- واجهات المستخدم (HTML / Templates) ---
@app.get("/", include_in_schema=False)
def serve_dashboard(request: Request):
    """عرض اللوحة الرئيسية للمنصة"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/templates/tree_view.html", include_in_schema=False)
def serve_tree_view(request: Request):
    """عرض الشجرة التفاعلية عند طلب HTMX"""
    return templates.TemplateResponse("tree_view.html", {"request": request})


# --- SYSTEM C: المتجر وشراء المنتجات الحقيقية ---
@app.post("/api/shop/purchase")
def purchase_product(user_id: int, product_id: int, quantity: int = 1, db: Session = Depends(get_db)):
    """
    شراء منتج حقيقي وتوليد العمولات تلقائياً (القاعدة الذهبية: لا عمولة بدون بيع منتج)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="المنتج غير موجود أو غير متوفر.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود.")

    total_price = product.price_biofn * quantity
    total_pv = product.pv_value * quantity

    # إنشاء طلب الشراء
    new_order = Order(
        user_id=user.id,
        total_amount=total_price,
        currency="BioFN",
        status=OrderStatus.PAID
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # إضافة عنصر الطلب
    order_item = OrderItem(
        order_id=new_order.id,
        product_id=product.id,
        quantity=quantity,
        price_at_purchase=product.price_biofn,
        pv_earned=total_pv
    )
    db.add(order_item)
    db.commit()

    # تشغيل محرك العمولات فوراً وبأجزاء من الثانية
    commission_result = CommissionEngine.calculate_order_commissions(db, new_order.id)

    return {
        "status": "success",
        "message": "تم إتمام عملية شراء المنتج بنجاح وتوزيع العمولات والنقاط لحظياً.",
        "order_id": new_order.id,
        "total_pv": total_pv,
        "commission_details": commission_result
    }


# --- SYSTEM E: المحفظة المالية ---
@app.get("/api/wallet/summary")
def get_wallet_summary(user_id: int = 1, db: Session = Depends(get_db)):
    """
    استعلام سريع عن أرصدة المحفظة
    """
    return WalletEngine.get_wallet_balance(db, user_id)


# --- SYSTEM G: لوحة تحكم المدير (Admin Dashboard) ---
@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    """
    إحصائيات حية وشاملة لمدير المنصة
    """
    total_users = db.query(User).count()
    total_orders = db.query(Order).count()
    pending_withdrawals = db.query(Transaction).filter(Transaction.tx_type.like("withdrawal_%"), Transaction.status == "pending").count()
    
    return {
        "status": "success",
        "platform_name": "BioFuturNet (BioFN)",
        "total_users": total_users,
        "total_orders": total_orders,
        "pending_withdrawals": pending_withdrawals,
        "currency_peg": "1 BioFN = 500 DZD"
    }

@app.post("/api/admin/approve-withdrawal")
def approve_withdrawal(transaction_id: int, db: Session = Depends(get_db)):
    """
    موافقة المدير على طلب السحب المالي
    """
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="معاملة السحب غير موجودة.")
    
    tx.status = "completed"
    db.commit()
    return {"status": "success", "message": f"تمت الموافقة على طلب السحب برقم {transaction_id} بنجاح."}


# نقطة اختبار تشغيل الخادم
@app.get("/api/status")
def read_root():
    return {
        "project": "BioFuturNet (BioFN)",
        "status": "Online",
        "compliance": "100% Product-Based MLM Platform",
        "author": "Dr. Bachir BOURROUBEY (الدكتور بوروباي البشير)"
    }
