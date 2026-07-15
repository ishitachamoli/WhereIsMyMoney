# WhereIsMyMoneyGoing — Setup Guide

Personal finance tracker that auto-classifies your bank transactions using AI.
Upload a bank statement (CSV/PDF) → transactions are parsed → auto-categorized → view spending analytics.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   Next.js App   │────▶│   FastAPI Backend     │────▶│  Database   │
│   (Port 3000)   │     │   (Port 8000)         │     │  SQLite/PG  │
└─────────────────┘     └──────────────────────┘     └─────────────┘
                             │
                       ┌─────┴──────┐
                       │ Classification│
                       │  Pipeline     │
                       ├───────────────┤
                       │ Tier 1: Rules │ ← Regex patterns (<1ms)
                       │ Tier 2: ML    │ ← Zero-shot BART (optional)
                       │ Tier 3: LLM   │ ← Ollama/Llama3 (optional)
                       └───────────────┘
```

## Prerequisites

| Requirement     | Version   | Notes                                    |
|-----------------|-----------|------------------------------------------|
| Python          | 3.11+     | Required for backend                     |
| Node.js         | 18+       | Required for frontend                    |
| pip             | latest    | Python package manager                   |
| Docker (opt)    | 24+       | For containerized deployment             |
| Ollama (opt)    | latest    | For Tier 3 LLM classification            |

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (lite = no ML model, just rule engine)
pip install -r requirements-lite.txt

# OR full install with ML classification (downloads ~1.5GB model)
# pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env if needed (defaults work for local dev with SQLite)

# Start the server
uvicorn app.main:app --reload --port 8000
```

The server starts at http://localhost:8000 with:
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

On first startup in development mode, SQLite database is auto-created and seeded with default categories.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at http://localhost:3000

### 3. (Optional) Ollama for LLM Classification

For Tier 3 LLM-based classification of complex transactions:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the model
ollama pull llama3.1:8b

# Ollama runs on http://localhost:11434 by default
```

---

## Docker Setup (Recommended for Full Stack)

Run the entire stack with one command:

```bash
# From project root
docker-compose up --build

# This starts:
#   - PostgreSQL on port 5432
#   - Backend on port 8000
#   - Frontend on port 3000
```

To run in detached mode:
```bash
docker-compose up -d --build

# View logs
docker-compose logs -f backend

# Stop everything
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

---

## Railway Deployment

The project includes Railway configuration for production deployment.

### Setup

1. Connect your GitHub repository to Railway
2. Railway will auto-detect `railway.toml` and use `Dockerfile.production`
3. Add environment variables in Railway dashboard:

| Variable          | Value                              |
|-------------------|------------------------------------|
| `DATABASE_URL`    | Your PostgreSQL connection string   |
| `ENVIRONMENT`     | `production`                        |
| `SECRET_KEY`      | Generate a secure random key        |
| `CORS_ORIGINS`    | Your frontend URL                   |
| `DEBUG`           | `false`                             |

### Build Configuration

- Uses `Dockerfile.production` (multi-stage build)
- Health check on `/health` endpoint
- Auto-restart on failure

---

## How to Test

### Upload a Sample Bank Statement

A sample HDFC bank statement CSV is included for testing:

```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@backend/tests/fixtures/sample_hdfc_statement.csv" \
  -F "user_id=1"
```

Or use the Swagger UI at http://localhost:8000/docs → POST `/api/v1/upload`

### Test Classification

```bash
# Classify a single transaction
curl -X POST http://localhost:8000/api/v1/classify \
  -H "Content-Type: application/json" \
  -d '{"description": "UPI-SWIGGY-ORDERS@PAYTM", "amount": -450.0}'

# Batch classify
curl -X POST http://localhost:8000/api/v1/classify/batch \
  -H "Content-Type: application/json" \
  -d '{"transactions": [
    {"description": "NETFLIX.COM SUBSCRIPTION", "amount": -649},
    {"description": "SALARY CREDIT ACME CORP", "amount": 85000},
    {"description": "ATM-CASH WDL-STATE BANK", "amount": -10000}
  ]}'
```

### View Analytics

```bash
# Spending by category
curl "http://localhost:8000/api/v1/analytics/spending-by-category?user_id=1"

# Income vs expenses
curl "http://localhost:8000/api/v1/analytics/income-vs-expenses?user_id=1"

# Summary
curl "http://localhost:8000/api/v1/analytics/summary?user_id=1"
```

### Run Integration Tests

```bash
cd backend
python tests/run_tests.py
```

---

## Supported Banks

| Bank          | CSV | PDF | Auto-detect |
|---------------|-----|-----|-------------|
| HDFC Bank     | ✅  | ✅  | ✅          |
| ICICI Bank    | ✅  | ✅  | ✅          |
| SBI           | ✅  | ✅  | ✅          |
| Axis Bank     | ✅  | ✅  | ✅          |
| Kotak Mahindra| ✅  | ✅  | ✅          |
| IDFC First    | ✅  | ✅  | ✅          |

**Tip:** If bank auto-detection fails, rename your file to include the bank name (e.g., `hdfc_jan2024.csv`).

---

## Classification Pipeline

Transactions are classified through a 3-tier pipeline:

| Tier | Method      | Speed  | Accuracy | Requires           |
|------|-------------|--------|----------|---------------------|
| 1    | Rule Engine | <1ms   | ~95%     | Nothing (built-in)  |
| 2    | ML (BART)   | ~200ms | ~85%     | `transformers` pkg  |
| 3    | LLM (Ollama)| ~300ms | ~90%     | Ollama running      |

- **Tier 1** handles ~80% of transactions via merchant name regex patterns
- **Tier 2** activates only when rules are unsure (requires `requirements.txt` full install)
- **Tier 3** activates only when ML is also unsure (requires Ollama running locally)

The pipeline escalates progressively — most transactions never leave Tier 1.

---

## API Endpoints

| Method | Endpoint                              | Description                    |
|--------|---------------------------------------|--------------------------------|
| POST   | `/api/v1/upload`                      | Upload bank statement          |
| GET    | `/api/v1/upload/statements`           | List uploaded statements       |
| GET    | `/api/v1/transactions`                | List transactions (paginated)  |
| POST   | `/api/v1/transactions`                | Create transaction manually    |
| PUT    | `/api/v1/transactions/{id}`           | Update transaction             |
| DELETE | `/api/v1/transactions/{id}`           | Delete transaction             |
| GET    | `/api/v1/analytics/spending-by-category` | Spending breakdown          |
| GET    | `/api/v1/analytics/timeline`          | Spending timeline              |
| GET    | `/api/v1/analytics/income-vs-expenses`| Income vs expenses             |
| GET    | `/api/v1/analytics/summary`           | Summary statistics             |
| GET    | `/api/v1/categories`                  | List categories                |
| POST   | `/api/v1/categories`                  | Create custom category         |
| POST   | `/api/v1/classify`                    | Classify single transaction    |
| POST   | `/api/v1/classify/batch`              | Classify multiple transactions |
| POST   | `/api/v1/classify/feedback`           | Submit correction              |
| GET    | `/api/v1/classify/stats`              | Classification accuracy stats  |

---

## Project Structure

```
whereIsMyMoneyGoing/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── routers/        # API endpoints
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/
│   │       ├── bank_parser.py           # Multi-bank CSV/PDF parser
│   │       ├── transaction_service.py   # CRUD logic
│   │       ├── analytics_service.py     # Analytics queries
│   │       └── classification/          # AI classification pipeline
│   │           ├── pipeline.py          # Orchestrator
│   │           ├── rule_engine.py       # Tier 1: Regex rules
│   │           ├── ml_classifier.py     # Tier 2: Zero-shot ML
│   │           ├── llm_classifier.py    # Tier 3: Ollama LLM
│   │           ├── categories.py        # Category taxonomy
│   │           ├── confidence.py        # Scoring logic
│   │           └── rules/               # Rule definitions
│   ├── tests/
│   │   ├── fixtures/       # Sample bank statements
│   │   └── test_classification.py
│   ├── requirements.txt          # Full (with ML)
│   ├── requirements-lite.txt     # Lite (rules only)
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/                # Next.js app directory
│   ├── components/         # React components
│   ├── lib/                # API client, utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # Full stack orchestration
├── Dockerfile.production   # Multi-stage production build
├── railway.toml            # Railway deployment config
└── SETUP.md               # This file
```

---

## Troubleshooting

### Backend won't start: `ModuleNotFoundError`

Make sure you're in the virtual environment and dependencies are installed:
```bash
cd backend
source venv/bin/activate
pip install -r requirements-lite.txt
```

### `No module named 'sqlite3'`

Your Python installation may not have sqlite3. Install `pysqlite3-binary`:
```bash
pip install pysqlite3-binary
```
The app auto-fallbacks to pysqlite3 if sqlite3 is unavailable.

### Upload fails with "Could not detect bank"

Rename your file to include the bank name: `hdfc_statement.csv`, `icici_jan2024.csv`, etc.

### Classification returns "Other" for everything

- Check that default categories are seeded (happens automatically in dev mode)
- If using ML classification, ensure `transformers` and `torch` are installed
- If using LLM, ensure Ollama is running: `curl http://localhost:11434/api/tags`

### Frontend can't connect to backend

Check CORS settings in `.env`:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Docker: Database connection refused

Wait for PostgreSQL health check to pass. The backend has `depends_on` with health check condition.

### Port already in use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different ports
uvicorn app.main:app --port 8001
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev -- --port 3001
```

---

## GitHub Actions Auto-Deploy to EC2

The repo auto-deploys to EC2 on every push to `main` using GitHub Actions.

### One-Time Setup

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add these three secrets:

| Secret | Value | Example |
|--------|-------|---------|
| `EC2_HOST` | EC2 public IP or domain | `54.123.45.67` or `ec2.example.com` |
| `EC2_USER` | SSH username | `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu) |
| `EC2_SSH_KEY` | Private SSH key file contents | (paste the `.pem` file as-is, including BEGIN/END lines) |

### How It Works

1. You push code to `main`
2. GitHub Actions workflow triggers automatically
3. Workflow SSHs into EC2 and runs deployment script:
   ```bash
   cd ~/whereIsMyMoneyGoing
   git pull origin main
   docker-compose down
   docker-compose up -d --build
   ```
4. Health check workflow verifies:
   - Backend is responding at `/health`
   - Frontend is responding at `/`
   - Both wait 30s for services to fully boot

### First-Time EC2 Setup

Before GitHub Actions can deploy, your EC2 instance needs:

```bash
# Install Docker and Docker Compose
sudo yum update -y  # Amazon Linux
sudo yum install docker -y
sudo usermod -aG docker ec2-user
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone the repo
cd ~
git clone https://github.com/YOUR-USERNAME/whereIsMyMoneyGoing.git

# Copy and configure .env file
cd whereIsMyMoneyGoing
cp .env.example .env
# Edit .env with your database URL, API keys, etc.
```

### Troubleshooting

- **"Permission denied (publickey)"**: Check your `EC2_SSH_KEY` contains the full `.pem` file with BEGIN/END lines
- **"Connection refused"**: Check `EC2_HOST` is your EC2's public IP and SSH is enabled on port 22
- **Health check fails**: Docker services may need more than 30s to boot; increase sleep time in `.github/workflows/health-check.yml`

---

## EC2 Deployment (Docker Compose)

Deploy the full stack on a single EC2 instance with Docker Compose. This is a simple, cost-effective production setup.

### Prerequisites

- AWS account with EC2 access
- EC2 instance (Amazon Linux 2023 or Ubuntu 22.04)
- Instance type: `t3.micro` or larger (free tier eligible)
- Security group allowing:
  - Port 80 (HTTP)
  - Port 443 (HTTPS) — for future SSL setup
  - SSH access (port 22) for management

### Quick Deploy

SSH into your EC2 instance and run:

```bash
curl -sSL https://raw.githubusercontent.com/tchamoli/whereIsMyMoneyGoing/main/deploy-ec2.sh | bash
```

This script will:
1. Install Docker and Docker Compose
2. Clone the repository
3. Create a `.env` file with secure database password
4. Build and start all services (PostgreSQL, Backend, Frontend, Nginx)

### Manual Setup

If you prefer manual setup:

```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-ec2-ip

# Install Docker
sudo yum update -y && sudo yum install -y docker
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone https://github.com/tchamoli/whereIsMyMoneyGoing.git
cd whereIsMyMoneyGoing

# Create .env file with secure credentials
cat > .env << 'EOF'
DB_PASSWORD=$(openssl rand -hex 16)
CORS_ORIGINS=*
NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8080
EOF

# Start services
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### Architecture

The `docker-compose.yml` orchestrates:

```
┌─────────────────────────────────────────────┐
│ EC2 Instance                                │
│ ┌───────────────────────────────────────┐   │
│ │ Nginx (Port 80/443)                   │   │
│ │ - Routes /api/* → Backend (8080)      │   │
│ │ - Routes /* → Frontend (3000)         │   │
│ ├───────────────────────────────────────┤   │
│ │ Frontend (Port 3000)                  │   │
│ │ - Next.js app                         │   │
│ ├───────────────────────────────────────┤   │
│ │ Backend (Port 8080)                   │   │
│ │ - FastAPI server                      │   │
│ │ - Depends on: db (healthcheck)        │   │
│ ├───────────────────────────────────────┤   │
│ │ PostgreSQL (Port 5432)                │   │
│ │ - Persistent: postgres_data volume    │   │
│ └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Environment Variables

Create `.env` file in project root:

```bash
DB_PASSWORD=<secure-random-password>
CORS_ORIGINS=*
NEXT_PUBLIC_API_URL=http://<your-ec2-public-ip>:8080
```

### Accessing the Application

Once deployed:

```bash
# Frontend
http://<your-ec2-public-ip>

# Backend API
http://<your-ec2-public-ip>:8080
http://<your-ec2-public-ip>:8080/docs  (Swagger UI)
http://<your-ec2-public-ip>:8080/health  (Health check)
```

### SSL/TLS Setup (Optional)

For production, use Let's Encrypt with Certbot:

```bash
# Install Certbot
sudo yum install -y certbot python3-certbot-nginx

# Request certificate
sudo certbot certonly --nginx -d your-domain.com

# Copy certificates to certbot volumes
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./certbot/conf/live/your-domain.com/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./certbot/conf/live/your-domain.com/

# Restart Nginx in Docker
docker-compose restart nginx
```

### Monitoring & Maintenance

```bash
# Check service status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Stop and remove data
docker-compose down -v

# Backup database
docker-compose exec db pg_dump -U wimm_user wimm > backup.sql

# Restore database
docker-compose exec -T db psql -U wimm_user wimm < backup.sql
```

### Cost Estimate

- EC2: t3.micro free tier (12 months), then ~$0.01/hour
- No additional charges for Docker/Docker Compose
- Minimal data transfer costs
- **Total first year: Free (t3.micro free tier)**

---

## AWS App Runner Deployment

### Prerequisites
- AWS CLI configured (`aws configure`)
- Docker installed locally
- An AWS account with permissions to create ECR repositories and App Runner services

### Quick Deploy

```bash
# From project root
./deploy-aws.sh ap-south-1
```

This script:
1. Logs into ECR in your AWS account
2. Creates ECR repositories (wimm-backend, wimm-frontend)
3. Builds and pushes Docker images to ECR
4. Prints next steps for App Runner setup

### Manual Setup (AWS Console)

1. **Create RDS PostgreSQL Database**
   - AWS Console → RDS → Create database
   - Engine: PostgreSQL (version 13+)
   - Instance class: db.t3.micro (free tier eligible)
   - Allocated storage: 20 GB
   - Public access: No (use VPC)
   - Note the endpoint (e.g., `wimm-db.12345.ap-south-1.rds.amazonaws.com`)

2. **Backend Service (App Runner)**
   - AWS Console → App Runner → Create service
   - Image: Select ECR → `wimm-backend:latest`
   - Port: `8080`
   - vCPU: 0.25 (free tier)
   - Memory: 0.5 GB (free tier)
   - Environment variables:
     ```
     DATABASE_URL=[REDACTED:database-connection-string]
     CORS_ORIGINS=https://<frontend-app-runner-url>
     ENVIRONMENT=production
     SECRET_KEY=<generate-secure-key>
     ```
   - Note the service URL (e.g., `https://xxxx.ap-south-1.apprunner.amazonaws.com`)

3. **Frontend Service (App Runner)**
   - AWS Console → App Runner → Create service
   - Image: Select ECR → `wimm-frontend:latest`
   - Port: `3000`
   - vCPU: 0.25 (free tier)
   - Memory: 0.5 GB (free tier)
   - Environment variables:
     ```
     NODE_ENV=production
     NEXT_PUBLIC_API_URL=https://<backend-app-runner-url>
     ```

4. **Update Backend with Frontend URL**
   - Backend service → Configuration → Edit
   - Add to environment variables: `CORS_ORIGINS=https://<frontend-app-runner-url>`

### Cost Estimate (Free Tier)

- App Runner: Free tier covers up to 2 services ($0.005/GB-hour after)
- RDS: Free tier covers 12 months of db.t3.micro ($0.015/hour after)
- ECR: $0.10/GB stored, $0.09/GB data transfer

---

## Environment Variables

| Variable             | Default                        | Description                      |
|----------------------|--------------------------------|----------------------------------|
| `DATABASE_URL`       | `sqlite:///./wimm_dev.db`      | Database connection string       |
| `ENVIRONMENT`        | `development`                  | `development` or `production`    |
| `SECRET_KEY`         | `change-me-in-production`      | JWT secret key                   |
| `DEBUG`              | `true`                         | Enable debug logging             |
| `MAX_UPLOAD_SIZE_MB` | `10`                           | Max upload file size             |
| `CORS_ORIGINS`       | `http://localhost:3000,...`     | Allowed CORS origins             |
| `NEXT_PUBLIC_API_URL`| `http://localhost:8000`        | Backend URL for frontend         |
