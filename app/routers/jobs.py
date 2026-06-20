from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.worker.tasks import process_csv
import uuid, os, shutil
from typing import Optional

router = APIRouter(prefix="/jobs", tags=["jobs"])
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    job_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/{job_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = models.Job(id=job_id, filename=file.filename, status="pending")
    db.add(job)
    db.commit()

    process_csv.delay(job_id, file_path)

    return {"job_id": job_id, "status": "pending"}

@router.get("/{job_id}/status")
def get_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status,
        "filename": job.filename,
        "created_at": str(job.created_at),
    }

    if job.status == "completed":
        summary = db.query(models.JobSummary).filter(
            models.JobSummary.job_id == job_id).first()
        if summary:
            response["summary"] = {
                "total_spend_inr": summary.total_spend_inr,
                "total_spend_usd": summary.total_spend_usd,
                "anomaly_count": summary.anomaly_count,
                "risk_level": summary.risk_level,
                "row_count_clean": job.row_count_clean,
            }
    return response

@router.get("/{job_id}/results")
def get_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is {job.status}")

    transactions = db.query(models.Transaction).filter(
        models.Transaction.job_id == job_id).all()
    summary = db.query(models.JobSummary).filter(
        models.JobSummary.job_id == job_id).first()
    anomalies = [t for t in transactions if t.is_anomaly]

    return {
        "job_id": job_id,
        "transactions": [
            {
                "txn_id": t.txn_id, "date": t.date,
                "merchant": t.merchant, "amount": t.amount,
                "currency": t.currency, "status": t.status,
                "category": t.category, "account_id": t.account_id,
                "is_anomaly": t.is_anomaly, "anomaly_reason": t.anomaly_reason,
            } for t in transactions
        ],
        "anomalies": [
            {
                "txn_id": t.txn_id, "merchant": t.merchant,
                "amount": t.amount, "reason": t.anomaly_reason
            } for t in anomalies
        ],
        "summary": {
            "total_spend_inr": summary.total_spend_inr,
            "total_spend_usd": summary.total_spend_usd,
            "top_merchants": summary.top_merchants,
            "anomaly_count": summary.anomaly_count,
            "narrative": summary.narrative,
            "risk_level": summary.risk_level,
        } if summary else {}
    }

@router.get("")
def list_jobs(status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Job)
    if status:
        query = query.filter(models.Job.status == status)
    jobs = query.all()
    return [
        {
            "job_id": j.id, "filename": j.filename,
            "status": j.status, "row_count_raw": j.row_count_raw,
            "created_at": str(j.created_at)
        } for j in jobs
    ]