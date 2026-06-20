# AI-Powered Transaction Processing Pipeline

## Architecture Diagram

![Architecture](https://github.com/user-attachments/assets/87f61e0c-7718-4c02-9b87-b70eec957c5c)

![Architecture Flow](https://github.com/user-attachments/assets/702f08cd-8604-40c2-abf1-02be1a0ba6d0)

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

## Submission Checklist
- ✅ GitHub repo (public)
- ✅ Architecture diagram (above)
- 🎥 Demo video: [Watch here](https://your-loom-link-here)
