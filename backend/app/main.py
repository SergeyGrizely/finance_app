from fastapi import FastAPI, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from . import database, models, schemas, crud, auth
from .database import engine, get_db
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, date
from .schemas import StatisticsOut
from . import email_service
from fastapi import Body
from .email_service import send_code, generate_code
from fastapi import BackgroundTasks
from fastapi import UploadFile, File
import json
from typing import List

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance API")

@app.get("/health")
def health():
    return {"status": "ok"}

# регистрация и верификация (без изменений, но проверьте импорты)
@app.post("/register/request")
def request_registration(
    background_tasks: BackgroundTasks,
    email: str = Body(...),
    password: str = Body(...),
    name: str = Body(...),
    db: Session = Depends(get_db)
):
    if crud.get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    code = crud.create_email_verification(db, email, password, name)

    background_tasks.add_task(email_service.send_code, email, code)

    return {"detail": "Код отправлен на email"}

@app.post("/register/confirm")
def confirm_registration(
    email: str = Body(...),
    code: str = Body(...),
    db: Session = Depends(get_db)
):
    from .models import EmailVerification  # если нужно, но можно импортировать сверху
    record = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.code == code,
        EmailVerification.expires_at > datetime.utcnow()
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Неверный код или срок действия истёк")

    user_data = schemas.UserCreate(
        email=record.email,
        password=record.password,
        name=record.name,
        is_verified=True
    )
    user = crud.create_user(db, user_data)

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

@app.put("/profile")
def update_profile(
    name: str = None,
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    pass

@app.get("/statistics", response_model=schemas.StatisticsOut)
def get_statistics(
    period: str = Query("month"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат start_date (используйте YYYY-MM-DD)")
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат end_date (используйте YYYY-MM-DD)")
    
    print(f"📊 API: period={period}, start={start}, end={end}, user={current_user.id}")
    
    stats = crud.get_user_statistics(
        db=db,
        owner_id=current_user.id,
        period=period,
        start_date=start,
        end_date=end
    )
    return stats

@app.get("/transactions/export")
def export_transactions(
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(models.Transaction).filter(
        models.Transaction.owner_id == current_user.id
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

@app.post("/transactions/import")
async def import_transactions(
    file: UploadFile = File(...),
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        data = json.loads(content)

        for item in data:
            tx = models.Transaction(
                amount=item["amount"],
                category=item["category"],
                note=item.get("note", ""),
                type=item.get("type", "expense"),
                date=date.fromisoformat(item["date"]),
                owner_id=current_user.id
            )
            db.add(tx)

        db.commit()

        return {"message": "Импорт выполнен"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка импорта: {e}")

@app.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(
    tx: schemas.TransactionCreate,
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return crud.create_transaction(db, owner_id=current_user.id, tx=tx)

@app.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_transactions_for_user(db, owner_id=current_user.id)

@app.put("/transactions/{tx_id}", response_model=schemas.TransactionOut)
def update_transaction(
    tx_id: int,
    tx: schemas.TransactionUpdate,
    current_user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_tx = db.query(models.Transaction).filter(
        models.Transaction.id == tx_id,
        models.Transaction.owner_id == current_user.id
    ).first()

    if not db_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.amount is not None:
        db_tx.amount = tx.amount
    if tx.category is not None:
        db_tx.category = tx.category
    if tx.note is not None:
        db_tx.note = tx.note
    if tx.type is not None:
        db_tx.type = tx.type
    if tx.date is not None:
        db_tx.date = tx.date

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