import os
import shutil
import time
from typing import Dict

import numpy as np
import pandas as pd
import joblib
import requests
from fastapi import FastAPI, APIRouter, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# --- FIX: Removed TFSMLayer import which was causing the crash ---
# from keras.layers import TFSMLayer 
from keras.preprocessing.image import load_img, img_to_array
import tensorflow as tf  # Added explicit TF import

# Import database and auth
from db import init_db, check_db_connection
from auth import auth_router

# -------------------------
# Config
# -------------------------
MODEL_DIR = os.path.join(os.path.dirname(__file__), "MRI")
CKD_MODEL_DIR = os.path.join(os.path.dirname(__file__), "CKD")
CKD_SCALER_PATH = os.path.join(CKD_MODEL_DIR, "data_scaler.joblib")
CKD_DIAGNOSIS_PATH = os.path.join(CKD_MODEL_DIR, "ckd_diagnosis_model.joblib")
CKD_STAGE_PATH = os.path.join(CKD_MODEL_DIR, "ckd_stage_model.joblib")
ASCVD_MODEL_PATH = os.path.join(os.path.dirname(__file__), "ASCVD_Risk_Estimator.pkl")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

CLASS_DICT: Dict[int, str] = {0: 'Glioma', 1: 'Meningioma', 2: 'No Tumor', 3: 'Pituitary'}
MRI_MODEL = None
CKD_SCALER = None
CKD_DIAGNOSIS_MODEL = None
CKD_STAGE_MODEL = None
CKD_MODEL_READY = False
ASCVD_MODEL = None
ASCVD_MODEL_READY = False

# CKD Feature Order
FEATURE_ORDER = ['gfr', 'c3_c4', 'blood_pressure', 'serum_creatinine', 'serum_calcium', 'bun', 'urine_ph', 'oxalate_levels']

# API Key read from the environment variable specified by the user
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

# -------------------------
# Pydantic Models
# -------------------------
class ASCVDRiskInput(BaseModel):
    blood_glucose: float
    HbA1C: float
    Systolic_BP: float
    Diastolic_BP: float
    LDL: float
    HDL: float
    Triglycerides: float
    Haemoglobin: float
    MCV: float

# -------------------------
# FastAPI Setup
# -------------------------
app = FastAPI(title="HealthAI Backend")
router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in prod!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Helper Functions (MRI Model)
# -------------------------
def load_mri_model():
    """Load the TensorFlow MRI model using tf.saved_model.load (Safe for all versions)."""
    global MRI_MODEL
    
    if not os.path.exists(MODEL_DIR):
        print(f"ERROR: MRI model not found at {MODEL_DIR}")
        return

    # Force CPU in production containers without GPU
    try:
        tf.config.set_visible_devices([], 'GPU')
    except Exception:
        pass

    print(f"INFO: Loading MRI model from {MODEL_DIR}...")
    try:
        # --- FIX: Using standard TF SavedModel loader instead of TFSMLayer ---
        loaded_bundle = tf.saved_model.load(MODEL_DIR)
        
        # We extract the default serving signature (acts like a function)
        MRI_MODEL = loaded_bundle.signatures['serving_default']
        print("INFO: MRI Model loaded successfully")
    except Exception as e:
        print(f"ERROR: Failed to load MRI model: {e}")
        MRI_MODEL = None

def predict_mri_image(image_path: str):
    """Run inference on a single MRI image."""
    if MRI_MODEL is None:
        raise RuntimeError("MRI Model not loaded")

    img = load_img(image_path, target_size=(128, 128))
    img_array = img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # --- FIX: Convert numpy array to TF Tensor (Required for signatures) ---
    input_tensor = tf.constant(img_array, dtype=tf.float32)

    # Predict
    prediction = MRI_MODEL(input_tensor)
    
    # Handle Dictionary output (standard for SavedModel signatures)
    if isinstance(prediction, dict):
        # Extract the first output tensor (usually 'dense_X' or 'output_0')
        prediction = next(iter(prediction.values()))

    # Convert back to numpy
    prediction = prediction.numpy()
    
    class_index = int(np.argmax(prediction, axis=-1)[0])
    confidence = float(prediction[0][class_index])
    label = CLASS_DICT.get(class_index, "Unknown")
    return label, confidence

# -------------------------
# Helper Functions (CKD Model)
# -------------------------
def load_ckd_models():
    """Load the CKD models (scaler, diagnosis, stage) from CKD directory."""
    global CKD_SCALER, CKD_DIAGNOSIS_MODEL, CKD_STAGE_MODEL, CKD_MODEL_READY
    
    try:
        if not os.path.exists(CKD_MODEL_DIR):
            print(f"WARNING: CKD model directory not found at {CKD_MODEL_DIR}")
            return
            
        if not all([
            os.path.exists(CKD_SCALER_PATH),
            os.path.exists(CKD_DIAGNOSIS_PATH),
            os.path.exists(CKD_STAGE_PATH)
        ]):
            print(f"WARNING: CKD model files not found in {CKD_MODEL_DIR}")
            return
        
        print(f"INFO: Loading CKD models from {CKD_MODEL_DIR}...")
        CKD_SCALER = joblib.load(CKD_SCALER_PATH)
        CKD_DIAGNOSIS_MODEL = joblib.load(CKD_DIAGNOSIS_PATH)
        CKD_STAGE_MODEL = joblib.load(CKD_STAGE_PATH)
        CKD_MODEL_READY = True
        print("INFO: CKD Models loaded successfully")
    except Exception as e:
        print(f"ERROR: Failed to load CKD models: {e}")
        CKD_MODEL_READY = False

# -------------------------
# Helper Functions (ASCVD Risk Estimator Model)
# -------------------------
def load_ascvd_model():
    """Load the ASCVD Risk Estimator model."""
    global ASCVD_MODEL, ASCVD_MODEL_READY
    
    try:
        if not os.path.exists(ASCVD_MODEL_PATH):
            print(f"WARNING: ASCVD Risk Estimator model not found at {ASCVD_MODEL_PATH}")
            return
        
        print(f"INFO: Loading ASCVD Risk Estimator model from {ASCVD_MODEL_PATH}...")
        ASCVD_MODEL = joblib.load(ASCVD_MODEL_PATH)
        ASCVD_MODEL_READY = True
        print("INFO: ASCVD Risk Estimator Model loaded successfully")
    except Exception as e:
        print(f"ERROR: Failed to load ASCVD Risk Estimator model: {e}")
        ASCVD_MODEL_READY = False

def feature_extraction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame with the following columns:
    ['blood_glucose', 'hba1c', 'systolic_bp', 'diastolic_bp',
     'ldl', 'hdl', 'triglycerides', 'haemoglobin', 'mcv']

    Returns the same DataFrame with additional engineered features.
    """
    df.columns = df.columns.str.lower()
    df['glucose_hba1c_ratio'] = df['blood_glucose'] / df['hba1c']
    df['pulse_pressure'] = df['systolic_bp'] - df['diastolic_bp']
    df['MAP'] = (df['systolic_bp'] + 2 * df['diastolic_bp']) / 3
    df['hypertension_flag'] = ((df['systolic_bp'] >= 140) | (df['diastolic_bp'] >= 90)).astype(int)
    df['total_cholesterol'] = df['ldl'] + df['hdl'] + (df['triglycerides'] / 5)
    df['ldl_hdl_ratio'] = df['ldl'] / df['hdl']
    df['tg_hdl_ratio'] = df['triglycerides'] / df['hdl']
    df['non_hdl'] = df['total_cholesterol'] - df['hdl']
    df['anaemia_flag'] = (df['haemoglobin'] < 12).astype(int)
    df['microcytosis_flag'] = (df['mcv'] < 80).astype(int)
    df['hb_mcv_ratio'] = df['haemoglobin'] / df['mcv']
    df['risk_score'] = (df['blood_glucose'] / 200) + (df['ldl'] / 160) + (df['triglycerides'] / 200) + (df['systolic_bp'] / 140)

    return df

def get_disease_recommendations(disease: str) -> dict:
    """Get prevention and treatment recommendations for a disease."""
    recommendations = {
        'Anemia': {
            'title': 'Anemia',
            'prevention': 'Maintain a balanced diet rich in iron (red meat, spinach, lentils). Consume vitamin C to increase iron absorption. Avoid tea/coffee after meals.',
            'treatment': 'Iron supplements under medical supervision, sometimes vitamin B12 or folic acid supplementation.',
            'suggested_plan': 'Daily iron tablets + iron-rich diet + monitor hemoglobin levels regularly.'
        },
        'Hypertension': {
            'title': 'Hypertension',
            'prevention': 'Reduce salt intake, exercise regularly, maintain healthy weight, avoid smoking.',
            'treatment': 'Blood pressure medication under medical supervision and regular blood pressure monitoring.',
            'suggested_plan': 'Daily blood pressure monitoring + medications (ACE inhibitors / Beta blockers) + reduce salt intake.'
        },
        'Diabetes': {
            'title': 'Diabetes',
            'prevention': 'Healthy diet with low sugar, maintain ideal weight, exercise regularly.',
            'treatment': 'Blood sugar lowering medications (such as Metformin) or insulin therapy.',
            'suggested_plan': 'Balanced diet + daily exercise + medication as prescribed.'
        },
        'High_Cholesterol': {
            'title': 'High Cholesterol',
            'prevention': 'Reduce saturated fats (fried foods, butter), increase fiber (vegetables, fruits, oats), regular exercise.',
            'treatment': 'Cholesterol-lowering medications (Statins) under medical supervision and healthy diet.',
            'suggested_plan': 'Reduce fat intake + Statin medications + regular lipid profile monitoring.'
        },
        'Fit': {
            'title': 'Healthy / Normal',
            'prevention': 'Maintain healthy diet, exercise regularly, periodic health checkups.',
            'treatment': 'No treatment needed, just continue healthy lifestyle.',
            'suggested_plan': 'Annual health checkup + maintain healthy lifestyle.'
        },
        'Unknown': {
            'title': 'Unknown',
            'prevention': 'Unable to provide recommendations due to insufficient data.',
            'treatment': 'Please consult a medical professional.',
            'suggested_plan': 'Please consult a medical professional.'
        }
    }
    
    return recommendations.get(disease, recommendations['Unknown'])

# -------------------------
# Startup Event
# -------------------------
@app.on_event("startup")
def startup_event():
    print("INFO: Starting HealthAI Backend...")
    
    # Initialize database
    print("INFO: Initializing database...")
    try:
        check_db_connection()
        init_db()
    except Exception as e:
        print(f"WARNING: Database initialization failed: {e}")
    
    # Load ML models
    load_mri_model()
    load_ckd_models()
    load_ascvd_model()
    
    print("INFO: HealthAI Backend started successfully")

# -------------------------
# Root Endpoints
# -------------------------
@app.get("/")
def root():
    return {"status": "online", "service": "HealthAI Backend"}

# -------------------------
# API Router Endpoints
# -------------------------
@router.get("/")
def api_root():
    return {
        "status": "online",
        "service": "HealthAI API",
        "version": "1.0.0"
    }

@router.get("/rays")
def get_rays():
    return {
        "status": "success",
        "title": "Medical Imaging Analysis",
        "description": "Upload your MRI scans for AI-powered analysis",
        "supported_formats": ["jpg", "jpeg", "png"],
        "model_ready": MRI_MODEL is not None
    }

@router.get("/report")
def get_report():
    return {
        "status": "success",
        "reports": [],
        "message": "No reports available yet"
    }

@router.get("/about")
def get_about():
    return {
        "status": "success",
        "name": "HealthAI Labs",
        "description": "AI-powered medical imaging analysis platform",
        "version": "1.0.0",
        "features": ["MRI Analysis", "Brain Tumor Detection", "Medical Reports", "CKD Analysis", "ASCVD Risk Assessment"]
    }

@router.get("/analysis")
def get_analysis():
    return {
        "status": "success",
        "message": "Analysis Dashboard",
        "available_analyses": [
            {
                "id": "brain-mri",
                "name": "Brain MRI Analysis",
                "description": "Advanced AI analysis of brain MRI scans for tumor detection and classification",
                "type": "image",
                "ready": MRI_MODEL is not None
            },
            {
                "id": "ckd-analysis",
                "name": "Chronic Kidney Disease Analysis",
                "description": "Comprehensive CKD analysis from laboratory data",
                "type": "data",
                "ready": CKD_MODEL_READY
            },
            {
                "id": "ascvd-risk",
                "name": "ASCVD Risk Assessment",
                "description": "Predict cardiovascular disease risk based on blood test markers (glucose, cholesterol, blood pressure, etc.)",
                "type": "data",
                "ready": ASCVD_MODEL_READY
            },
            {
                "id": "chest-xray",
                "name": "Chest X-Ray Analysis",
                "description": "Comprehensive chest X-ray analysis for respiratory conditions",
                "type": "image",
                "ready": False,
                "coming_soon": True
            }
        ],
        "recent_analyses": []
    }

@router.get("/askdoctor")
def get_askdoctor():
    return {
        "status": "success",
        "message": "Ask a Doctor",
        "available": True
    }

@router.get("/contact")
def get_contact():
    return {
        "status": "success",
        "email": "contact@healthai.com",
        "phone": "+1-234-567-8900",
        "address": "123 Health St, Medical City"
    }

@router.get("/news")
def get_news(category: str = "health", lang: str = "en", page: int = 1):
    
    if not GNEWS_API_KEY:
        print("CRITICAL: GNEWS_API_KEY environment variable is NOT set. Returning mock data.")
        return {
             "status": "success",
             "category": category,
             "language": lang,
             "page": page,
             "total_pages": 5,
             "articles": [
                 {
                     "id": "mock-1",
                     "title": "Mock Data: AI in Disease Diagnostics",
                     "description": "This is mock data because the GNEWS_API_KEY environment variable is not set.",
                     "publishedAt": "2025-11-28T10:00:00Z",
                     "source": {"name": "Mock News Daily"},
                     "url": "https://www.example.com/mock-article-1",
                     "image": "https://placehold.co/600x337/3b82f6/ffffff?text=MOCK+NEWS"
                 }
             ]
         }

    # NewsAPI Endpoint
    url = f"https://newsapi.org/v2/top-headlines?category={category}&language={lang}&page={page}&pageSize=20&apiKey={GNEWS_API_KEY}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "ok":
            print(f"ERROR: NewsAPI returned status '{data.get('status')}' - Message: {data.get('message')}")
            return {"status": "error", "articles": [], "message": data.get('message')}

        formatted_articles = []
        for article in data.get("articles", []):
            if article.get("title") == "[Removed]" or not article.get("url"):
                continue

            formatted_articles.append({
                "id": article.get("url"),
                "title": article.get("title", "No Title Available"),
                "description": article.get("description", article.get("content", "No description available.")),
                "url": article.get("url"),
                "image": article.get("urlToImage"),
                "publishedAt": article.get("publishedAt"),
                "source": {
                    "name": article.get("source", {}).get("name", "Unknown Source")
                }
            })

        total_results = data.get("totalResults", 100)
        total_pages = min(int(total_results / 20) + 1, 5)

        return {
            "status": "success",
            "category": category,
            "language": lang,
            "page": page,
            "total_pages": total_pages,
            "articles": formatted_articles
        }

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to connect to NewsAPI: {e}")
        return {
            "status": "error",
            "articles": [],
            "message": "Connection error to external news service."
        }

# -------------------------
# MRI Analysis Endpoint
# -------------------------
@router.post("/rays/mri")
async def analyze_mri(file: UploadFile = File(...)):
    if MRI_MODEL is None:
        return JSONResponse(status_code=503, content={"error": "MRI Model not ready"})

    temp_filename = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{file.filename}")

    try:
        with open(temp_filename, "wb") as f:
            shutil.copyfileobj(file.file, f)

        label, confidence = predict_mri_image(temp_filename)
        
        return {
            "status": "success",
            "prediction": label,
            "confidence": float(confidence),
            "confidence_percent": f"{confidence:.2%}",
            "details": {"class": label, "score": float(confidence)}
        }
    except Exception as e:
        print(f"ERROR: MRI analysis failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Analysis failed", "message": str(e)}
        )
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# -------------------------
# CKD Analysis Endpoints
# -------------------------
@router.post("/analysis/ckd/file")
async def analyze_ckd_file(file: UploadFile = File(...)):
    if not CKD_MODEL_READY:
        return JSONResponse(status_code=503, content={"error": "CKD Models not ready"})

    temp_filename = os.path.join(UPLOAD_DIR, f"ckd_input_{int(time.time())}_{file.filename}")

    try:
        with open(temp_filename, "wb") as f:
            shutil.copyfileobj(file.file, f)

        input_df = pd.read_csv(temp_filename)
        
        if len(input_df.columns) != len(FEATURE_ORDER):
            raise ValueError(
                f"Number of columns ({len(input_df.columns)}) != features ({len(FEATURE_ORDER)}). "
                f"Expected: {', '.join(FEATURE_ORDER)}"
            )

        input_df = input_df[FEATURE_ORDER]
        scaled_features = CKD_SCALER.transform(input_df)
        diagnosis_prediction = CKD_DIAGNOSIS_MODEL.predict(scaled_features)[0]

        if diagnosis_prediction == 1:
            stage_prediction = CKD_STAGE_MODEL.predict(scaled_features)[0]
            result = {
                "diagnosis_result": "Positive - Chronic Kidney Disease detected.",
                "ckd_stage": f"Stage {int(stage_prediction)}",
            }
        else:
            result = {
                "diagnosis_result": "Negative - No Chronic Kidney Disease detected.",
                "ckd_stage": "Not applicable",
            }

        return {
            "status": "success",
            "prediction": result["diagnosis_result"],
            "ckd_stage": result["ckd_stage"],
            "diagnosis_code": int(diagnosis_prediction)
        }

    except Exception as e:
        print(f"ERROR: CKD analysis failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Analysis failed", "message": str(e)}
        )
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@router.post("/analysis/ckd/manual")
async def analyze_ckd_manual(
    gfr: float,
    c3_c4: float,
    blood_pressure: float,
    serum_creatinine: float,
    serum_calcium: float,
    bun: float,
    urine_ph: float,
    oxalate_levels: float
):
    if not CKD_MODEL_READY:
        return JSONResponse(status_code=503, content={"error": "CKD Models not ready"})

    try:
        input_data = {
            'gfr': [gfr],
            'c3_c4': [c3_c4],
            'blood_pressure': [blood_pressure],
            'serum_creatinine': [serum_creatinine],
            'serum_calcium': [serum_calcium],
            'bun': [bun],
            'urine_ph': [urine_ph],
            'oxalate_levels': [oxalate_levels]
        }

        input_df = pd.DataFrame(input_data)
        input_df = input_df[FEATURE_ORDER]
        scaled_features = CKD_SCALER.transform(input_df)
        diagnosis_prediction = CKD_DIAGNOSIS_MODEL.predict(scaled_features)[0]

        if diagnosis_prediction == 1:
            stage_prediction = CKD_STAGE_MODEL.predict(scaled_features)[0]
            result = {
                "diagnosis_result": "Positive - Chronic Kidney Disease detected.",
                "ckd_stage": f"Stage {int(stage_prediction)}",
            }
        else:
            result = {
                "diagnosis_result": "Negative - No Chronic Kidney Disease detected.",
                "ckd_stage": "Not applicable",
            }

        return {
            "status": "success",
            "prediction": result["diagnosis_result"],
            "ckd_stage": result["ckd_stage"],
            "diagnosis_code": int(diagnosis_prediction),
            "input_data": input_data
        }

    except Exception as e:
        print(f"ERROR: CKD manual analysis failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Analysis failed", "message": str(e)}
        )

# -------------------------
# ASCVD Risk Assessment Endpoint
# -------------------------
@router.post("/analysis/ascvd-risk")
async def analyze_ascvd_risk(data: ASCVDRiskInput):
    """
    Predict cardiovascular disease risk based on health markers from blood tests.
    """
    if not ASCVD_MODEL_READY:
        return JSONResponse(status_code=503, content={"error": "ASCVD Risk Estimator Model not ready"})

    try:
        # Convert input to dictionary
        input_data = {
            'blood_glucose': data.blood_glucose,
            'HbA1C': data.HbA1C,
            'Systolic_BP': data.Systolic_BP,
            'Diastolic_BP': data.Diastolic_BP,
            'LDL': data.LDL,
            'HDL': data.HDL,
            'Triglycerides': data.Triglycerides,
            'Haemoglobin': data.Haemoglobin,
            'MCV': data.MCV
        }

        # Create DataFrame
        df = pd.DataFrame([input_data])

        # Apply feature extraction
        processed_df = feature_extraction(df.copy())

        # Make prediction
        prediction = ASCVD_MODEL.predict(processed_df)[0]
        
        # Disease mapping
        disease_map = {
            0: 'Anemia',
            1: 'Fit',
            2: 'Hypertension',
            3: 'Diabetes',
            4: 'High_Cholesterol'
        }
        
        predicted_disease = disease_map.get(prediction, 'Unknown')
        
        # Get recommendations
        recommendation = get_disease_recommendations(predicted_disease)
        
        return {
            "status": "success",
            "disease": predicted_disease,
            "disease_code": int(prediction),
            "recommendation": recommendation,
            "input_data": input_data
        }

    except Exception as e:
        print(f"ERROR: ASCVD Risk assessment failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Analysis failed", "message": str(e)}
        )

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
