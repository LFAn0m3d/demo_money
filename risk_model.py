import os
import numpy as np

try:
    import joblib
    from tensorflow.keras.models import load_model
except Exception:  # modules might not be installed in some environments
    joblib = None
    load_model = None

# Global variables to cache loaded models
IFOREST = None
AUTOENC = None

MODEL_DIR = os.getenv('MODEL_DIR', 'models')
IFOREST_PATH = os.path.join(MODEL_DIR, 'isolation_forest.pkl')
AUTOENCODER_PATH = os.path.join(MODEL_DIR, 'autoencoder.h5')


def load_models():
    """Load Isolation Forest and Autoencoder models once."""
    global IFOREST, AUTOENC

    if joblib is None or load_model is None:
        return

    if not IFOREST and os.path.exists(IFOREST_PATH):
        IFOREST = joblib.load(IFOREST_PATH)

    if not AUTOENC and os.path.exists(AUTOENCODER_PATH):
        AUTOENC = load_model(AUTOENCODER_PATH)


def parse_amount(amount_str):
    """Safely convert amount string to a float."""
    try:
        return float(str(amount_str).replace(',', '').strip())
    except Exception:
        return 0.0


def _extract_features(data: dict):
    """Extract structured numerical features from OCR data."""
    amount = parse_amount(data.get('amount', '0'))
    sender_len = len(data.get('sender_name') or '')
    receiver_len = len(data.get('receiver_name') or '')
    return [amount, sender_len, receiver_len]


def calculate_risk(data: dict) -> float:
    """Calculate risk score using preloaded ML models."""
    load_models()
    features = _extract_features(data)
    feats = np.array(features).reshape(1, -1)

    if IFOREST:
        try:
            iso_score = -IFOREST.decision_function(feats)[0]
            iso_score = (iso_score + 1) / 2
        except Exception:
            iso_score = 0.5
    else:
        iso_score = 0.5

    if AUTOENC:
        try:
            recon = AUTOENC.predict(feats, verbose=0)
            mse = np.mean(np.square(feats - recon))
            auto_score = mse / (mse + 1)
        except Exception:
            auto_score = 0.5
    else:
        auto_score = 0.5

    risk = (iso_score + auto_score) / 2
    return round(risk, 2)
