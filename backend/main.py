import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.staticfiles import StaticFiles

import models
import schemas
import auth
from database import engine, get_db, SessionLocal
from video_processing import process_video_with_mediapipe

# Create all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sports Injury Risk Detection API")

@app.on_event("startup")
def create_default_user():
    db = SessionLocal()
    try:
        default_email = "demo@sportsai.com"
        user = db.query(models.User).filter(models.User.email == default_email).first()
        if not user:
            hashed_password = auth.get_password_hash("password123")
            db_user = models.User(email=default_email, hashed_password=hashed_password, role="Athlete")
            db.add(db_user)
            db.commit()
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)

app.mount("/processed", StaticFiles(directory="processed"), name="processed")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except auth.JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        # Auto-register for seamless demo experience
        hashed_password = auth.get_password_hash(form_data.password)
        user = models.User(email=form_data.username, hashed_password=hashed_password, role="Athlete")
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/google", response_model=schemas.Token)
def login_with_google(google_data: schemas.GoogleLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == google_data.email).first()
    if not user:
        hashed_password = auth.get_password_hash("google_mock_password_random_secure")
        user = models.User(email=google_data.email, hashed_password=hashed_password, role=google_data.role)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/athlete/profile", response_model=schemas.AthleteProfileResponse)
def create_athlete_profile(profile: schemas.AthleteProfileCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "Athlete":
        raise HTTPException(status_code=403, detail="Only Athletes can create a profile")
    
    existing = db.query(models.AthleteProfile).filter(models.AthleteProfile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists")

    db_profile = models.AthleteProfile(**profile.model_dump(), user_id=current_user.id)
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

@app.get("/athlete/profile", response_model=schemas.AthleteProfileResponse)
def get_athlete_profile(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    profile = db.query(models.AthleteProfile).filter(models.AthleteProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.put("/athlete/profile", response_model=schemas.AthleteProfileResponse)
def update_athlete_profile(profile_update: schemas.AthleteProfileCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "Athlete":
        raise HTTPException(status_code=403, detail="Only Athletes can update a profile")
    
    profile = db.query(models.AthleteProfile).filter(models.AthleteProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in profile_update.model_dump().items():
        setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    return profile

@app.post("/athlete/assessments", response_model=schemas.PhysicalAssessmentResponse)
def create_physical_assessment(assessment: schemas.PhysicalAssessmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_assessment = models.PhysicalAssessment(**assessment.model_dump(), user_id=current_user.id)
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return db_assessment

@app.get("/athlete/assessments", response_model=list[schemas.PhysicalAssessmentResponse])
def get_physical_assessments(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.PhysicalAssessment).filter(models.PhysicalAssessment.user_id == current_user.id).all()

@app.post("/athlete/performance", response_model=schemas.PerformanceRecordResponse)
def create_performance_record(record: schemas.PerformanceRecordCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_record = models.PerformanceRecord(**record.model_dump(), user_id=current_user.id)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@app.get("/athlete/performance", response_model=list[schemas.PerformanceRecordResponse])
def get_performance_records(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.PerformanceRecord).filter(models.PerformanceRecord.user_id == current_user.id).all()

from fastapi import Form

@app.post("/video/upload")
async def upload_and_process_video(
    file: UploadFile = File(...), 
    activity: str = Form("Unknown"),
    surface_type: str = Form("Unknown"),
    footwear: str = Form("Unknown"),
    rpe: int = Form(5),
    sleep_quality: int = Form(5),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Save the uploaded file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process the video
    try:
        result = process_video_with_mediapipe(
            file_path, "processed", activity, surface_type, footwear, rpe, sleep_quality
        )
        
        import json
        from datetime import datetime
        
        db_analysis = models.VideoAnalysis(
            user_id=current_user.id,
            activity=result['analytics']['activity_analyzed'],
            surface_type=result['analytics']['surface_type'],
            footwear=result['analytics']['footwear'],
            rpe=result['analytics']['rpe'],
            sleep_quality=result['analytics']['sleep_quality'],
            risk_score=result['analytics']['risk_score'],
            risk_level=result['analytics']['risk_level'],
            injury_probabilities=json.dumps(result['analytics']['injury_probabilities']),
            corrective_recommendation=result['analytics']['corrective_recommendation'],
            created_at=datetime.utcnow().isoformat()
        )
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        
        # 11. Notification & Alert System
        if db_analysis.risk_level in ["High Risk", "Critical Risk"]:
            alert_type = "alert" if db_analysis.risk_level == "Critical Risk" else "warning"
            db_notification = models.Notification(
                user_id=current_user.id,
                title="High Injury Risk Detected",
                message=f"Your recent analysis for {db_analysis.activity} resulted in a {db_analysis.risk_level}. Please review recommendations.",
                type=alert_type,
                created_at=datetime.utcnow().isoformat()
            )
            db.add(db_notification)
            db.commit()
        
        return {
            "message": "Video processed successfully", 
            "original_file": file.filename,
            "processed_url": f"/processed/{result['filename']}",
            "analytics": result['analytics']
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/athlete/analyses", response_model=list[schemas.VideoAnalysisResponse])
def get_athlete_analyses(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.VideoAnalysis).filter(models.VideoAnalysis.user_id == current_user.id).order_by(models.VideoAnalysis.created_at.desc()).all()

@app.get("/notifications", response_model=list[schemas.NotificationResponse])
def get_notifications(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Notification).filter(models.Notification.user_id == current_user.id).order_by(models.Notification.created_at.desc()).all()

from fastapi.responses import StreamingResponse
import io
import csv
from reportlab.pdfgen import canvas

@app.get("/export/csv")
def export_csv(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    analyses = db.query(models.VideoAnalysis).filter(models.VideoAnalysis.user_id == current_user.id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Activity", "Risk Score", "Risk Level", "Recommendations", "Date"])
    
    for analysis in analyses:
        writer.writerow([analysis.activity, analysis.risk_score, analysis.risk_level, analysis.corrective_recommendation, analysis.created_at])
        
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=analyses.csv"})

@app.get("/export/pdf")
def export_pdf(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    analyses = db.query(models.VideoAnalysis).filter(models.VideoAnalysis.user_id == current_user.id).all()
    
    output = io.BytesIO()
    p = canvas.Canvas(output)
    p.drawString(100, 800, f"Biomechanical Assessment Report - {current_user.email}")
    
    y = 750
    for analysis in analyses:
        p.drawString(100, y, f"Activity: {analysis.activity} | Score: {analysis.risk_score} | Level: {analysis.risk_level}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
            
    p.save()
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=analyses.pdf"})
