from fastapi import FastAPI, Depends
from .auth import get_current_streamer, get_current_advertiser

app = FastAPI()

@app.get("/streamer/home")
def streamer_home(user = Depends(get_current_streamer)):
    return {"message": "Добро пожаловать в кабинет стримера!"}

@app.get("/advertiser/home")
def advertiser_home(user = Depends(get_current_advertiser)):
    return {"message": "Добро пожаловать в кабинет рекламодателя!"}
