# app/db/seed.py

from sqlalchemy.orm import Session

from app.models.user_model import User
from app.models.group_model import Group  # 💡 Pastikan mengimport model Group
from app.core.security import hash_password

def run_seed(db: Session):
    try:
        # =========================================================================
        # 1️⃣ SEED GROUPS & SUB-GROUPS
        # =========================================================================
        # Cek apakah Group Utama 'Finance & Accounting' sudah ada
        parent_group = db.query(Group).filter(Group.name == "Finance & Accounting").first()

        if not parent_group:
            parent_group = Group(
                name="Finance & Accounting",
                parent_id=None,
                is_active=True
            )
            db.add(parent_group)
            db.commit()
            db.refresh(parent_group)  # Refresh untuk mendapatkan ID yang baru digenerate
            print("✅ Parent Group 'Finance & Accounting' created")
        else:
            print("ℹ️ Parent Group 'Finance & Accounting' already exists")

        # Daftar Sub-Groups yang ingin dibuat di bawah 'Finance & Accounting'
        sub_groups_to_create = ["Tax", "Finance", "Asset & Anggaran"]

        for sub_name in sub_groups_to_create:
            # Cek apakah sub-group sudah ada
            sub_group_exists = db.query(Group).filter(
                Group.name == sub_name, 
                Group.parent_id == parent_group.id
            ).first()

            if not sub_group_exists:
                new_sub_group = Group(
                    name=sub_name,
                    parent_id=parent_group.id,  # 💡 Menghubungkan ke Group Utama
                    is_active=True
                )
                db.add(new_sub_group)
                print(f"✅ Sub-Group '{sub_name}' created")
            else:
                print(f"ℹ️ Sub-Group '{sub_name}' already exists")
        
        # Commit seluruh sub-groups yang baru ditambahkan
        db.commit()

        # =========================================================================
        # 2️⃣ SEED SUPERUSER
        # =========================================================================
        superuser = db.query(User).filter(
            User.username == "rioteguhard@gmail.com"  # Menyesuaikan dengan isian payload Anda sebelumnya
        ).first()

        if not superuser:
            user = User(
                name="Rio Teguh A",
                username="rioteguhard@gmail.com",
                password=hash_password("123456"),
                role="super_admin",
                is_active=True,
                group_id=None  # Super Admin umumnya tidak terikat group spesifik
            )
            db.add(user)
            db.commit()
            print("✅ Superadmin created")
        else:
            print("ℹ️ Superadmin already exists")

    except Exception as e:
        db.rollback()
        print("❌ Seed error:", e)