from fastapi import Depends, HTTPException
from .database import get_db
from sqlalchemy.orm import Session
from . import crud, models
import jwt

SECRET_KEY = "your_secret_key"

def get_current_user(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = crud.get_user_by_id(db, payload.get("user_id"))
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

def get_current_streamer(user: models.User = Depends(get_current_user)):
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Access forbidden")
    return user

def get_current_advertiser(user: models.User = Depends(get_current_user)):
    if user.role != "advertiser":
        raise HTTPException(status_code=403, detail="Access forbidden")
    return user
