# Sports Injury Risk Detection from Video

An AI-powered sports injury risk detection platform that analyzes athlete movement videos using computer vision, human pose estimation, biomechanics, and machine learning.

## Project Overview

This system will eventually provide:
- Computer vision-based movement analysis
- Human pose estimation and joint tracking
- Biomechanical calculations and movement metrics
- Injury risk prediction and scoring
- Corrective exercise recommendations
- Role-based access for athletes, coaches, physiotherapists, sports scientists, and administrators

**Current Status: Milestone 1 - Foundation Complete**

## Architecture

The system follows a modular monolith architecture designed for future microservices decomposition:

```
Sports_INJURYRisk/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py       # Application entry point
│   │   ├── core/         # Configuration, security, dependencies
│   │   ├── db/           # Database configuration
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── api/routes/   # API endpoints
│   │   └── services/     # Business logic
│   ├── alembic/          # Database migrations
│   ├── tests/            # Backend tests
│   └── requirements.txt  # Python dependencies
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # Reusable components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API client
│   │   └── context/      # React context
│   └── package.json      # Node dependencies
├── datasets/             # Dataset integration
│   ├── registry/         # Dataset metadata
│   ├── raw/              # Raw datasets (not in git)
│   ├── processed/        # Processed datasets (not in git)
│   └── sample/           # Sample dataset for testing
├── scripts/              # Utility scripts
│   └── dataset/          # Dataset validation
└── docker-compose.yml    # Docker configuration
```

## Tech Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Password Hashing**: bcrypt (passlib)
- **Validation**: Pydantic

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **HTTP Client**: Axios

### DevOps
- **Containerization**: Docker
- **Orchestration**: Docker Compose
- **Version Control**: Git

## Repository Structure

Detailed structure and purpose of each directory:

```
backend/
├── app/
│   ├── main.py                 # FastAPI application setup
│   ├── core/
│   │   ├── config.py          # Application configuration
│   │   ├── security.py        # JWT authentication logic
│   │   └── dependencies.py    # RBAC dependencies
│   ├── db/
│   │   ├── database.py        # Database session management
│   │   └── base.py            # Base model import
│   ├── models/
│   │   ├── user.py            # User model
│   │   └── athlete.py         # Athlete model
│   ├── schemas/
│   │   ├── auth.py            # Authentication schemas
│   │   ├── user.py            # User schemas
│   │   ├── athlete.py         # Athlete schemas
│   │   └── dataset.py         # Dataset schemas
│   ├── api/routes/
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── users.py           # User management endpoints
│   │   ├── athletes.py        # Athlete management endpoints
│   │   └── datasets.py        # Dataset endpoints
│   └── services/
│       ├── auth_service.py    # Authentication business logic
│       ├── athlete_service.py # Athlete business logic
│       └── dataset_service.py # Dataset business logic
├── alembic/
│   ├── env.py                 # Alembic environment
│   ├── script.py.mako         # Migration template
│   └── versions/              # Migration files
├── tests/
│   ├── conftest.py            # Test configuration
│   ├── test_auth.py           # Authentication tests
│   ├── test_athletes.py       # Athlete tests
│   └── test_datasets.py       # Dataset tests
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── Dockerfile                # Docker configuration

frontend/
├── src/
│   ├── main.jsx              # React entry point
│   ├── App.jsx               # Main application component
│   ├── index.css             # Global styles
│   ├── components/
│   │   └── Layout.jsx         # Main layout component
│   ├── pages/
│   │   ├── Login.jsx          # Login page
│   │   ├── Register.jsx       # Registration page
│   │   ├── Dashboard.jsx      # Dashboard page
│   │   ├── AthleteList.jsx    # Athlete list page
│   │   ├── AthleteProfile.jsx # Athlete profile page
│   │   └── Profile.jsx        # User profile page
│   ├── services/
│   │   └── api.js             # API client
│   └── context/
│       └── AuthContext.jsx    # Authentication context
├── package.json              # Node dependencies
├── vite.config.js            # Vite configuration
├── tailwind.config.js        # Tailwind configuration
├── postcss.config.js         # PostCSS configuration
└── .env.example              # Environment variables template

datasets/
├── README.md                 # Dataset documentation
├── registry/
│   └── datasets.json         # Dataset registry
├── raw/                      # Raw datasets (not in git)
├── processed/                # Processed datasets (not in git)
└── sample/
    └── sample_pose.json      # Sample dataset

scripts/
└── dataset/
    └── validate_datasets.py  # Dataset validation script
```

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **PostgreSQL**: 15 or higher (or use Docker)
- **Docker**: (optional, for containerized development)
- **Docker Compose**: (optional, for containerized development)
- **Git**: for version control

## Environment Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Sports_INJURYRisk
```

### 2. Environment Variables

Copy the example environment files and configure them:

```bash
# Root environment variables
cp .env.example .env

# Backend environment variables
cp backend/.env.example backend/.env

# Frontend environment variables
cp frontend/.env.example frontend/.env
```

Edit the `.env` files with your configuration:

**Root `.env`:**
```env
POSTGRES_USER=sports_user
POSTGRES_PASSWORD=sports_password
POSTGRES_DB=sports_injury_risk
DATABASE_URL=postgresql://sports_user:sports_password@localhost:5432/sports_injury_risk
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
VITE_API_URL=http://localhost:8000
```

**Backend `backend/.env`:**
```env
DATABASE_URL=postgresql://sports_user:sports_password@localhost:5432/sports_injury_risk
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Frontend `frontend/.env`:**
```env
VITE_API_URL=http://localhost:8000
```

**Important**: Change `SECRET_KEY` to a secure random string in production.

## PostgreSQL Setup

### Option 1: Using Docker (Recommended)

```bash
# Start PostgreSQL using Docker Compose
docker-compose up -d postgres

# Check if PostgreSQL is running
docker-compose ps
```

### Option 2: Local PostgreSQL Installation

If you have PostgreSQL installed locally:

```bash
# Create database
createdb sports_injury_risk

# Or use psql
psql -U postgres
CREATE DATABASE sports_injury_risk;
CREATE USER sports_user WITH PASSWORD 'sports_password';
GRANT ALL PRIVILEGES ON DATABASE sports_injury_risk TO sports_user;
```

## Backend Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Migrations

```bash
# Run Alembic migrations
alembic upgrade head
```

### 4. Start Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

API Documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Running the Application

### Using Docker Compose (All-in-One)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Manual Setup (Development)

1. **Start PostgreSQL** (if not using Docker):
   ```bash
   # Docker
   docker-compose up -d postgres
   
   # Or local PostgreSQL
   # Ensure PostgreSQL is running
   ```

2. **Start Backend**:
   ```bash
   cd backend
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   uvicorn app.main:app --reload
   ```

3. **Start Frontend** (in a new terminal):
   ```bash
   cd frontend
   npm run dev
   ```

4. **Access the Application**:
   - Frontend: `http://localhost:5173`
   - Backend API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`

## Database Migrations

### Create a New Migration

```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migrations

```bash
alembic downgrade -1
```

## Running Tests

### Backend Tests

```bash
cd backend
pytest
```

Run specific test files:
```bash
pytest tests/test_auth.py
pytest tests/test_athletes.py
pytest tests/test_datasets.py
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## API Documentation

The API is documented using Swagger/OpenAPI. Access it at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### API Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

#### Users
- `GET /api/v1/users/` - Get all users (admin only)
- `GET /api/v1/users/{user_id}` - Get specific user

#### Athletes
- `POST /api/v1/athletes` - Create athlete profile
- `GET /api/v1/athletes` - Get all athletes
- `GET /api/v1/athletes/{id}` - Get specific athlete
- `GET /api/v1/athletes/me` - Get current athlete's profile
- `PUT /api/v1/athletes/{id}` - Update athlete profile
- `DELETE /api/v1/athletes/{id}` - Delete athlete profile (admin only)

#### Datasets
- `GET /api/v1/datasets` - Get registered datasets and their status

## Dataset Integration

### Dataset Validation

Run the dataset validation script to check dataset integration status:

```bash
python scripts/dataset/validate_datasets.py
```

This script will:
- Inspect registered datasets
- Check expected files
- Validate sample annotations
- Report missing datasets
- Report valid datasets

### Dataset Registry

The dataset registry is maintained in `datasets/registry/datasets.json`. It contains metadata about all datasets used in the system.

For more information, see `datasets/README.md`.

## Milestone 1 Scope

Milestone 1 includes the following functionality:

### ✅ Implemented
- Project initialization and structure
- FastAPI backend with SQLAlchemy
- PostgreSQL database with Alembic migrations
- JWT authentication with password hashing
- Role-based access control (5 roles)
- User registration and login
- Athlete profile management (CRUD)
- Dataset registry and sample integration
- Dataset validation script
- React frontend with authentication
- Protected routes and authorization
- Basic API documentation
- Docker Compose configuration
- Backend tests

### 🚧 Not Implemented (Future Milestones)
- Pose estimation (MediaPipe, YOLO, OpenPose)
- Video processing pipeline
- Biomechanical calculations
- Movement anomaly detection
- Injury risk prediction models
- Risk scoring algorithms
- Corrective exercise recommendations
- Advanced analytics dashboards
- Real-time camera processing

## User Roles

The system supports five user roles with different permissions:

1. **Athlete**
   - View/update own athlete profile
   - View own data

2. **Coach**
   - View athlete profiles
   - Create and manage athlete information

3. **Physiotherapist**
   - View athlete profiles
   - Access injury-related information

4. **Sports Scientist**
   - View athlete profiles
   - Access analysis-ready information

5. **Administrator**
   - Full system access
   - User management
   - Athlete management (including deletion)

## Security Considerations

- Passwords are hashed using bcrypt
- JWT tokens are used for authentication
- Role-based access control is enforced on the backend
- CORS is configured for allowed origins
- Environment variables are used for sensitive data
- `.env` files are excluded from git

**Important**: Never commit `.env` files or secrets to the repository.

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. Ensure PostgreSQL is running:
   ```bash
   docker-compose ps  # If using Docker
   # or check local PostgreSQL status
   ```

2. Verify DATABASE_URL in `.env` file

3. Check if database exists:
   ```bash
   psql -U sports_user -d sports_injury_risk
   ```

### Migration Issues

If migrations fail:

```bash
# Reset database (WARNING: This deletes all data)
alembic downgrade base
alembic upgrade head
```

### Frontend API Connection Issues

If the frontend cannot connect to the backend:

1. Ensure backend is running on port 8000
2. Check `VITE_API_URL` in `frontend/.env`
3. Verify CORS configuration in `backend/app/main.py`

## Development Workflow

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and test them

3. Run tests:
   ```bash
   cd backend && pytest
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

5. Push and create a pull request

## Future Milestones

- **Milestone 2**: Pose estimation and video processing
- **Milestone 3**: Injury risk prediction and analytics
- **Milestone 4**: Advanced recommendations and deployment

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the development team.

---

**Note**: This is Milestone 1 of the Sports Injury Risk Detection system. The current implementation provides a solid foundation for future AI/ML features including pose estimation, biomechanical analysis, and injury risk prediction.
