from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
import random
from datetime import datetime, timedelta, date   # ← прямой импорт date
from .models import EmailVerification
import json
from typing import List

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_statistics(
    db: Session,
    owner_id: int,
    period: str = "month",
    start_date: date = None,
    end_date: date = None
):
    try:
        now = datetime.utcnow().date()
        
        if start_date and end_date:
            filter_start = datetime.combine(start_date, datetime.min.time())
            filter_end = datetime.combine(end_date, datetime.max.time())
            print(f"  📅 Используются явные даты: {start_date} - {end_date}")
        else:
            if period == "day":
                start = now - timedelta(days=1)
                end = now
            elif period == "week":
                start = now - timedelta(weeks=1)
                end = now
            elif period == "month":
                start = now - timedelta(days=30)
                end = now
            elif period == "year":
                start = now - timedelta(days=365)
                end = now
            else:
                start = datetime(1970, 1, 1).date()
                end = now
            
            filter_start = datetime.combine(start, datetime.min.time())
            filter_end = datetime.combine(end, datetime.max.time())
            print(f"  📅 Используется period '{period}': {start} - {end}")

        transactions = db.query(models.Transaction).filter(
            models.Transaction.owner_id == owner_id,
            models.Transaction.date >= filter_start.date(),
            models.Transaction.date <= filter_end.date()
        ).all()

        print(f"  🔍 Найдено транзакций: {len(transactions)}")
        for t in transactions:
            print(f"    - {t.date}: {t.type} {t.category} {t.amount}")

        total_income = 0.0
        total_expense = 0.0
        income_by_category = {}
        expense_by_category = {}

        for t in transactions:
            if t.type == "income":
                total_income += t.amount
                income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount
            else:
                total_expense += t.amount
                expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount

        return {
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "balance": float(total_income - total_expense),
            "income_by_category": {k: float(v) for k, v in income_by_category.items()},
            "expense_by_category": {k: float(v) for k, v in expense_by_category.items()},
        }
    
    except Exception as e:
        print(f"❌ Ошибка в get_user_statistics: {e}")
        import traceback
        traceback.print_exc()
        raise

def create_user(db: Session, user: schemas.UserCreate):
    hashed = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed,
        name=user.name,
        is_verified=getattr(user, "is_verified", False)
    )
    db.add(db_user)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании пользователя: {e}")
        raise e
    db.refresh(db_user)
    return db_user

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_transaction(db: Session, owner_id: int, tx: schemas.TransactionCreate):
    db_tx = models.Transaction(
        amount=tx.amount,
        category=tx.category,
        note=tx.note,
        type=tx.type,
        date=tx.date or date.today(),   # ← date.today() работает
        owner_id=owner_id
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

def get_transactions_for_user(db: Session, owner_id: int):
    return db.query(models.Transaction).filter(
        models.Transaction.owner_id == owner_id
    ).order_by(models.Transaction.date.desc()).all()

def create_email_verification(db: Session, email: str, password: str, name: str):
    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)

    record = EmailVerification(
        email=email,
        code=code,
        expires_at=expires,
        password=password,
        name=name
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return code

def verify_email_code(db: Session, email: str, code: str):
    record = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.code == code,
        EmailVerification.expires_at > datetime.utcnow()
    ).first()

    if not record:
        return None

    user_data = schemas.UserCreate(
        email=record.email,
        password=record.password,
        name=record.name
    )
    create_user(db, user_data)   # ← используем уже определённую функцию

    db.delete(record)
    db.commit()
    return True

def export_transactions(db: Session, owner_id: int):
    transactions = db.query(models.Transaction).filter(
        models.Transaction.owner_id == owner_id
    ).all()

    return [
        {
            "amount": t.amount,
            "category": t.category,
            "note": t.note,
            "type": t.type,
            "date": t.date.isoformat()
        }
        for t in transactions
    ]


def import_transactions(db: Session, owner_id: int, data: List[schemas.TransactionExport]):
    for t in data:
        db_tx = models.Transaction(
            amount=t.amount,
            category=t.category,
            note=t.note,
            type=t.type,
            date=t.date,
            owner_id=owner_id
        )
        db.add(db_tx)

    db.commit()