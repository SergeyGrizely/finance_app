from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from typing import Dict

from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    is_verified: bool = False  # по умолчанию False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str  # <-- добавляем имя

    class Config:
        orm_mode = True

class TransactionBase(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""


class TransactionOut(TransactionBase):
    id: int
    created_at: datetime
    owner_id: int
    type: str = "expense"
    class Config:
        orm_mode = True

class TransactionsList(BaseModel):
    transactions: List[TransactionOut]

class TransactionCreate(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    type: str = "expense"  # "income" or "expense"

class TransactionUpdate(BaseModel):
    amount: Optional[float]
    category: Optional[str]
    note: Optional[str]
    type: Optional[str]  # "income" или "expense"

class StatisticsOut(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    income_by_category: Dict[str, float]  # категории доходов
    expense_by_category: Dict[str, float]  # категории расходов

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str   # никнейм


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

