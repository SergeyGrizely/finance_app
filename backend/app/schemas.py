from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, date

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
        orm_mode = True

class TransactionBase(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    type: str = "expense"

class TransactionCreate(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    type: str = "expense"
    date: Optional[date] = None  # ✅ теперь должно работать

class TransactionOut(TransactionBase):
    id: int
    date: date
    created_at: datetime
    owner_id: int

    class Config:
        orm_mode = True

class TransactionsList(BaseModel):
    transactions: List[TransactionOut]

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    category: Optional[str] = None
    note: Optional[str] = None
    type: Optional[str] = None
    date: Optional[date] = None

class StatisticsOut(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    income_by_category: Dict[str, float]
    expense_by_category: Dict[str, float]

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str