from sqlalchemy.orm import Session
from app.models import Wallet, Transaction, User
import logging

logger = logging.getLogger("BioFN_WalletEngine")

class WalletEngine:
    
    @staticmethod
    def get_wallet_balance(db: Session, user_id: int):
        """
        استعلام لحظي عن أرصدة المحفظة بالعملات المختلفة
        """
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            return {"status": "error", "message": "المحفظة غير موجودة."}
        
        return {
            "status": "success",
            "balance_biofn": wallet.balance_biofn,
            "balance_dzd": wallet.balance_dzd, # 1 BioFN = 500 DZD
            "balance_usd": wallet.balance_usd,
            "total_earned": wallet.total_earned,
            "total_withdrawn": wallet.total_withdrawn
        }

    @staticmethod
    def request_withdrawal(db: Session, user_id: int, amount_biofn: float, payout_method: str, account_details: str):
        """
        طلب سحب الأرباح (يدعم التحويل البنكي DZD / BaridiMob أو العملات الرقمية Crypto / USDS)
        """
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            return {"status": "error", "message": "المحفظة غير موجودة."}

        if amount_biofn <= 0:
            return {"status": "error", "message": "مبلغ السحب غير صالح."}

        if wallet.balance_biofn < amount_biofn:
            return {"status": "error", "message": "رصيد المحفظة غير كافٍ لإتمام عملية السحب."}

        # خصم المبلغ مؤقتاً أو كلياً من المحفظة لحين الموافقة من لوحة المدير (SYSTEM G)
        wallet.balance_biofn -= amount_biofn
        wallet.total_withdrawn += amount_biofn

        # تسجيل المعاملة في سجل المعاملات المالية
        transaction = Transaction(
            wallet_id=wallet.id,
            amount=amount_biofn,
            currency="BioFN",
            tx_type=f"withdrawal_{payout_method}",
            status="pending", # بانتظار موافقة المدير
            reference_note=f"Payout to {payout_method}: {account_details}"
        )
        db.add(transaction)
        db.commit()

        return {
            "status": "success",
            "message": "تم تقديم طلب السحب بنجاح وهو قيد المراجعة الفورية من الإدارة.",
            "remaining_balance": wallet.balance_biofn
        }

    @staticmethod
    def transfer_funds(db: Session, sender_id: int, recipient_username: str, amount_biofn: float):
        """
        تحويل رصيد داخلي بين الأعضاء بشكل فوري وأجزاء من الثانية
        """
        if amount_biofn <= 0:
            return {"status": "error", "message": "مبلغ التحويل يجب أن يكون أكبر من الصفر."}

        sender_wallet = db.query(Wallet).filter(Wallet.user_id == sender_id).first()
        if not sender_wallet or sender_wallet.balance_biofn < amount_biofn:
            return {"status": "error", "message": "رصيدك غير كافٍ لإتمام التحويل."}

        recipient = db.query(User).filter(User.username == recipient_username).first()
        if not recipient or not recipient.is_active:
            return {"status": "error", "message": "المستلم غير موجود أو الحساب غير نشط."}

        if sender_id == recipient.id:
            return {"status": "error", "message": "لا يمكنك تحويل الأموال إلى نفس الحساب."}

        recipient_wallet = db.query(Wallet).filter(Wallet.user_id == recipient.id).first()
        if not recipient_wallet:
            recipient_wallet = Wallet(user_id=recipient.id, balance_biofn=0.0)
            db.add(recipient_wallet)

        # خصم وإضافة الأرصدة
        sender_wallet.balance_biofn -= amount_biofn
        recipient_wallet.balance_biofn += amount_biofn

        # تسجيل العمليات للمعطرفين
        tx_send = Transaction(
            wallet_id=sender_wallet.id,
            amount=-amount_biofn,
            currency="BioFN",
            tx_type="internal_transfer_out",
            status="completed",
            reference_note=f"Transfer to @{recipient.username}"
        )
        tx_recv = Transaction(
            wallet_id=recipient_wallet.id,
            amount=amount_biofn,
            currency="BioFN",
            tx_type="internal_transfer_in",
            status="completed",
            reference_note=f"Received from sender id {sender_id}"
        )

        db.add(tx_send)
        db.add(tx_recv)
        db.commit()

        return {"status": "success", "message": f"تم تحويل {amount_biofn} BioFN بنجاح إلى العضو @{recipient.username}."}