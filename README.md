# Sports Injury Risk Detection

AI-powered platform that analyzes athlete movement videos, extracts human poses, evaluates biomechanical indicators, and provides preliminary injury-risk screening.

## Project Setup

### Prerequisites

- Node.js (v22+)
- Python 3.8 - 3.14 (Tested with 3.14)
- PostgreSQL 17

### Environment Variables

1. Copy `.env.example` to `.env` in the root (for reference) and `backend/.env`.
2. Update the `DATABASE_URL` with your PostgreSQL credentials.

### Frontend Setup

1. Open a terminal and navigate to `frontend/`.
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`

### Backend Setup

1. Open a terminal and navigate to `backend/`.
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt` (Note: wait for all dependencies like OpenCV, FastAPI, SQLAlchemy, and MediaPipe to finish installing).
5. Run the FastAPI server: `python -m uvicorn app.main:app --reload`

## Troubleshooting

- **PostgreSQL**: Ensure the PostgreSQL service is running and `psql` is added to your system PATH (`C:\Program Files\PostgreSQL\17\bin`).
- **Python Dependencies**: If a package fails to install, try upgrading pip: `python -m pip install --upgrade pip`.

### Database Setup (Docker)

1. Ensure Docker Desktop is running.
2. In the project root, start the PostgreSQL container: `docker-compose up -d`
3. Run Alembic migrations from the `backend/` directory to create the tables:
   ```bash
   cd backend
   .\.venv\Scripts\activate
   alembic upgrade head
   ```

### Backend Structure

- `app/api/`: API routers and endpoints
- `app/models/`: SQLAlchemy database models
- `app/schemas/`: Pydantic models (data validation)
- `app/services/`: Business logic and external service integrations
- `app/db/`: Database configuration and sessions
- `tests/`: Pytest test suite

To run tests:
```bash
cd backend
pytest -v
```

## Authentication & Google OAuth 2.0 Setup

The application supports both standard email/password authentication and **Sign in / Sign up with Google (OAuth 2.0 / OpenID Connect)**.

### Quick Setup for Google Authentication:
1. Create a Web OAuth 2.0 Client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Set Authorized JavaScript origins to:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
3. Set your Client ID in `backend/.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```
4. Set your Client ID in `frontend/.env`:
   ```env
   VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```
5. Full step-by-step instructions: see [Google OAuth Setup Guide](docs/GOOGLE_AUTH_SETUP.md).

## Documentation
- [Google OAuth Setup Guide](docs/GOOGLE_AUTH_SETUP.md): Step-by-step Google Cloud Console configuration, security architecture, and manual verification checklist.
- [Datasets and Movement Analysis Workflow](docs/DATASETS_AND_WORKFLOW.md): Detailed information on computer vision datasets (Human3.6M, COCO, etc.), clinical references (FIFA), and the biomechanical analysis workflow.

