# SkillMatch AI — Production Deployment Guide

This guide details the deployment topology, environment configuration, database management, and maintenance procedures for running **SkillMatch AI** in production.

---

## 1. System Architecture

SkillMatch AI is containerized and composed of the following services:

| Service | Container Image / Source | Role | Port (Internal/Host) |
| :--- | :--- | :--- | :--- |
| **`web`** | Nginx Alpine (`./frontend`) | Static SPA host + reverse proxy to `/api/` | `8080` (HTTP) |
| **`api`** | Python 3.12-slim (`./backend`) | FastAPI application server (Uvicorn) | `8000` |
| **`worker`** | Python 3.12-slim (`./backend`) | APScheduler background job runner & ingestion | Background |
| **`dev-db` / RDS** | `pgvector/pgvector:pg17` | PostgreSQL with pgvector extension | `5432` |
| **`mailpit` / SMTP** | `axllent/mailpit` (or SendGrid/SES) | Transactional email & digest notifications | `8025` (Web UI) / `1025` (SMTP) |

```mermaid
graph TD
    Client[Browser / Client] -->|HTTP 8080| Web[Nginx Web SPA]
    Web -->|Static Assets| Assets[Vite Bundle]
    Web -->|/api/v1/ Proxy| API[FastAPI Server :8000]
    API --> DB[(PostgreSQL + pgvector)]
    Worker[APScheduler Worker] --> DB
    Worker -->|Ingestion Feeds| ExtAPIs[Adzuna / Greenhouse / Lever / Ashby]
    Worker -->|Digests / Verification| SMTP[SMTP / Mailpit]
    API -->|Emails / SSE| SMTP
```

---

## 2. Prerequisites

- **Docker & Docker Compose v2+**
- **PostgreSQL 15+** with the **`pgvector`** extension enabled (e.g., Neon Postgres, AWS RDS, Supabase, or self-hosted container).
- **Domain & SSL**: Valid domain with Let's Encrypt / Cloudflare SSL termination.

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` and configure production secrets:

```bash
cp .env.example .env
```

### Essential Production Variables

```ini
# Application Environment
ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://skillmatch.example.com

# Database (PostgreSQL with pgvector)
DATABASE_URL=postgresql+psycopg://skillmatch_user:StrongPassword123@db-host:5432/skillmatch

# Security & Authentication
SECRET_KEY=generate-a-strong-64-character-hex-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Ingestion & Adzuna Credentials
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

# Email / Notifications (SMTP)
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=AKIAEXAMPLEUSER
SMTP_PASS=ExampleAppPassword
SMTP_FROM=no-reply@skillmatch.example.com
SMTP_USE_TLS=true

# AI & Embeddings
SEMANTIC_ENABLED=true
EMBEDDING_PROVIDER=local   # or 'openai'
OPENAI_API_KEY=            # if EMBEDDING_PROVIDER=openai
```

---

## 4. Deploying with Docker Compose

### 4.1 Production Launch

To build images and launch services in detached mode:

```bash
docker compose up -d --build
```

The startup lifecycle handles:
1. `wait_db`: Waits for PostgreSQL to accept connections and verifies `vector` extension.
2. `alembic upgrade head`: Applies all schema migrations automatically.
3. `seed`: Seeds initial reference catalog (skills, sample companies, admin user).
4. `uvicorn`: Boots FastAPI on port `8000`.
5. `worker`: Boots APScheduler worker to monitor RSS feeds, ATS APIs, and notification queues.
6. `web`: Serves compiled Vite SPA via Nginx on port `8080`.

### 4.2 Verifying Service Health

Verify that all containers are healthy:

```bash
docker compose ps
```

Health endpoints:
- API: `http://localhost:8000/api/v1/health`
- Web SPA: `http://localhost:8080/`
- Worker: verified via `python -m app.worker_health`

---

## 5. Database Migrations

SkillMatch AI uses Alembic for schema migrations. To run or check migrations manually:

```bash
# Check current migration revision
docker compose exec api alembic current

# Upgrade to latest revision
docker compose exec api alembic upgrade head

# Create a new migration revision
docker compose exec api alembic revision -m "describe_change"
```

---

## 6. Reverse Proxy & SSL (Nginx / Caddy)

Place a reverse proxy in front of the container setup for TLS termination:

### Sample Nginx Configuration (`/etc/nginx/sites-available/skillmatch.conf`)

```nginx
server {
    listen 80;
    server_name skillmatch.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name skillmatch.example.com;

    ssl_certificate /etc/letsencrypt/live/skillmatch.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skillmatch.example.com/privkey.pem;

    client_max_body_size 10M; # Required for PDF resume uploads

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Enable SSE (Server-Sent Events) for real-time notifications
    location /api/v1/notifications/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

---

## 7. Operational Maintenance & Monitoring

### Viewing Logs

```bash
# View all service logs
docker compose logs -f

# View API logs only
docker compose logs -f api

# View background worker ingestion logs
docker compose logs -f worker
```

### Ingestion Triggers

The worker runs scheduled ingestion every hour. You can trigger an ad-hoc ingestion via the API or CLI:

```bash
# Ad-hoc ingestion inside container
docker compose exec api python -m app.ingest_now
```

### Backup & Disaster Recovery

```bash
# Dump PostgreSQL database
pg_dump -U skillmatch -d skillmatch -Fc -f "skillmatch_backup_$(date +%Y%m%d).dump"

# Restore database
pg_restore -U skillmatch -d skillmatch -c "skillmatch_backup_YYYYMMDD.dump"
```
