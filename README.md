# AI-Powered Transaction Processing Pipeline

## Stack
- FastAPI + PostgreSQL + Celery + Redis + Gemini AI
- Fully containerised with Docker Compose

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/maithreyan12/alemeno-backend-assignment.git
cd alemeno-backend-assignment
```

### 2. Add your Gemini API key
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Start everything
```bash
docker compose up --build
```

## API Endpoints

### Upload CSV
```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@transactions.csv"
```

### Check Status
```bash
curl http://localhost:8000/jobs/{job_id}/status
```

### Get Results
```bash
curl http://localhost:8000/jobs/{job_id}/results
```

### List All Jobs
```bash
curl http://localhost:8000/jobs
```

## API Docs
Visit http://localhost:8000/docs for interactive Swagger UI
