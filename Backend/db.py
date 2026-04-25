# db.py - Database configuration and models for HealthAI
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db:5432/healthai_db")

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# -------------------------
# Database Models
# -------------------------

class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    full_name = Column(String(255))
    
    # OAuth fields
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'facebook', etc.
    profile_picture = Column(String(500), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, full_name={self.full_name})>"


class AnalysisHistory(Base):
    """
    Analysis history for users - will store references to MinIO objects
    This is prepared for future integration with MinIO
    """
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)  # Foreign key to users.id
    
    # Analysis details
    analysis_type = Column(String(50), nullable=False)  # 'mri', 'ckd', 'xray', etc.
    analysis_result = Column(Text, nullable=True)  # JSON string of results
    
    # MinIO references (for future implementation)
    minio_image_path = Column(String(500), nullable=True)  # Path to uploaded image in MinIO
    minio_report_path = Column(String(500), nullable=True)  # Path to generated report in MinIO
    
    # Metadata
    confidence_score = Column(String(50), nullable=True)
    diagnosis = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<AnalysisHistory(id={self.id}, user_id={self.user_id}, type={self.analysis_type})>"


class UserSession(Base):
    """
    User sessions for tracking active logins (optional, for security)
    """
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    
    # Session metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"


# -------------------------
# Database Helper Functions
# -------------------------

def get_db():
    """
    Dependency function to get database session
    Usage in FastAPI:
        @app.get("/some-endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    print("INFO: Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("INFO: Database tables created successfully")


def check_db_connection():
    """
    Check if database connection is working
    Returns True if connection is successful, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        print("INFO: Database connection successful")
        return True
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        return False


# -------------------------
# User CRUD Operations
# -------------------------

def get_user_by_email(db, email: str):
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_google_id(db, google_id: str):
    """Get user by Google ID"""
    return db.query(User).filter(User.google_id == google_id).first()


def get_user_by_id(db, user_id: int):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db, email: str, hashed_password: str = None, full_name: str = None, 
                google_id: str = None, oauth_provider: str = None, profile_picture: str = None):
    """Create a new user"""
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        google_id=google_id,
        oauth_provider=oauth_provider,
        profile_picture=profile_picture,
        is_verified=bool(google_id)  # Auto-verify OAuth users
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_last_login(db, user_id: int):
    """Update user's last login timestamp"""
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login = datetime.utcnow()
        db.commit()


def create_analysis_record(db, user_id: int, analysis_type: str, analysis_result: str,
                          confidence_score: str = None, diagnosis: str = None,
                          minio_image_path: str = None, minio_report_path: str = None):
    """Create a new analysis history record"""
    record = AnalysisHistory(
        user_id=user_id,
        analysis_type=analysis_type,
        analysis_result=analysis_result,
        confidence_score=confidence_score,
        diagnosis=diagnosis,
        minio_image_path=minio_image_path,
        minio_report_path=minio_report_path
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_user_analysis_history(db, user_id: int, limit: int = 10):
    """Get user's analysis history"""
    return db.query(AnalysisHistory)\
        .filter(AnalysisHistory.user_id == user_id)\
        .order_by(AnalysisHistory.created_at.desc())\
        .limit(limit)\
        .all()
