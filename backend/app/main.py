from fastapi import FastAPI, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from . import database, models, schemas, crud, auth
from .database import engine, get_db
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from .schemas import StatisticsOut
from . import email_service, schemas
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Body
from .email_service import send_code, generate_code

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance API")

verification_codes = {}  # хранение временных  кодов (email: код)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/register/request")
def request_registration(
    email: str = Body(...),
    password: str = Body(...),
    name: str = Body(...),
    db: Session = Depends(get_db)
):
    # Проверка, есть ли уже пользователь
    if crud.get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    # Сохраняем временного пользователя в EmailVerification
    code = crud.create_email_verification(db, email, password, name)

    # Отправка кода по email
    try:
        send_code(email, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки кода: {e}")

    return {"detail": "Код отправлен на email"}

@app.post("/register/confirm")
def confirm_registration(
    email: str = Body(...),
    code: str = Body(...),
    db: Session = Depends(get_db)
):
    from . import crud, schemas

    # Проверка кода через БД
    record = db.query(crud.EmailVerification).filter(
        crud.EmailVerification.email == email,
        crud.EmailVerification.code == code,
        crud.EmailVerification.expires_at > datetime.utcnow()
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Неверный код или срок действия истёк")

    # Создаём пользователя и ставим is_verified=True
    user_data = schemas.UserCreate(
        email=record.email,
        password=record.password,
        name=record.name,
        is_verified=True      # теперь это законно
    )
    user = crud.create_user(db, user_data)


    # Удаляем запись с кодом
    db.delete(record)
    db.commit()

    return {"detail": "Регистрация успешна", "user_id": user.id}

@app.get("/profile", response_model=schemas.UserOut)
def get_profile(current_user = Depends(auth.get_current_user)):
    return current_user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    access_token_expires = timedelta(minutes=1440)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# Профиль пользователя
@app.get("/profile", response_model=schemas.UserOut)
def get_profile(current_user = Depends(auth.get_current_user)):
    return current_user

@app.put("/profile")
def update_profile(
    name: str = None,
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Обновление имени пользователя и т.д.
    pass

@app.get("/statistics", response_model=schemas.StatisticsOut)
def get_statistics(
    period: str = "month",
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    stats = crud.get_user_statistics(db=db, owner_id=current_user.id, period=period)
    return stats

# Transactions
@app.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(tx: schemas.TransactionCreate, current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.create_transaction(db, owner_id=current_user.id, tx=tx)

@app.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(current_user = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.get_transactions_for_user(db, owner_id=current_user.id)

from fastapi import Body

@app.put("/transactions/{tx_id}", response_model=schemas.TransactionOut)
def update_transaction(
    tx_id: int,
    tx: schemas.TransactionCreate = Body(...),
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id,
        models.Transaction.owner_id == current_user.id
    ).first()

    if not db_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db_tx.amount = tx.amount
    db_tx.category = tx.category
    db_tx.note = tx.note
    db_tx.type = tx.type
    db.commit()
    db.refresh(db_tx)
    return db_tx

@app.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(
    tx_id: int = Path(..., description="ID транзакции"),
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id,
        models.Transaction.owner_id == current_user.id
    ).first()
    
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(tx)
    db.commit()
    return