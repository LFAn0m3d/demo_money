import os
import numpy as np

try:
    import joblib
    from sklearn.ensemble import IsolationForest
    from tensorflow.keras.models import load_model
except Exception:  # modules might not be installed in some environments
    joblib = None
    load_model = None

MODEL_DIR = os.getenv('MODEL_DIR', 'models')
IFOREST_PATH = os.path.join(MODEL_DIR, 'isolation_forest.pkl')
AUTOENCODER_PATH = os.path.join(MODEL_DIR, 'autoencoder.h5')


def load_models():
    """Load Isolation Forest and Autoencoder models if available."""
    if joblib is None or load_model is None:
        return None, None
    if not (os.path.exists(IFOREST_PATH) and os.path.exists(AUTOENCODER_PATH)):
        return None, None
    iforest = joblib.load(IFOREST_PATH)
    autoenc = load_model(AUTOENCODER_PATH)
    return iforest, autoenc


def _extract_features(data: dict):
    """Extract simple numerical features from OCR data."""
    try:
        amount = float(data.get('amount', '0').replace(',', ''))
    except Exception:
        amount = 0.0
    sender_len = len(data.get('sender_name') or '')
    receiver_len = len(data.get('receiver_name') or '')
    return [amount, sender_len, receiver_len]


def calculate_risk(data: dict) -> float:
    """Calculate risk score using Isolation Forest and Autoencoder models."""
    features = _extract_features(data)
    iforest, autoenc = load_models()
    feats = np.array(features).reshape(1, -1)

    if iforest is not None:
        iso_score = -iforest.decision_function(feats)[0]
        iso_score = (iso_score + 1) / 2
    else:
        iso_score = 0.5

    if autoenc is not None:
        recon = autoenc.predict(feats, verbose=0)
        mse = np.mean(np.square(feats - recon))
        auto_score = mse / (mse + 1)
    else:
        auto_score = 0.5

    risk = (iso_score + auto_score) / 2
    return round(float(risk), 2)
