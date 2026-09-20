from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, users, athletes, datasets

app = FastAPI(
    title="Sports Injury Risk Detection API",
    description="API for sports injury risk detection from video analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(athletes.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Sports Injury Risk Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "Milestone 1 - Foundation Complete"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
