import os
import joblib

# -------------------------------------------------------------------------
# Load model safely (supports list of fallback model paths)
# -------------------------------------------------------------------------
def load_model_if_exists(model_paths):
    """
    Accepts either:
    - a single model path (string)
    - a list of model paths (tries them in order)
    """
    if isinstance(model_paths, str):
        model_paths = [model_paths]

    for path in model_paths:
        if os.path.exists(path):
            print(f"✅ Loaded model: {path}")
            return joblib.load(path)

    print("❌ No model found in provided paths.")
    return None


# -------------------------------------------------------------------------
# Rule-based backup scoring (optional)
# -------------------------------------------------------------------------
def compute_rule_based_risk(temp, humidity, wind, visibility):
    score = 0

    # Temperature
    if temp >= 40: score += 25
    elif temp >= 30: score += 15
    elif temp <= -5: score += 10

    # Humidity
    if humidity >= 80: score += 20
    elif humidity >= 60: score += 10

    # Wind
    if wind >= 40: score += 30
    elif wind >= 25: score += 15

    # Visibility
    if visibility < 2000: score += 25
    elif visibility < 5000: score += 10

    return min(score, 100)


# -------------------------------------------------------------------------
# Aircraft type → numeric mapping
# -------------------------------------------------------------------------
def map_aircraft_type(aircraft_type):
    mapping = {
        "Commercial Jet": 0,
        "Cargo Aircraft": 1,
        "Helicopter": 2,
        "Private Plane": 3,
        "Military Aircraft": 4,
        "Glider": 5,
        "Ultralight": 6,
        "Unknown": 7
    }
    return mapping.get(aircraft_type, 7)
