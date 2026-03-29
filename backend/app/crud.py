from datetime import date, datetime, timedelta
import random
from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .models import EmailVerification

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VALID_TRANSACTION_TYPES = {"income", "expense"}
VALID_CATEGORY_TYPES = {"income", "expense"}
VALID_BUDGET_PERIODS = {"weekly", "monthly", "yearly", "custom"}
VALID_DEBT_DIRECTIONS = {"lent", "borrowed"}
VALID_DEBT_EVENT_TYPES = {"issue", "repayment", "adjustment", "forgiven"}


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def _require_category(
    db: Session,
    *,
    category_id: int,
    user_id: int,
    tx_type: Optional[str] = None,
):
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == user_id,
    ).first()
    if not category:
        raise ValueError("Category not found")
    if tx_type and category.type != tx_type:
        raise ValueError("Category type does not match transaction type")
    return category


def _require_account(db: Session, *, account_id: Optional[int], user_id: int):
    if account_id is None:
        return None
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.user_id == user_id,
    ).first()
    if not account:
        raise ValueError("Account not found")
    return account


def _change_account_balance(account: Optional[models.Account], delta: float):
    if account is not None:
        account.balance = float((account.balance or 0.0) + delta)


def _transaction_account_delta(tx_type: str, amount: float) -> float:
    return amount if tx_type == "income" else -amount


def _debt_issue_account_delta(direction: str, amount: float) -> float:
    return -amount if direction == "lent" else amount


def _debt_repayment_account_delta(direction: str, amount: float) -> float:
    return amount if direction == "lent" else -amount


def _apply_debt_event(debt: models.Debt, event_type: str, amount: float):
    if event_type == "issue":
        debt.current_balance = float((debt.current_balance or 0.0) + amount)
    elif event_type == "repayment":
        debt.current_balance = max(0.0, float((debt.current_balance or 0.0) - amount))
    elif event_type == "adjustment":
        debt.current_balance = float((debt.current_balance or 0.0) + amount)
    elif event_type == "forgiven":
        debt.current_balance = max(0.0, float((debt.current_balance or 0.0) - amount))

    debt.status = "closed" if debt.current_balance == 0 else "open"


def get_user_statistics(
    db: Session,
    owner_id: int,
    period: str = "month",
    start_date: date = None,
    end_date: date = None,
):
    now = datetime.utcnow().date()

    if start_date and end_date:
        start = start_date
        end = end_date
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

    transactions = (
        db.query(models.Transaction)
        .options(joinedload(models.Transaction.category))
        .filter(
            models.Transaction.owner_id == owner_id,
            models.Transaction.date >= start,
            models.Transaction.date <= end,
        )
        .all()
    )

    total_income = 0.0
    total_expense = 0.0
    income_by_category = {}
    expense_by_category = {}

    for tx in transactions:
        category_name = tx.category.name if tx.category else f"category:{tx.category_id}"
        if tx.type == "income":
            total_income += tx.amount
            income_by_category[category_name] = income_by_category.get(category_name, 0.0) + tx.amount
        else:
            total_expense += tx.amount
            expense_by_category[category_name] = expense_by_category.get(category_name, 0.0) + tx.amount

    return {
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "balance": float(total_income - total_expense),
        "income_by_category": {k: float(v) for k, v in income_by_category.items()},
        "expense_by_category": {k: float(v) for k, v in expense_by_category.items()},
    }


def create_user(db: Session, user: schemas.UserCreate):
    hashed = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed,
        name=user.name,
        is_verified=getattr(user, "is_verified", False),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_category(db: Session, user_id: int, category: schemas.CategoryCreate):
    if category.type not in VALID_CATEGORY_TYPES:
        raise ValueError("Invalid category type")

    db_category = models.Category(name=category.name, type=category.type, user_id=user_id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def get_categories_for_user(db: Session, user_id: int):
    return (
        db.query(models.Category)
        .filter(models.Category.user_id == user_id)
        .order_by(models.Category.type.asc(), models.Category.name.asc())
        .all()
    )


def create_account(db: Session, user_id: int, account: schemas.AccountCreate):
    db_account = models.Account(**account.model_dump(), user_id=user_id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def get_accounts_for_user(db: Session, user_id: int):
    return (
        db.query(models.Account)
        .filter(models.Account.user_id == user_id)
        .order_by(models.Account.name.asc())
        .all()
    )


def update_account(db: Session, user_id: int, account_id: int, account: schemas.AccountUpdate):
    db_account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.user_id == user_id,
    ).first()
    if not db_account:
        return None

    for key, value in account.model_dump(exclude_unset=True).items():
        setattr(db_account, key, value)

    db.commit()
    db.refresh(db_account)
    return db_account


def create_budget(db: Session, user_id: int, budget: schemas.BudgetCreate):
    if budget.period not in VALID_BUDGET_PERIODS:
        raise ValueError("Invalid budget period")
    _require_account(db, account_id=budget.account_id, user_id=user_id)
    if budget.category_id is not None:
        _require_category(db, category_id=budget.category_id, user_id=user_id)

    db_budget = models.Budget(**budget.model_dump(), user_id=user_id)
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


def get_budgets_for_user(db: Session, user_id: int):
    return (
        db.query(models.Budget)
        .filter(models.Budget.user_id == user_id)
        .order_by(models.Budget.start_date.desc(), models.Budget.id.desc())
        .all()
    )


def update_budget(db: Session, user_id: int, budget_id: int, budget: schemas.BudgetUpdate):
    db_budget = db.query(models.Budget).filter(
        models.Budget.id == budget_id,
        models.Budget.user_id == user_id,
    ).first()
    if not db_budget:
        return None

    payload = budget.model_dump(exclude_unset=True)
    if "period" in payload and payload["period"] not in VALID_BUDGET_PERIODS:
        raise ValueError("Invalid budget period")
    if "account_id" in payload:
        _require_account(db, account_id=payload["account_id"], user_id=user_id)
    if "category_id" in payload and payload["category_id"] is not None:
        _require_category(db, category_id=payload["category_id"], user_id=user_id)

    for key, value in payload.items():
        setattr(db_budget, key, value)

    db.commit()
    db.refresh(db_budget)
    return db_budget


def create_transaction(db: Session, owner_id: int, tx: schemas.TransactionCreate):
    if tx.type not in VALID_TRANSACTION_TYPES:
        raise ValueError("Invalid transaction type")

    category = _require_category(db, category_id=tx.category_id, user_id=owner_id, tx_type=tx.type)
    account = _require_account(db, account_id=tx.account_id, user_id=owner_id)

    db_tx = models.Transaction(
        amount=tx.amount,
        category_id=category.id,
        account_id=account.id if account else None,
        note=tx.note,
        type=tx.type,
        date=tx.date or date.today(),
        owner_id=owner_id,
    )
    db.add(db_tx)
    _change_account_balance(account, _transaction_account_delta(tx.type, tx.amount))
    db.commit()
    return get_transaction_for_user(db, owner_id=owner_id, tx_id=db_tx.id)


def get_transaction_for_user(db: Session, owner_id: int, tx_id: int):
    return (
        db.query(models.Transaction)
        .options(
            joinedload(models.Transaction.category),
            joinedload(models.Transaction.account),
        )
        .filter(
            models.Transaction.id == tx_id,
            models.Transaction.owner_id == owner_id,
        )
        .first()
    )


def get_transactions_for_user(db: Session, owner_id: int):
    return (
        db.query(models.Transaction)
        .options(
            joinedload(models.Transaction.category),
            joinedload(models.Transaction.account),
        )
        .filter(models.Transaction.owner_id == owner_id)
        .order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
        .all()
    )


def update_transaction(db: Session, owner_id: int, tx_id: int, tx: schemas.TransactionUpdate):
    db_tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id,
        models.Transaction.owner_id == owner_id,
    ).first()
    if not db_tx:
        return None

    old_account = _require_account(db, account_id=db_tx.account_id, user_id=owner_id)
    _change_account_balance(old_account, -_transaction_account_delta(db_tx.type, db_tx.amount))

    payload = tx.model_dump(exclude_unset=True)
    new_type = payload.get("type", db_tx.type)
    new_amount = payload.get("amount", db_tx.amount)
    new_category_id = payload.get("category_id", db_tx.category_id)
    new_account_id = payload.get("account_id", db_tx.account_id)

    if new_type not in VALID_TRANSACTION_TYPES:
        raise ValueError("Invalid transaction type")

    _require_category(db, category_id=new_category_id, user_id=owner_id, tx_type=new_type)
    new_account = _require_account(db, account_id=new_account_id, user_id=owner_id)

    for key, value in payload.items():
        setattr(db_tx, key, value)

    _change_account_balance(new_account, _transaction_account_delta(new_type, new_amount))
    db.commit()
    return get_transaction_for_user(db, owner_id=owner_id, tx_id=db_tx.id)


def delete_transaction(db: Session, owner_id: int, tx_id: int):
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id,
        models.Transaction.owner_id == owner_id,
    ).first()
    if not tx:
        return False

    account = _require_account(db, account_id=tx.account_id, user_id=owner_id)
    _change_account_balance(account, -_transaction_account_delta(tx.type, tx.amount))
    db.delete(tx)
    db.commit()
    return True


def create_debt(db: Session, user_id: int, debt: schemas.DebtCreate):
    if debt.direction not in VALID_DEBT_DIRECTIONS:
        raise ValueError("Invalid debt direction")

    account = _require_account(db, account_id=debt.account_id, user_id=user_id)
    issued_at = debt.issued_at or date.today()
    db_debt = models.Debt(
        person_name=debt.person_name,
        direction=debt.direction,
        principal_amount=debt.principal_amount,
        current_balance=0.0,
        currency=debt.currency,
        issued_at=issued_at,
        due_date=debt.due_date,
        note=debt.note,
        account_id=account.id if account else None,
        user_id=user_id,
    )
    db.add(db_debt)
    db.flush()

    initial_event = models.DebtEvent(
        debt_id=db_debt.id,
        event_type="issue",
        amount=debt.principal_amount,
        event_date=issued_at,
        note=debt.note or "",
        account_id=account.id if account else None,
    )
    db.add(initial_event)
    _apply_debt_event(db_debt, "issue", debt.principal_amount)
    _change_account_balance(account, _debt_issue_account_delta(debt.direction, debt.principal_amount))
    db.commit()
    return get_debt_for_user(db, user_id=user_id, debt_id=db_debt.id)


def get_debt_for_user(db: Session, user_id: int, debt_id: int):
    return (
        db.query(models.Debt)
        .options(
            joinedload(models.Debt.events),
            joinedload(models.Debt.account),
        )
        .filter(
            models.Debt.id == debt_id,
            models.Debt.user_id == user_id,
        )
        .first()
    )


def get_debts_for_user(db: Session, user_id: int):
    return (
        db.query(models.Debt)
        .options(
            joinedload(models.Debt.events),
            joinedload(models.Debt.account),
        )
        .filter(models.Debt.user_id == user_id)
        .order_by(models.Debt.status.asc(), models.Debt.issued_at.desc(), models.Debt.id.desc())
        .all()
    )


def update_debt(db: Session, user_id: int, debt_id: int, debt: schemas.DebtUpdate):
    db_debt = db.query(models.Debt).filter(
        models.Debt.id == debt_id,
        models.Debt.user_id == user_id,
    ).first()
    if not db_debt:
        return None

    payload = debt.model_dump(exclude_unset=True)
    if "direction" in payload and payload["direction"] not in VALID_DEBT_DIRECTIONS:
        raise ValueError("Invalid debt direction")
    if "account_id" in payload:
        _require_account(db, account_id=payload["account_id"], user_id=user_id)

    for key, value in payload.items():
        setattr(db_debt, key, value)

    if db_debt.current_balance == 0 and db_debt.status != "closed":
        db_debt.status = "closed"

    db.commit()
    return get_debt_for_user(db, user_id=user_id, debt_id=debt_id)


def create_debt_event(db: Session, user_id: int, debt_id: int, event: schemas.DebtEventCreate):
    if event.event_type not in VALID_DEBT_EVENT_TYPES:
        raise ValueError("Invalid debt event type")

    debt = db.query(models.Debt).filter(
        models.Debt.id == debt_id,
        models.Debt.user_id == user_id,
    ).first()
    if not debt:
        return None

    account = _require_account(
        db,
        account_id=event.account_id if event.account_id is not None else debt.account_id,
        user_id=user_id,
    )
    event_date = event.event_date or date.today()
    db_event = models.DebtEvent(
        debt_id=debt.id,
        event_type=event.event_type,
        amount=event.amount,
        event_date=event_date,
        note=event.note or "",
        account_id=account.id if account else None,
    )
    db.add(db_event)

    _apply_debt_event(debt, event.event_type, event.amount)

    if event.event_type == "issue":
        _change_account_balance(account, _debt_issue_account_delta(debt.direction, event.amount))
    elif event.event_type == "repayment":
        _change_account_balance(account, _debt_repayment_account_delta(debt.direction, event.amount))

    db.commit()
    db.refresh(db_event)
    return db_event


def create_email_verification(db: Session, email: str, password: str, name: str):
    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)

    record = EmailVerification(
        email=email,
        code=code,
        expires_at=expires,
        password=password,
        name=name,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return code


def verify_email_code(db: Session, email: str, code: str):
    record = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.code == code,
        EmailVerification.expires_at > datetime.utcnow(),
    ).first()

    if not record:
        return None

    user_data = schemas.UserCreate(
        email=record.email,
        password=record.password,
        name=record.name,
    )
    create_user(db, user_data)

    db.delete(record)
    db.commit()
    return True


def export_transactions(db: Session, owner_id: int):
    transactions = (
        db.query(models.Transaction)
        .options(joinedload(models.Transaction.category))
        .filter(models.Transaction.owner_id == owner_id)
        .all()
    )

    return [
        {
            "amount": t.amount,
            "category_id": t.category_id,
            "category_name": t.category.name if t.category else None,
            "account_id": t.account_id,
            "note": t.note,
            "type": t.type,
            "date": t.date.isoformat(),
        }
        for t in transactions
    ]


def import_transactions(db: Session, owner_id: int, data: List[schemas.TransactionExport]):
    imported = []
    for tx in data:
        category_id = tx.category_id
        if category_id is None:
            if not tx.category_name:
                raise ValueError("category_id or category_name is required")
            category = (
                db.query(models.Category)
                .filter(
                    models.Category.user_id == owner_id,
                    models.Category.name == tx.category_name,
                    models.Category.type == tx.type,
                )
                .first()
            )
            if not category:
                category = models.Category(name=tx.category_name, type=tx.type, user_id=owner_id)
                db.add(category)
                db.flush()
            category_id = category.id

        imported.append(
            create_transaction(
                db,
                owner_id=owner_id,
                tx=schemas.TransactionCreate(
                    amount=tx.amount,
                    category_id=category_id,
                    account_id=tx.account_id,
                    note=tx.note,
                    type=tx.type,
                    date=tx.date,
                ),
            )
        )

    return imported
