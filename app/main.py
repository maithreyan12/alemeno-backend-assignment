from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import jobs

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Transaction Processing API")

app.include_router(jobs.router)

@app.get("/")
def root():
    return {"message": "Transaction Processing API is running"}