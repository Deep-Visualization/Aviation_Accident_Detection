from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from model_utils import load_model_if_exists, compute_rule_based_risk, map_aircraft_type

app = Flask(__name__)

# Load API key
load_dotenv("api.env")
OWM_API_KEY = os.getenv("OWM_API_KEY")

# Load model
MODEL_PATHS = ["aircraft_damage_rf_model_smote.joblib"]
model = load_model_if_exists(MODEL_PATHS)

CITIES = [
"New York","Los Angeles","Chicago","Houston","Phoenix",
"Boston","San Francisco","Seattle","Miami","Dallas",
"London","Paris","Dubai","Tokyo","Delhi","Mumbai"
]

AIRCRAFT_TYPES = [
"Commercial Jet","Cargo Aircraft","Helicopter",
"Plane","Military Aircraft","Glider",
"Ultralight","Unknown"
]

def get_weather(city):

    url=f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OWM_API_KEY}&units=metric"
    resp=requests.get(url)

    if resp.status_code!=200:
        return None

    data=resp.json()

    return {
        "temp":data["main"]["temp"],
        "humidity":data["main"]["humidity"],
        "wind":data["wind"]["speed"],
        "visibility":data.get("visibility",5000),
        "conditions":data["weather"][0]["main"],
        "icon":data["weather"][0]["icon"]
    }


def build_features(weather, aircraft):

    weather_score={
        "Clear":1,
        "Clouds":2,
        "Rain":3,
        "Snow":4,
        "Thunderstorm":5
    }

    return[
        weather["temp"],
        weather["humidity"],
        weather_score.get(weather["conditions"],2),
        map_aircraft_type(aircraft)
    ]


@app.route("/",methods=["GET","POST"])
def index():

    prediction=None
    risk_score=None
    reason=None
    weather=None

    if request.method=="POST":

        city=request.form.get("city")
        aircraft=request.form.get("aircraft")

        weather=get_weather(city)

        if not weather:
            prediction="Weather API error"
        else:

            current_time=datetime.now().strftime("%B %d, %Y - %H:%M")

            features=build_features(weather,aircraft)

            if model:
                try:
                    pred=model.predict([features])[0]
                    prediction=f"Predicted Damage Level: {pred}"
                except:
                    risk_score=compute_rule_based_risk(
                        weather["temp"],
                        weather["humidity"],
                        weather["wind"],
                        weather["visibility"]
                    )
                    prediction=f"Risk Score: {risk_score}%"

            else:
                risk_score=compute_rule_based_risk(
                    weather["temp"],
                    weather["humidity"],
                    weather["wind"],
                    weather["visibility"]
                )
                prediction=f"Risk Score: {risk_score}%"

            reason={
                "datetime":current_time,
                "city":city,
                "weather":weather["conditions"],
                "temperature":weather["temp"],
                "humidity":weather["humidity"],
                "wind":weather["wind"],
                "visibility":weather["visibility"],
                "aircraft":aircraft
            }

    return render_template(
        "index.html",
        cities=CITIES,
        aircraft_list=AIRCRAFT_TYPES,
        prediction=prediction,
        risk_score=risk_score,
        reason=reason,
        weather=weather
    )


if __name__=="__main__":
    app.run(debug=True)