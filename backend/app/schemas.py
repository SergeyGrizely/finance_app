import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import date as date_type  # можно и так, но для единообразия лучше datetime.date

# ====================== Базовые схемы ======================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    is_verified: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True

# ====================== Транзакции ======================

class TransactionBase(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    type: str = "expense"

class TransactionCreate(TransactionBase):
    date: Optional[datetime.date] = None   # явно datetime.date

class TransactionOut(TransactionBase):
    id: int
    date: datetime.date   # явно datetime.date
    owner_id: int

    class Config:
        from_attributes = True

class TransactionsList(BaseModel):
    transactions: List[TransactionOut]

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    category: Optional[str] = None
    note: Optional[str] = None
    type: Optional[str] = None
    date: Optional[datetime.date] = Field(default=None, description="Дата транзакции")   # явно datetime.date

class TransactionExport(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    type: str
    date: datetime.date

# ====================== Статистика ======================

class StatisticsOut(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    income_by_category: Dict[str, float]
    expense_by_category: Dict[str, float]

# ====================== Регистрация / верификация ======================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str