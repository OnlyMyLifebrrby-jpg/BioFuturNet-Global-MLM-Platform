from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import User, Order, OrderItem, Commission, CommissionType, Wallet
import logging

logger = logging.getLogger("BioFN_TreeEngine")

class TreeEngine:
    
    @staticmethod
    def register_user_in_trees(db: Session, new_user_id: int, sponsor_id: int, parent_id: int, binary_position: str):
        """
        تسجيل عضو جديد في الشجرة الثنائية (Binary) والشجرة العمودية (Unilevel)
        binary_position: إما 'left' أو 'right'
        """
        new_user = db.query(User).filter(User.id == new_user_id).first()
        if not new_user:
            raise ValueError("المستخدم غير موجود.")

        # 1. تعيين المستهلك في شجرة Unilevel
        new_user.sponsor_id = sponsor_id

        # 2. تعيين المستهلك في الشجرة الثنائية Binary
        parent = db.query(User).filter(User.id == parent_id).first()
        if not parent:
            raise ValueError("الأب في الشجرة الثنائية غير موجود.")

        if binary_position not in ["left", "right"]:
            raise ValueError("موقع الشجرة الثنائية يجب أن يكون 'left' أو 'right'.")

        # التحقق من أن المكان فارغ تحت الأب في ذلك الاتجاه
        existing_child = db.query(User).filter(
            User.parent_id == parent_id, 
            User.binary_position == binary_position
        ).first()

        if existing_child:
            raise ValueError(f"المكان {binary_position} محجوز مسبقاً تحت هذا العضو.")

        new_user.parent_id = parent_id
        new_user.binary_position = binary_position
        
        db.commit()
        db.refresh(new_user)
        return {"status": "success", "message": "تم ربط المستخدم بنجاح في الشجرتين."}

    @staticmethod
    def update_binary_volumes(db: Session, user_id: int, pv_amount: float):
        """
        صعود الحجم (Volume PV) صعودياً للأعلى في الشجرة الثنائية وتحديث النقاط يمين ويسار
        بشكل تلقائي ولحظي مع كل عملية شراء منتج (القاعدة Product-Based)
        """
        current_user = db.query(User).filter(User.id == user_id).first()
        
        while current_user and current_user.parent_id:
            parent = db.query(User).filter(User.id == current_user.parent_id).first()
            if not parent:
                break
            
            # تحديد ما إذا كان الفرع يمين أم يسار بالنسبة للأب
            if current_user.binary_position == "left":
                parent.left_volume += pv_amount
            elif current_user.binary_position == "right":
                parent.right_volume += pv_amount
            
            db.commit()
            
            # الانتقال للأعلى (Upstream)
            current_user = parent

    @staticmethod
    def get_binary_tree_structure(db: Session, user_id: int, depth: int = 3):
        """
        استخراج شجرة المستخدم الثنائية لعرضها على الواجهة التفاعلية (HTML/HTMX)
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        def build_node(current_user, current_depth):
            if not current_user or current_depth > depth:
                return None
            
            # البحث عن الأبناء في اليسار واليمين
            left_child = db.query(User).filter(User.parent_id == current_user.id, User.binary_position == "left").first()
            right_child = db.query(User).filter(User.parent_id == current_user.id, User.binary_position == "right").first()

            return {
                "id": current_user.id,
                "username": current_user.username,
                "full_name": current_user.full_name,
                "rank": current_user.rank,
                "left_volume": current_user.left_volume,
                "right_volume": current_user.right_volume,
                "left": build_node(left_child, current_depth + 1),
                "right": build_node(right_child, current_depth + 1)
            }

        return build_node(user, 1)

    @staticmethod
    def get_unilevel_lineage(db: Session, user_id: int, max_levels: int = 10):
        """
        الحصول على شبكة Unilevel حتى 10 مستويات عمق للعمولات غير المباشرة
        """
        network = {}
        current_level_ids = [user_id]
        
        for level in range(1, max_levels + 1):
            if not current_level_ids:
                break
            next_level_users = db.query(User).filter(User.sponsor_id.in_(current_level_ids)).all()
            if not next_level_users:
                break
            
            network[f"level_{level}"] = [{"id": u.id, "username": u.username, "sponsor_id": u.sponsor_id} for u in next_level_users]
            current_level_ids = [u.id for u in next_level_users]
            
        return network