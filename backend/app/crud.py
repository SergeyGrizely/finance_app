from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
import random
from datetime import datetime, timedelta
from .models import EmailVerification

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_statistics(db: Session, owner_id: int, period: str = "month"):
    from datetime import datetime, timedelta

    now = datetime.utcnow()

    # Определяем дату начала периода
    if period == "day":
        start = now - timedelta(days=1)
    elif period == "week":
        start = now - timedelta(weeks=1)
    elif period == "month":
        start = now - timedelta(days=30)
    elif period == "year":
        start = now - timedelta(days=365)
    else:
        start = datetime(1970, 1, 1)

    # Получаем транзакции пользователя за период
    transactions = db.query(models.Transaction).filter(
        models.Transaction.owner_id == owner_id,
        models.Transaction.created_at >= start
    ).all()

    total_income = 0.0
    total_expense = 0.0
    income_by_category = {}
    expense_by_category = {}

    for t in transactions:
        if t.type == "income":
            total_income += t.amount
            income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount
        else:  # expense
            total_expense += t.amount
            expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount

    return {
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "balance": float(total_income - total_expense),
        "income_by_category": {k: float(v) for k, v in income_by_category.items()},
        "expense_by_category": {k: float(v) for k, v in expense_by_category.items()},
    }




def create_user(db: Session, user: schemas.UserCreate):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    hashed = pwd_context.hash(user.password[:72])
    db_user = models.User(
        email=user.email,
        hashed_password=hashed,
        name=user.name,           # никнейм
        is_verified=getattr(user, "is_verified", False)  # ставим True, если передано
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
        type=tx.type,        # <--- добавляем
        owner_id=owner_id
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

def get_transactions_for_user(db: Session, owner_id: int):
    return db.query(models.Transaction).filter(models.Transaction.owner_id == owner_id).order_by(models.Transaction.created_at.desc()).all()

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
        return None  # неверный код

    # Создаём пользователя из временной записи
    from . import crud, schemas
    user_data = schemas.UserCreate(
        email=record.email,
        password=record.password,
        name=record.name
    )
    crud.create_user(db, user_data)

    # Удаляем запись с кодом, чтобы нельзя было использовать повторно
    db.delete(record)
    db.commit()

    return True

