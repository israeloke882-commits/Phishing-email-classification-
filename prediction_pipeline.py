import joblib
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

class PhishingDetector:
    def __init__(self):
        self.lr_model = joblib.load('models/lr_model.pkl')
        self.rf_model = joblib.load('models/rf_model.pkl')
        self.tfidf_vectorizer = joblib.load('models/tfidf_vectorizer.pkl')
        self.tokenizer = joblib.load('models/tokenizer.pkl')
        self.lstm_model = load_model('models/lstm_model.h5')
        self.max_len = 100
        self.ensemble_threshold = 0.5 # Threshold for the averaged score
    
    def predict(self, email_text):
        # --- All models make a prediction ---
        tfidf_features = self.tfidf_vectorizer.transform([email_text])
        lr_proba = self.lr_model.predict_proba(tfidf_features)[0][1]
        rf_proba = self.rf_model.predict_proba(tfidf_features)[0][1]
        
        seq = self.tokenizer.texts_to_sequences([email_text])
        padded = pad_sequences(seq, maxlen=self.max_len)
        lstm_proba = float(self.lstm_model.predict(padded, verbose=0)[0][0])

        # --- Ensemble Average for Final Decision ---
        average_proba = (lr_proba + rf_proba + lstm_proba) / 3.0

        if average_proba >= self.ensemble_threshold:
            prediction = 'Phishing'
            confidence = average_proba
        else:
            prediction = 'Legitimate'
            confidence = 1 - average_proba
        
        # --- Find the closest model for attribution ---
        scores = {
            'Logistic Regression': lr_proba,
            'Random Forest': rf_proba,
            'LSTM': lstm_proba
        }
        
        closest_model = min(scores, key=lambda model: abs(scores[model] - average_proba))

        return {
            'prediction': prediction,
            'confidence': float(confidence),
            'model_stage': closest_model,
            'stage_number': 1 # Only one stage now
        }

detector = None

def get_detector():
    global detector
    if detector is None:
        print("Initializing PhishingDetector with Ensemble Average pipeline...")
        detector = PhishingDetector()
    return detector
