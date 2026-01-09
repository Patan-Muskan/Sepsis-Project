"""
Phase 3 Prediction Utility
Handles LSTM predictions and integrates with Flask
"""

import numpy as np
import pickle
from tensorflow import keras

# Configuration
SEQUENCE_LENGTH = 12
FEATURE_COLUMNS = [
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'EtCO2', 'BaseExcess', 'HCO3',
    'FiO2', 'pH', 'PaCO2', 'SaO2', 'AST', 'BUN', 'Alkalinephos', 'Calcium', 'Chloride', 
    'Creatinine', 'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium', 'Phosphate', 
    'Potassium', 'Hgb'
]

class Phase3LSTMPredictor:
    """LSTM model wrapper for time-series predictions"""
    
    def __init__(self, model_path='model_phase3_lstm.h5', scaler_path='scaler_phase3.pkl'):
        """Initialize Phase 3 LSTM model"""
        try:
            self.model = keras.models.load_model(model_path)
            self.scaler = pickle.load(open(scaler_path, 'rb'))
            self.ready = True
            print("[INFO] Phase 3 LSTM model loaded successfully")
        except Exception as e:
            self.ready = False
            print(f"[WARNING] Phase 3 LSTM model not available: {e}")
    
    def create_sequence(self, features_list):
        """
        Create a sequence from a list of feature vectors
        features_list: list of feature vectors [[f1, f2, ...], [f1, f2, ...], ...]
        """
        if len(features_list) < SEQUENCE_LENGTH:
            # Pad with the first sample if we don't have enough data
            while len(features_list) < SEQUENCE_LENGTH:
                features_list = [features_list[0]] + features_list
        
        # Take last SEQUENCE_LENGTH samples
        sequence = np.array(features_list[-SEQUENCE_LENGTH:])
        
        # Reshape for scaler
        n_samples, n_features = sequence.shape
        sequence_flat = sequence.reshape(-1, n_features)
        
        # Scale
        sequence_scaled = self.scaler.transform(sequence_flat)
        sequence_scaled = sequence_scaled.reshape(1, SEQUENCE_LENGTH, n_features)
        
        return sequence_scaled
    
    def predict(self, features_history):
        """
        Predict sepsis probability from historical features
        features_history: list of feature dictionaries or arrays
        Returns: probability (0-1)
        """
        if not self.ready:
            return None
        
        try:
            # Convert dict list to array list if needed
            if isinstance(features_history[0], dict):
                features_array = []
                for feat_dict in features_history:
                    feat_array = [feat_dict.get(col, 0) for col in FEATURE_COLUMNS]
                    features_array.append(feat_array)
            else:
                features_array = features_history
            
            # Create sequence
            sequence = self.create_sequence(features_array)
            
            # Predict
            prob = self.model.predict(sequence, verbose=0)[0][0]
            return float(prob)
        
        except Exception as e:
            print(f"[ERROR] Phase 3 prediction failed: {e}")
            return None

# ============================================================================
# Initialization for Flask
# ============================================================================

phase3_predictor = None

def initialize_phase3():
    """Initialize Phase 3 model (called on Flask startup)"""
    global phase3_predictor
    try:
        phase3_predictor = Phase3LSTMPredictor()
    except:
        phase3_predictor = None
