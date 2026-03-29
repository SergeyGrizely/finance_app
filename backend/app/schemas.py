import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


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


class CategoryBase(BaseModel):
    name: str
    type: str


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class AccountBase(BaseModel):
    name: str
    type: str = "cash"
    currency: str = "RUB"
    balance: float = 0.0
    is_active: bool = True


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    currency: Optional[str] = None
    balance: Optional[float] = None
    is_active: Optional[bool] = None


class AccountOut(AccountBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class BudgetBase(BaseModel):
    name: str
    amount: float
    period: str = "monthly"
    start_date: datetime.date
    end_date: Optional[datetime.date] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    period: Optional[str] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None


class BudgetOut(BudgetBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class DebtEventBase(BaseModel):
    event_type: str
    amount: float
    event_date: Optional[datetime.date] = None
    note: Optional[str] = ""
    account_id: Optional[int] = None


class DebtEventCreate(DebtEventBase):
    pass


class DebtEventOut(DebtEventBase):
    id: int
    debt_id: int
    event_date: datetime.date

    class Config:
        from_attributes = True


class DebtBase(BaseModel):
    person_name: str
    direction: str
    principal_amount: float
    currency: str = "RUB"
    issued_at: Optional[datetime.date] = None
    due_date: Optional[datetime.date] = None
    note: Optional[str] = ""
    account_id: Optional[int] = None


class DebtCreate(DebtBase):
    pass


class DebtUpdate(BaseModel):
    person_name: Optional[str] = None
    direction: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    issued_at: Optional[datetime.date] = None
    due_date: Optional[datetime.date] = None
    note: Optional[str] = None
    account_id: Optional[int] = None


class DebtOut(DebtBase):
    id: int
    current_balance: float
    status: str
    user_id: int
    issued_at: datetime.date
    events: List[DebtEventOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    amount: float
    category_id: int
    account_id: Optional[int] = None
    note: Optional[str] = ""
    type: str = "expense"


class TransactionCreate(TransactionBase):
    date: Optional[datetime.date] = None


class TransactionOut(TransactionBase):
    id: int
    date: datetime.date
    owner_id: int
    category: Optional[CategoryOut] = None
    account: Optional[AccountOut] = None

    class Config:
        from_attributes = True


class TransactionsList(BaseModel):
    transactions: List[TransactionOut]


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    note: Optional[str] = None
    type: Optional[str] = None
    date: Optional[datetime.date] = Field(default=None, description="Дата транзакции")


class TransactionExport(BaseModel):
    amount: float
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    account_id: Optional[int] = None
    note: Optional[str] = ""
    type: str
    date: datetime.date


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
