# AthletiQ Production Deployment Guide

This guide details how to build, containerize, and deploy the AthletiQ platform in development, staging, and production environments.

---

## 1. Prerequisites

- **Docker Engine**: v24.0+
- **Docker Compose**: v2.20+
- **Host Specifications**:
  - Minimum: 2 CPU cores, 4 GB RAM, 20 GB SSD storage
  - Recommended: 4 CPU cores, 8 GB RAM, 50 GB NVMe storage (for concurrent video processing)

---

## 2. Quick Local Deployment (Docker Compose)

To spin up the entire multi-container stack locally (PostgreSQL 17, FastAPI backend, and Nginx React frontend):

1. **Clone and enter repository**:
   ```bash
   git clone <repo-url>
   cd sports-injury-risk
   ```

2. **Start the stack**:
   ```bash
   docker compose up --build -d
   ```

3. **Verify running containers**:
   ```bash
   docker compose ps
   ```

4. **Access the application**:
   - Web Application: [http://localhost:3000](http://localhost:3000)
   - FastAPI Backend API: [http://localhost:8000](http://localhost:8000)
   - Interactive Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Healthcheck: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

5. **Stop the stack**:
   ```bash
   docker compose down
   ```

---

## 3. Production Deployment (Cloud Server / VPS)

### Step 1: Server Provisioning
Set up an Ubuntu 22.04 LTS / 24.04 LTS virtual machine on AWS EC2, GCP Compute Engine, or DigitalOcean Droplet.

Install Docker and Docker Compose:
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### Step 2: Configure Production Environment Variables
Copy `.env.production.example` to `.env.production`:
```bash
cp .env.production.example .env.production
```

Edit `.env.production` with secure values:
- Generate a strong JWT key: `openssl rand -hex 32`
- Set `DB_PASSWORD` to a secure 32-character password.
- Set `BACKEND_CORS_ORIGINS=["https://athletiq.yourdomain.com"]`
- Set `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID`.
- Set `UVICORN_WORKERS=4`.

### Step 3: Launch Production Containers
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
```

### Step 4: Verify Container Health & Status
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 4. SSL / TLS Setup with Certbot & Let's Encrypt

To serve HTTPS on ports 80 and 443 with automated SSL certificate renewal:

1. Install Certbot on host:
   ```bash
   sudo apt-get install -y certbot
   ```

2. Request certificate in standalone mode:
   ```bash
   sudo certbot certonly --standalone -d athletiq.yourdomain.com
   ```

3. Mount certificates into frontend Nginx container by adding volume mounts to `docker-compose.prod.yml`:
   ```yaml
   volumes:
     - /etc/letsencrypt:/etc/letsencrypt:ro
   ```

4. Update `frontend/nginx.conf` to listen on port 443 with SSL certificates.

---

## 5. Database Migrations & Seeding

Database migrations run automatically on container boot via `backend/entrypoint.sh`.

To manually run migrations inside the running container:
```bash
docker compose exec backend alembic upgrade head
```

To seed rich demo accounts (Coaches, Physios, Athletes, Biomechanical trials):
```bash
docker compose exec -e SEED_DEMO_DATA=true backend python seed_demo.py
```

---

## 6. Backup and Recovery

### PostgreSQL Database Backup
```bash
docker compose exec db pg_dump -U postgres sports_injury_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Database Restore
```bash
gunzip < backup_20261102_220000.sql.gz | docker compose exec -T db psql -U postgres -d sports_injury_db
```

### Video Uploads Backup
Archive the persistent uploads volume:
```bash
docker run --rm -v athletiq_prod_uploads_data:/volume -v $(pwd):/backup alpine tar -czf /backup/uploads_$(date +%Y%m%d).tar.gz -C /volume .
```
