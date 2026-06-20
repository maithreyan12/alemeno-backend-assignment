from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, ForeignKey, Integer, Text
from app.database import Base
import uuid
import datetime

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    status = Column(String, default="pending")
    row_count_raw = Column(Integer)
    row_count_clean = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"))
    txn_id = Column(String)
    date = Column(String)
    merchant = Column(String)
    amount = Column(Float)
    currency = Column(String)
    status = Column(String)
    category = Column(String)
    account_id = Column(String)
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String)
    llm_category = Column(String)
    llm_failed = Column(Boolean, default=False)

class JobSummary(Base):
    __tablename__ = "job_summaries"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"))
    total_spend_inr = Column(Float)
    total_spend_usd = Column(Float)
    top_merchants = Column(JSON)
    anomaly_count = Column(Integer)
    narrative = Column(Text)
    risk_level = Column(String)