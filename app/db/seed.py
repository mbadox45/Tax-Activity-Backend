from sqlalchemy.orm import Session

from app.models.user_model import User
from app.core.security import hash_password

def run_seed(db: Session):
    try:
        # =========================
        # 1️⃣ Superuser
        # =========================
        superuser = db.query(User).filter(
            User.username == "admin"
        ).first()

        if not superuser:
            user = User(
                name="Admin",
                username="admin@ardiartax.com",
                password=hash_password("admin123"),
                role="admin",
                is_active=True
            )
            db.add(user)
            db.commit()
            print("✅ Superuser created")
        else:
            print("ℹ️ Superuser already exists")

    except Exception as e:
        db.rollback()
        print("❌ Seed error:", e)
        