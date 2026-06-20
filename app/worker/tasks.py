from app.worker.celery_app import celery_app
from app.database import SessionLocal
from app import models
import pandas as pd
import json, time, os, uuid, datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DOMESTIC_MERCHANTS = ['swiggy','ola','irctc','zomato','flipkart','blinkit','dunzo']

def parse_date_safe(d):
    try:
        return pd.to_datetime(str(d), dayfirst=True).strftime('%Y-%m-%d')
    except:
        return str(d)

def call_llm_with_retry(prompt, retries=3):
    for attempt in range(retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None

@celery_app.task
def process_csv(job_id: str, file_path: str):
    db = SessionLocal()
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        job.status = "processing"
        db.commit()

        # STEP A: Data Cleaning
        df = pd.read_csv(file_path)
        raw_count = len(df)

        df['date'] = df['date'].apply(parse_date_safe)
        df['amount'] = df['amount'].astype(str).str.replace('$', '', regex=False).astype(float)
        df['status'] = df['status'].str.upper().str.strip()
        df['currency'] = df['currency'].str.upper().str.strip()
        df['category'] = df['category'].fillna('Uncategorised').replace('', 'Uncategorised')
        df['txn_id'] = df['txn_id'].fillna('')
        df['notes'] = df['notes'].fillna('')
        df = df.drop_duplicates()
        clean_count = len(df)

        # STEP B: Anomaly Detection
        medians = df.groupby('account_id')['amount'].median()

        def is_outlier(row):
            median = medians.get(row['account_id'], 0)
            return row['amount'] > 3 * median if median > 0 else False

        df['is_anomaly'] = df.apply(is_outlier, axis=1)
        df['anomaly_reason'] = ''
        df.loc[df['is_anomaly'], 'anomaly_reason'] = 'Amount exceeds 3x account median'

        usd_domestic = (df['currency'] == 'USD') & \
                       (df['merchant'].str.lower().isin(DOMESTIC_MERCHANTS))
        df.loc[usd_domestic, 'is_anomaly'] = True
        df.loc[usd_domestic, 'anomaly_reason'] = 'USD used with domestic-only merchant'

        # STEP C: LLM Classification
        df['llm_category'] = ''
        df['llm_failed'] = False
        uncategorized = df[df['category'] == 'Uncategorised'].copy()

        if not uncategorized.empty:
            batch_text = "\n".join([
                f"{i}. merchant={row['merchant']}, amount={row['amount']}, notes={row['notes']}"
                for i, (_, row) in enumerate(uncategorized.iterrows())
            ])
            prompt = f"""Classify each transaction into exactly one category from:
Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other.

Transactions:
{batch_text}

Reply ONLY with a valid JSON array of strings, one per transaction, in order.
Example: ["Food", "Shopping"]"""

            result = call_llm_with_retry(prompt)
            if result:
                try:
                    clean = result.strip().replace('```json', '').replace('```', '')
                    categories = json.loads(clean)
                    for i, idx in enumerate(uncategorized.index):
                        if i < len(categories):
                            df.at[idx, 'llm_category'] = categories[i]
                            df.at[idx, 'category'] = categories[i]
                except:
                    df.loc[uncategorized.index, 'llm_failed'] = True
            else:
                df.loc[uncategorized.index, 'llm_failed'] = True

        # STEP D: LLM Narrative Summary
        top_merchants = df.groupby('merchant')['amount'].sum().nlargest(3).index.tolist()
        summary_input = {
            "total_inr": float(round(df[df['currency'] == 'INR']['amount'].sum(), 2)),
            "total_usd": float(round(df[df['currency'] == 'USD']['amount'].sum(), 2)),
            "top_merchants": top_merchants,
            "anomaly_count": int(df['is_anomaly'].sum())
        }

        narrative_prompt = f"""Given this financial data: {json.dumps(summary_input)}

Return ONLY a valid JSON object with these exact keys:
{{
  "total_spend_inr": <number>,
  "total_spend_usd": <number>,
  "top_merchants": ["m1","m2","m3"],
  "anomaly_count": <number>,
  "narrative": "<2-3 sentences about spending patterns>",
  "risk_level": "<low or medium or high>"
}}"""

        narrative_result = call_llm_with_retry(narrative_prompt)
        summary_data = {
            "total_spend_inr": summary_input['total_inr'],
            "total_spend_usd": summary_input['total_usd'],
            "top_merchants": top_merchants,
            "anomaly_count": summary_input['anomaly_count'],
            "narrative": "Summary unavailable due to LLM error.",
            "risk_level": "medium"
        }

        if narrative_result:
            try:
                clean = narrative_result.strip().replace('```json', '').replace('```', '')
                parsed = json.loads(clean)
                summary_data = {
                    "total_spend_inr": float(parsed.get('total_spend_inr', summary_input['total_inr'])),
                    "total_spend_usd": float(parsed.get('total_spend_usd', summary_input['total_usd'])),
                    "top_merchants": parsed.get('top_merchants', top_merchants),
                    "anomaly_count": int(parsed.get('anomaly_count', summary_input['anomaly_count'])),
                    "narrative": str(parsed.get('narrative', "Summary unavailable due to LLM error.")),
                    "risk_level": str(parsed.get('risk_level', 'medium')),
                }
            except:
                pass

        # Save transactions to DB
        for _, row in df.iterrows():
            txn = models.Transaction(
                id=str(uuid.uuid4()),
                job_id=job_id,
                txn_id=str(row.get('txn_id', '')),
                date=str(row.get('date', '')),
                merchant=str(row.get('merchant', '')),
                amount=float(row.get('amount', 0)),
                currency=str(row.get('currency', '')),
                status=str(row.get('status', '')),
                category=str(row.get('category', '')),
                account_id=str(row.get('account_id', '')),
                is_anomaly=bool(row.get('is_anomaly', False)),
                anomaly_reason=str(row.get('anomaly_reason', '')),
                llm_category=str(row.get('llm_category', '')),
                llm_failed=bool(row.get('llm_failed', False)),
            )
            db.add(txn)

        # Save summary
        job_summary = models.JobSummary(
            id=str(uuid.uuid4()),
            job_id=job_id,
            total_spend_inr=float(summary_data.get('total_spend_inr', 0)),
            total_spend_usd=float(summary_data.get('total_spend_usd', 0)),
            top_merchants=list(summary_data.get('top_merchants', [])),
            anomaly_count=int(summary_data.get('anomaly_count', 0)),
            narrative=str(summary_data.get('narrative', '')),
            risk_level=str(summary_data.get('risk_level', 'medium')),
        )
        db.add(job_summary)

        job.status = "completed"
        job.row_count_raw = raw_count
        job.row_count_clean = clean_count
        job.completed_at = datetime.datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()