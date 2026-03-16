✈️ Aviation Accident Risk Prediction and Analysis System

Motivated by the 2025 aviation tragedy in India that claimed over 260 lives — this project applies machine learning and data analytics to identify aviation risk patterns and contribute to safer skies.

📌 Overview
This project presents a full-stack Aviation Accident Risk Prediction and Analysis System developed as a Master's project for CIS 550 – Advanced Machine Learning at the University of Massachusetts Dartmouth.
The system combines:

🤖 Machine Learning — Random Forest Classifier with SMOTE balancing
🌦️ Real-time Weather Integration — OpenWeatherMap API
🌐 Web Application — Flask-based interactive prediction interface
📊 Interactive Dashboards — Streamlit + Power BI visualizations


🎯 Objectives

Analyze historical aviation accident data to uncover patterns and trends
Develop a machine learning model to predict aircraft damage risk
Integrate real-time weather data to enhance contextual risk analysis
Build a web application for user-facing risk predictions
Create interactive dashboards for visual exploration of aviation safety data

🗃️ Dataset
Source: NTSB Aviation Accident Database
The dataset includes records of aviation incidents and accidents with the following attributes:
FieldDescriptionEvent DateDate and time of the incidentAircraft TypeMake and model of the aircraftInjury SeverityFatal / Serious / Minor / NoneAircraft DamageExtent of structural damageLocationGeographic coordinates and regionOperational DetailsFlight phase, weather conditions, etc.

The cleaned dataset is stored as NTSB Cleaned dataset.xlsx in the /data directory.


🧠 Methodology
1. Data Preprocessing

Missing value imputation
Categorical variable standardization
Label encoding for ML compatibility
Feature engineering for predictive attributes

2. Machine Learning Model
ComponentDetailAlgorithmRandom Forest ClassifierImbalance HandlingSMOTE (Synthetic Minority Oversampling Technique)Saved Modelaircraft_damage_rf_model_smote.joblib
Random Forest was chosen for its strong predictive performance, resistance to overfitting, and ability to handle mixed data types. SMOTE was applied to address the inherent class imbalance in aviation accident datasets.
3. Web Application (Flask)
Users can input aviation parameters and receive real-time damage risk predictions, enriched with live weather data from the OpenWeatherMap API.
4. Dashboards

Streamlit — Exploratory analysis with dynamic filtering and time-series charts
Power BI — Professional reporting with KPIs, injury distribution, and trend monitoring


🛠️ Technologies
CategoryToolsProgrammingPython 3.10+Machine LearningScikit-learnImbalance Handlingimbalanced-learn (SMOTE)Data AnalysisPandas, NumPyWeb FrameworkFlaskDashboardingStreamlit, Power BIVisualizationPlotlyAPI IntegrationOpenWeatherMap APIFrontendHTML, CSS

📊 Dashboard Features
Streamlit Dashboard

Interactive accident data explorer
Time-based trend analysis
Filter by year, aircraft type, severity

Power BI Dashboard

Accident statistics & KPIs
Injury severity distribution
Aircraft damage classification breakdown
Long-term safety trend monitoring


📈 Model Performance
The Random Forest Classifier trained with SMOTE oversampling achieved improved performance on minority class predictions compared to a baseline model trained on imbalanced data.

Detailed evaluation metrics (accuracy, precision, recall, F1-score, confusion matrix) are available in notebooks/model_training.ipynb.


🎓 Academic Context
FieldDetailAuthorDeepthi KavithaDegreeMaster of Science in Computer ScienceUniversityUniversity of Massachusetts DartmouthCourseCIS 550 – Advanced Machine LearningInstructorDr. Firas KhatibSubmissionMay 2026

📚 References

National Transportation Safety Board (NTSB) Aviation Accident Database
Pedregosa et al., Scikit-learn: Machine Learning in Python
Chawla et al., SMOTE: Synthetic Minority Over-sampling Technique
Flask Web Framework Documentation
Plotly Visualization Library Documentation
OpenWeatherMap API Documentation

