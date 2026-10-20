# Sports Injury Risk Detection from Video

AI platform that analyses athlete movement videos: pose estimation (MediaPipe) -> biomechanics ->
anomaly detection -> injury-risk prediction -> weighted risk score -> corrective recommendations,
with role-based dashboards, alerts and PDF/Excel reports.

> Decision-support tool. Outputs are screening indicators, not medical diagnoses.

## Quick start (Docker)

```bash
cp .env.example .env        # edit SECRET_KEY and ADMIN_* values
docker compose up --build
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs
- Health:   http://localhost:8000/health

## Local development

```bash
# backend (SQLite by default, no extra services needed)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev                  # http://localhost:5173 (proxies /api to :8000)
```

## Tests

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## Optional: train the ML model

```bash
cd backend
python -m ml.train_injury_model --help
```
The platform works without a trained model (rule-based scoring); a model, if present at
`MODEL_PATH`, adds an ML probability alongside it.

## Risk score

`Injury Risk Score = 35% biomechanical deviations + 20% injury history + 20% movement asymmetry
+ 15% training load + 10% fatigue`. Categories: Low < 25, Moderate < 50, High < 75, Critical >= 75.

## Cloud deployment

Images are plain Docker: push `backend` and `frontend` to ECR/ACR and run them on ECS/App Service
(or any container host) with managed PostgreSQL, MongoDB-compatible storage and object storage.
