from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    debts = relationship("Debt", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="owner")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, default="cash")
    currency = Column(String, default="RUB")
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    budgets = relationship("Budget", back_populates="account")
    debts = relationship("Debt", back_populates="account")
    debt_events = relationship("DebtEvent", back_populates="account")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    period = Column(String, default="monthly")
    start_date = Column(Date, nullable=False, default=date.today)
    end_date = Column(Date, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")
    account = relationship("Account", back_populates="budgets")


class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    person_name = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # lent | borrowed
    principal_amount = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    status = Column(String, default="open")
    issued_at = Column(Date, default=date.today, nullable=False)
    due_date = Column(Date, nullable=True)
    note = Column(String, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    user = relationship("User", back_populates="debts")
    account = relationship("Account", back_populates="debts")
    events = relationship("DebtEvent", back_populates="debt", cascade="all, delete-orphan")


class DebtEvent(Base):
    __tablename__ = "debt_events"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # issue | repayment | adjustment | forgiven
    amount = Column(Float, nullable=False)
    event_date = Column(Date, default=date.today, nullable=False)
    note = Column(String, default="")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    debt = relationship("Debt", back_populates="events")
    account = relationship("Account", back_populates="debt_events")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    note = Column(String, default="")
    type = Column(String, default="expense")
    date = Column(Date, default=date.today)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    password = Column(String, nullable=True)
    name = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
