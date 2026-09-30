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
from database import engine, get_db
from video_processing import process_video_with_mediapipe

# Create all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sports Injury Risk Detection API")

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
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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

from fastapi import Form

@app.post("/video/upload")
async def upload_and_process_video(
    file: UploadFile = File(...), 
    activity: str = Form("Unknown"),
    surface_type: str = Form("Unknown"),
    footwear: str = Form("Unknown"),
    rpe: int = Form(5),
    sleep_quality: int = Form(5),
    current_user: models.User = Depends(get_current_user)
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
        return {
            "message": "Video processed successfully", 
            "original_file": file.filename,
            "processed_url": f"/processed/{result['filename']}",
            "analytics": result['analytics']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
