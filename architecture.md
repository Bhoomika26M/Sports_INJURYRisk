# Sports Injury Risk Detection
## System Architecture – Milestone 1

### 1. Project Overview

The Sports Injury Risk Detection system is an AI-powered platform designed to analyze athlete movement videos and identify biomechanical issues, abnormal movement patterns, injury risk factors, and potential injuries.

The main users of the system are athletes, coaches, sports scientists, physiotherapists, and medical teams.

The system consists of:

- React frontend
- FastAPI backend
- PostgreSQL database
- Authentication and Role-Based Access Control (RBAC)
- Athlete profile management
- Video processing and analysis modules
- Computer vision and machine learning modules

---

## 2. System Architecture

```text
                    ┌─────────────────────┐
                    │        User         │
                    │                     │
                    │ Athlete / Coach /   │
                    │ Sports Professional │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   React Frontend    │
                    │                     │
                    │ Dashboard           │
                    │ Athlete Profiles    │
                    │ Video Upload        │
                    │ Movement Analysis   │
                    │ Risk Assessment     │
                    │ Reports             │
                    └──────────┬──────────┘
                               │
                         HTTP / REST API
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Backend   │
                    │                     │
                    │ Authentication      │
                    │ RBAC                │
                    │ Athlete Management  │
                    │ Video Processing    │
                    │ AI/ML Services      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    PostgreSQL       │
                    │                     │
                    │ Users               │
                    │ Athletes            │
                    │ Analysis Results    │
                    │ Risk Information    │
                    └─────────────────────┘
3. Frontend

The frontend is developed using React and JavaScript.

The frontend provides the user interface for:

User authentication
Dashboard
Athlete profile management
Video upload
Movement analysis
Injury risk assessment
Recommendations
Reports and analytics

Current frontend structure:

frontend/
│
├── src/
│   ├── App.jsx
│   ├── App.css
│   ├── index.css
│   └── main.jsx
│
└── package.json
4. Backend

The backend is developed using Python and FastAPI.

The backend is responsible for:

User registration
User login
JWT authentication
Role-Based Access Control
Athlete profile management
Database communication
Video processing
AI and machine learning services

Current backend structure:

backend/
│
├── database/
│   └── database.py
│
├── models/
│   ├── user.py
│   └── athlete.py
│
├── schemas/
│   ├── user.py
│   ├── login.py
│   └── athlete.py
│
├── routes/
│   └── general.py
│
├── services/
│   ├── security.py
│   └── auth.py
│
└── main.py
Backend Components
Routes

Routes handle API requests from the frontend.

Models

Models define the database tables using SQLAlchemy.

Schemas

Schemas validate incoming and outgoing data using Pydantic.

Services

Services handle security, password hashing, JWT authentication, and role verification.

Database

The database module establishes the connection with PostgreSQL and creates the required tables.

5. Authentication and RBAC

The system uses JWT-based authentication.

The authentication process is:

User
  │
  ▼
Register
  │
  ▼
Password is hashed
  │
  ▼
User stored in PostgreSQL
  │
  ▼
Login
  │
  ▼
Credentials verified
  │
  ▼
JWT access token generated
  │
  ▼
Token used for protected API requests
  │
  ▼
Role checked
  │
  ├───────────────┐
  ▼               ▼
Coach           Athlete
  │               │
  ▼               ▼
Allowed         Restricted
operations     operations

The system currently supports role-based access for users such as athletes and coaches.

6. Database Architecture

PostgreSQL is used as the primary relational database.

Users Table
users
--------------------------------
id          INTEGER PRIMARY KEY
name        VARCHAR NOT NULL
email       VARCHAR UNIQUE
password    VARCHAR NOT NULL
role        VARCHAR NOT NULL

Purpose:

Stores user account and authentication information.

Athletes Table
athletes
--------------------------------
id          INTEGER PRIMARY KEY
name        VARCHAR NOT NULL
age         INTEGER
gender      VARCHAR
sport       VARCHAR

Purpose:

Stores athlete profile information required for movement analysis and injury risk detection.

7. Athlete Profile Management

The athlete profile module allows authorized users to manage athlete information.

The current athlete profile contains:

Athlete ID
Name
Age
Gender
Sport

The backend currently provides APIs for:

Creating an athlete
Viewing athletes
Viewing an individual athlete
Updating an athlete
Deleting an athlete
8. Planned AI and Computer Vision Architecture

The future analysis pipeline will process athlete movement videos using computer vision and pose estimation techniques.

Athlete Movement Video
          │
          ▼
    Video Processing
          │
          ▼
    Pose Estimation
          │
          ▼
   Body Keypoint Data
          │
          ▼
Biomechanical Analysis
          │
          ▼
Movement Pattern Analysis
          │
          ▼
    Risk Prediction
          │
          ▼
   Risk Score & Alerts
          │
          ▼
Corrective Recommendations

Possible technologies for the analysis pipeline include OpenCV, MediaPipe, YOLOv8, TensorFlow, PyTorch, and pose estimation models.

9. Planned System Modules

The following modules will be implemented during later milestones:

Authentication and Role-Based Access Control
Athlete Profile Management
Video Upload and Processing
Pose Estimation
Biomechanical Analysis
Injury Risk Prediction
Movement Anomaly Detection
Risk Scoring
Corrective Recommendations
Dashboard and Analytics
Notifications
Reports
Testing and Deployment
10. Future Database Tables

Additional tables will be introduced as the project develops:

Videos

Stores uploaded athlete movement videos and related metadata.

Biomechanical Analysis

Stores calculated movement and biomechanical measurements.

Risk Assessments

Stores injury risk scores and assessment results.

Recommendations

Stores corrective movement and training recommendations.

Reports

Stores generated athlete analysis reports.

11. Technology Stack
Frontend
React
JavaScript
Tailwind CSS / CSS
Backend
Python
FastAPI
Database
PostgreSQL
MongoDB may be used as a secondary database if required
Computer Vision and AI
OpenCV
YOLOv8
MediaPipe
TensorFlow
PyTorch
Machine Learning and Data Processing
Scikit-learn
XGBoost
Pandas
NumPy
Development and Deployment
Git
GitHub
Docker
Docker Compose
Postman
12. Milestone 1 Status

The following Milestone 1 components have been initialized:

Project objectives and workflow
System architecture
Database structure
React frontend
FastAPI backend
PostgreSQL database
User registration
User login
Password hashing
JWT authentication
Role-Based Access Control
Athlete profile management
Initial dashboard UI

The remaining AI/biomechanics components will be developed in subsequent milestones.