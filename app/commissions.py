from sqlalchemy.orm import Session
from app.models import User, Order, OrderItem, Commission, CommissionType, Wallet
import logging

logger = logging.getLogger("BioFN_CommissionEngine")

class CommissionEngine:
    
    @staticmethod
    def calculate_order_commissions(db: Session, order_id: int):
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"status": "error", "message": "الطلب غير موجود."}

        buyer = db.query(User).filter(User.id == order.user_id).first()
        if not buyer:
            return {"status": "error", "message": "المشتري غير موجود."}

        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        total_pv = sum(item.pv_earned * item.quantity for item in order_items)
        
        if total_pv <= 0:
            return {"status": "success", "message": "الطلب لا يحتوي على نقاط مبيعات (PV) لتوليد عمولات."}

        buyer.personal_sales_volume += total_pv
        db.commit()

        if buyer.sponsor_id:
            sponsor = db.query(User).filter(User.id == buyer.sponsor_id).first()
            if sponsor:
                direct_amount = total_pv * 0.10
                CommissionEngine._add_commission(db, sponsor.id, buyer.id, order.id, direct_amount, CommissionType.DIRECT)

        CommissionEngine._distribute_unilevel(db, buyer, total_pv, order.id)

        from app.tree import TreeEngine
        TreeEngine.update_binary_volumes(db, buyer.id, total_pv)
        CommissionEngine._calculate_binary_pairing(db, buyer, order.id)

        return {"status": "success", "message": "تم حساب وتوزيع كافة العمولات المرتبطة بالمبيع لحظياً بأجزاء من الثانية."}

    @staticmethod
    def _distribute_unilevel(db: Session, buyer: User, total_pv: float, order_id: int):
        unilevel_rates = {
            1: 0.05, 2: 0.03, 3: 0.02, 4: 0.01, 5: 0.01,
            6: 0.01, 7: 0.01, 8: 0.005, 9: 0.005, 10: 0.005
        }
        
        current_sponsor_id = buyer.sponsor_id
        level = 1
        
        while current_sponsor_id and level <= 10:
            sponsor = db.query(User).filter(User.id == current_sponsor_id).first()
            if not sponsor:
                break
            
            rate = unilevel_rates.get(level, 0.01)
            commission_amount = total_pv * rate
            
            CommissionEngine._add_commission(db, sponsor.id, buyer.id, order_id, commission_amount, CommissionType.UNILEVEL)
            
            current_sponsor_id = sponsor.sponsor_id
            level += 1

    @staticmethod
    def _calculate_binary_pairing(db: Session, user: User, order_id: int):
        current = user
        while current and current.parent_id:
            parent = db.query(User).filter(User.id == current.parent_id).first()
            if not parent:
                break
            
            min_volume = min(parent.left_volume, parent.right_volume)
            if min_volume >= 100:
                pairing_bonus = min_volume * 0.10
                parent.left_volume -= min_volume
                parent.right_volume -= min_volume
                db.commit()
                
                CommissionEngine._add_commission(db, parent.id, user.id, order_id, pairing_bonus, CommissionType.BINARY_PAIRING)
            
            current = parent

    @staticmethod
    def _add_commission(db: Session, user_id: int, source_user_id: int, order_id: int, amount: float, c_type: CommissionType):
        if amount <= 0:
            return
        
        commission = Commission(
            user_id=user_id,
            source_user_id=source_user_id,
            order_id=order_id,
            amount=amount,
            commission_type=c_type,
            is_paid=True
        )
        db.add(commission)
        
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if wallet:
            wallet.balance_biofn += amount
            wallet.total_earned += amount
        else:
            new_wallet = Wallet(user_id=user_id, balance_biofn=amount, total_earned=amount)
            db.add(new_wallet)
            
        db.commit()
