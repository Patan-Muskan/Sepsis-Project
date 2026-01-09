#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
from flask import Flask, request, render_template
import pickle
import warnings
import os
warnings.filterwarnings('ignore')

# ============ Model Loading Configuration ============
SKIP_MODEL_LOADING = False  # Set to True to skip model loading for testing

# Try to import Phase 3 LSTM support
PHASE3_AVAILABLE = False
if not SKIP_MODEL_LOADING:
    try:
        from tensorflow.keras.models import load_model
        from sklearn.preprocessing import StandardScaler as SSScaler
        PHASE3_AVAILABLE = True
    except Exception as e:
        print(f"[WARNING] TensorFlow not available: {e}")
        PHASE3_AVAILABLE = False

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')

# Model and scaler placeholders
model = None
scaler = None
scaling_params = None
phase3_lstm_model = None
phase3_scaler = None
phase3_available = False
threshold_info = None
optimal_threshold = 0.5

if not SKIP_MODEL_LOADING:
    # List available model files
    print("[INFO] Checking available model files...")
    model_files = {
        'model_calibrated.pkl': os.path.exists('model_calibrated.pkl'),
        'scaler_calibrated.pkl': os.path.exists('scaler_calibrated.pkl'),
        'model_phase2.pkl': os.path.exists('model_phase2.pkl'),
        'model.pkl': os.path.exists('model.pkl'),
        'scaler.pkl': os.path.exists('scaler.pkl'),
        'model_phase3_lstm.h5': os.path.exists('model_phase3_lstm.h5'),
        'scaler_phase3.pkl': os.path.exists('scaler_phase3.pkl'),
    }
    for f, exists in model_files.items():
        print(f"  - {f}: {'✓ Found' if exists else '✗ Missing'}")
    
    # Try to load models in order of preference
    model_loaded = False
    
    # Option 1: Calibrated model
    if model_files['model_calibrated.pkl'] and model_files['scaler_calibrated.pkl']:
        try:
            model = pickle.load(open('model_calibrated.pkl', 'rb'))
            scaler = pickle.load(open('scaler_calibrated.pkl', 'rb'))
            if os.path.exists('scaling_params.pkl'):
                scaling_params = pickle.load(open('scaling_params.pkl', 'rb'))
            print("[INFO] Using Calibrated model with probability scaling")
            model_loaded = True
        except Exception as e:
            print(f"[WARNING] Failed to load calibrated model: {e}")
    
    # Option 2: Phase 2 model
    if not model_loaded and model_files['model_phase2.pkl']:
        try:
            model = pickle.load(open('model_phase2.pkl', 'rb'))
            if hasattr(model, 'n_features_in_') and model.n_features_in_ == 43:
                print("[INFO] Phase 2 model requires trend features - skipping")
                model = None
            else:
                if model_files['scaler.pkl']:
                    scaler = pickle.load(open('scaler.pkl', 'rb'))
                print("[INFO] Using Phase 2 model")
                model_loaded = True
        except Exception as e:
            print(f"[WARNING] Failed to load Phase 2 model: {e}")
    
    # Option 3: Phase 1 model (fallback)
    if not model_loaded and model_files['model.pkl']:
        try:
            model = pickle.load(open('model.pkl', 'rb'))
            if model_files['scaler.pkl']:
                scaler = pickle.load(open('scaler.pkl', 'rb'))
            print("[INFO] Using Phase 1 model (model.pkl)")
            model_loaded = True
        except Exception as e:
            print(f"[ERROR] Failed to load Phase 1 model: {e}")
    
    if not model_loaded:
        print("[ERROR] No ML model could be loaded! Server will return test responses.")
    
    # Load Phase 2 threshold info if available
    if os.path.exists('threshold_info.pkl'):
        try:
            threshold_info = pickle.load(open('threshold_info.pkl', 'rb'))
            optimal_threshold = threshold_info.get('optimal_threshold', 0.5)
        except:
            pass

    # Load Phase 3 LSTM model if available
    if PHASE3_AVAILABLE and model_files['model_phase3_lstm.h5'] and model_files['scaler_phase3.pkl']:
        try:
            phase3_lstm_model = load_model('model_phase3_lstm.h5')
            phase3_scaler = pickle.load(open('scaler_phase3.pkl', 'rb'))
            phase3_available = True
            print("[INFO] Phase 3 LSTM model loaded - 6-hour advance prediction available")
        except Exception as e:
            print(f"[WARNING] Phase 3 LSTM not available: {e}")
            phase3_available = False
else:
    print("[INFO] SKIP_MODEL_LOADING=True - Running without ML models for testing")

# Phase 3 LSTM feature columns
PHASE3_FEATURES = [
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp',
    'BaseExcess', 'HCO3', 'FiO2', 'PaCO2', 'SaO2', 'Creatinine',
    'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium', 'Phosphate',
    'Bilirubin_total', 'Hgb', 'WBC', 'Fibrinogen', 'Platelets'
]

# Base features (27 features)
FEATURE_NAMES = [
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp',
    'BaseExcess', 'HCO3', 'FiO2', 'PaCO2', 'SaO2', 'Creatinine',
    'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium', 'Phosphate',
    'Bilirubin_total', 'Hgb', 'WBC', 'Fibrinogen', 'Platelets',
    'Age', 'Gender', 'HospAdmTime', 'ICULOS'
]

# Phase 2 trend features (optional)
TREND_FEATURES = [
    'HR_trend_1h', 'HR_volatility', 'O2Sat_trend_1h', 'O2Sat_volatility',
    'Temp_trend_1h', 'Temp_volatility', 'Lactate_trend_1h', 'Lactate_volatility',
    'SBP_trend_1h', 'SBP_volatility', 'Creatinine_trend_1h', 'Creatinine_volatility',
    'WBC_trend_1h', 'WBC_volatility', 'Glucose_trend_1h', 'Glucose_volatility'
]

# Clinical reference ranges for warning indicators
CLINICAL_RANGES = {
    'HR': (60, 100, 'beats/min'),
    'O2Sat': (95, 100, '%'),
    'Temp': (36.5, 37.5, '°C'),
    'SBP': (90, 120, 'mm Hg'),
    'MAP': (70, 100, 'mm Hg'),
    'DBP': (60, 80, 'mm Hg'),
    'Resp': (12, 20, 'breaths/min'),
    'Lactate': (0.5, 2.0, 'mmol/L'),
    'Glucose': (70, 100, 'mg/dL'),
    'Creatinine': (0.7, 1.3, 'mg/dL'),
    'WBC': (4.5, 11, 'K/µL'),
    'Hgb': (13.5, 17.5, 'g/dL'),
}

@app.route('/')
def home():
    return render_template('index.html')

def get_abnormal_features(features_dict):
    """
    Identify which features are outside normal ranges
    """
    abnormal = []
    for feature_name, value in features_dict.items():
        if feature_name in CLINICAL_RANGES and value != '':
            try:
                val = float(value)
                min_val, max_val, unit = CLINICAL_RANGES[feature_name]
                if val < min_val or val > max_val:
                    abnormal.append({
                        'feature': feature_name,
                        'value': val,
                        'normal_range': f"{min_val}-{max_val}",
                        'unit': unit,
                        'direction': 'HIGH' if val > max_val else 'LOW'
                    })
            except:
                pass
    
    # Sort by severity (furthest from normal range)
    abnormal.sort(key=lambda x: abs(x['value'] - (CLINICAL_RANGES[x['feature']][1] + CLINICAL_RANGES[x['feature']][0]) / 2), reverse=True)
    return abnormal

def detect_vital_instability(features_dict):
    """
    Detect critical vital sign fluctuations/instability.
    Note: This is for clinical instability detection, NOT sepsis inference.
    """
    instability_indicators = []
    severity_score = 0
    
    # Critical thresholds for vital signs
    # Note: O2Sat has no critical_high (100% is perfect, not critical)
    critical_vitals = {
        'HR': {'normal_range': (60, 100), 'critical_high': 130, 'critical_low': 40},
        'O2Sat': {'normal_range': (95, 100), 'critical_high': None, 'critical_low': 88},  # 100% is normal, not critical
        'Temp': {'normal_range': (36.5, 37.5), 'critical_high': 40, 'critical_low': 35},
        'SBP': {'normal_range': (90, 140), 'critical_high': 180, 'critical_low': 70},
        'Resp': {'normal_range': (12, 20), 'critical_high': 30, 'critical_low': 8},
    }
    
    for vital, thresholds in critical_vitals.items():
        try:
            value = float(features_dict.get(vital, 0))
            if value == 0:
                continue
            
            min_normal, max_normal = thresholds['normal_range']
            critical_high = thresholds['critical_high']
            critical_low = thresholds['critical_low']
            
            # Check for critically abnormal values
            is_critical = False
            if critical_low is not None and value <= critical_low:
                is_critical = True
            if critical_high is not None and value >= critical_high:
                is_critical = True
            
            if is_critical:
                instability_indicators.append({
                    'vital': vital,
                    'value': value,
                    'severity': 'CRITICAL',
                    'description': f'{vital} is critically abnormal ({value:.1f})',
                    'concern': 'Critical vital sign deviation - immediate attention required'
                })
                severity_score += 3
            
            # Check for values outside normal range but not critical
            elif value > max_normal or value < min_normal:
                instability_indicators.append({
                    'vital': vital,
                    'value': value,
                    'severity': 'ABNORMAL',
                    'description': f'{vital} is outside normal range ({value:.1f})',
                    'concern': 'Deviation from normal - monitoring advised'
                })
                severity_score += 1
        
        except (ValueError, TypeError):
            pass
    
    return {
        'indicators': instability_indicators,
        'severity_score': severity_score,
        'has_instability': severity_score > 0
    }

def generate_explanation(features_dict, prediction, confidence):
    """
    Generate a comprehensive explanation based on abnormal values and vital instability.
    Clearly separates ML Sepsis Risk from Clinical Instability.
    """
    abnormal_features = get_abnormal_features(features_dict)
    vital_instability = detect_vital_instability(features_dict)
    
    html = '<div style="margin-top: 20px;">'
    
    # Collect all abnormal vitals to avoid duplicates
    shown_vitals = set()
    
    # Show vital instability warnings if present (CRITICAL values only)
    critical_indicators = [i for i in vital_instability['indicators'] if i['severity'] == 'CRITICAL']
    
    if critical_indicators:
        severity_colors = {
            'CRITICAL': '#ff6b6b',
            'ABNORMAL': '#ff9f43'
        }
        
        html += '''
        <div style="background: rgba(255, 107, 107, 0.1); border: 2px solid rgba(255, 107, 107, 0.4); 
                    border-radius: 10px; padding: 15px; margin-bottom: 15px;">
            <h5 style="color: #ff6b6b;">🚨 Critical Vital Sign Alert</h5>
            <p style="color: #b0b0b0; margin-bottom: 10px;">Critical values detected requiring immediate attention:</p>
            <ul style="color: #b0b0b0; margin-left: 20px;">
        '''
        
        for indicator in critical_indicators:
            color = severity_colors.get(indicator['severity'], '#facc15')
            severity_badge = f'<span style="background: {color}; color: #0a0e27; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">{indicator["severity"]}</span>'
            html += f'''
            <li style="color: #b0b0b0; margin-bottom: 10px;">
                <strong style="color: {color};">{indicator['vital']}</strong>: {indicator['value']:.1f} {severity_badge}
                <br><span style="color: #999; margin-left: 20px;">→ {indicator['concern']}</span>
            </li>
            '''
            shown_vitals.add(indicator['vital'])
        
        html += '</ul></div>'
    
    # Show other abnormal values (excluding already shown critical vitals)
    other_abnormal = [f for f in abnormal_features if f['feature'] not in shown_vitals]
    
    if other_abnormal:
        html += '''
        <div style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.2); 
                    border-radius: 10px; padding: 15px; margin-bottom: 15px;">
            <h5 style="color: #ffd700;">⚠️ Abnormal Clinical Values</h5>
            <p style="color: #b0b0b0; margin-bottom: 10px;">Values outside normal ranges:</p>
            <ul style="color: #b0b0b0; margin-left: 20px;">
        '''
        
        for item in other_abnormal[:8]:  # Show top 8 abnormal values
            color = '#ff6b6b' if item['direction'] == 'HIGH' else '#facc15'
            html += f'''
            <li style="color: {color}; margin-bottom: 8px;">
                <strong>{item['feature']}</strong>: {item['value']:.2f} {item['unit']} 
                <span style="color: #b0b0b0;">({item['direction']} - Normal: {item['normal_range']} {item['unit']})</span>
            </li>
            '''
        
        html += '</ul></div>'
    
    # Show "all normal" only if no abnormalities at all
    if not critical_indicators and not other_abnormal:
        html += '''
        <div style="background: rgba(74, 222, 128, 0.08); border: 1px solid rgba(74, 222, 128, 0.2); 
                    border-radius: 10px; padding: 15px; margin-bottom: 15px;">
            <h5 style="color: #4ade80;">✓ All Clinical Values Within Normal Ranges</h5>
            <p style="color: #b0b0b0;">All monitored parameters are within normal clinical ranges.</p>
        </div>
        '''
    
    html += '</div>'
    return html

def calculate_continuous_risk_trajectory(form_data, current_sepsis_probability):
    """
    Calculate continuous, trend-based 6-7 hour sepsis risk trajectory.
    
    MANDATORY CLINICAL RULES:
    1. If ALL vitals/labs are normal with NO abnormal trends → NO future risk prediction
       Output: "Future risk not indicated" (return None for future_risk_6h)
    2. Early sepsis prediction (6-7 hours) is ONLY allowed if:
       - Abnormal values exist, OR
       - Worsening trends are detected, OR
       - Subclinical instability is present
    3. DO NOT assign numeric sepsis probabilities when no clinical trigger exists
    4. Avoid unnecessary percentages like 5-10% in fully normal patients
    
    This is a CLINICAL DECISION SUPPORT TOOL, not a speculative risk generator.
    Avoid false alarms and unnecessary risk inflation.
    
    Returns:
        dict: {
            'current_risk': float (0-1),
            'future_risk_6h': float (0-1) or None if not indicated,
            'trajectory': str ('escalating', 'stable', 'improving', 'not_indicated'),
            'risk_velocity': float (-1 to 1, rate of change),
            'clinical_trigger_present': bool
        }
    """
    
    # Define optimal physiological ranges (center of comfort zone)
    optimal_ranges = {
        'HR': {'optimal': 70, 'min': 60, 'max': 100, 'critical_low': 40, 'critical_high': 150},
        'Temp': {'optimal': 37.0, 'min': 36.5, 'max': 37.5, 'critical_low': 35, 'critical_high': 40},
        'SBP': {'optimal': 110, 'min': 90, 'max': 130, 'critical_low': 70, 'critical_high': 200},
        'MAP': {'optimal': 85, 'min': 70, 'max': 100, 'critical_low': 50, 'critical_high': 150},
        'DBP': {'optimal': 70, 'min': 60, 'max': 85, 'critical_low': 40, 'critical_high': 120},
        'Resp': {'optimal': 16, 'min': 12, 'max': 20, 'critical_low': 8, 'critical_high': 40},
        'O2Sat': {'optimal': 97, 'min': 95, 'max': 100, 'critical_low': 88, 'critical_high': 100},
        'Glucose': {'optimal': 85, 'min': 70, 'max': 100, 'critical_low': 40, 'critical_high': 300},
        'Lactate': {'optimal': 1.2, 'min': 0.5, 'max': 2.0, 'critical_low': 0.2, 'critical_high': 10},
        'WBC': {'optimal': 7, 'min': 4.5, 'max': 11, 'critical_low': 1, 'critical_high': 50},
    }
    
    def calculate_deviation_risk(value, param_name):
        """
        Calculate continuous risk contribution (0-1) from a single parameter.
        Uses smooth Gaussian-like curve centered on optimal range.
        """
        try:
            value = float(value)
        except:
            return 0.0
        
        if param_name not in optimal_ranges:
            return 0.0
        
        ranges = optimal_ranges[param_name]
        optimal = ranges['optimal']
        normal_min = ranges['min']
        normal_max = ranges['max']
        critical_low = ranges['critical_low']
        critical_high = ranges['critical_high']
        
        # If within optimal range -> minimal risk
        if normal_min <= value <= normal_max:
            # Smooth function: highest at center, increases toward edges
            center_distance = abs(value - optimal)
            normal_range = (normal_max - normal_min) / 2
            # Returns 0 at optimal, rises to ~0.1-0.2 at range edges
            return (center_distance / normal_range) * 0.2
        
        # If outside normal range -> progressive risk scaling
        elif value < normal_min:
            # Below normal: scale from 0.2 (at edge) to 1.0 (at critical)
            range_below = normal_min - critical_low
            if range_below <= 0:
                return 0.5 if value < normal_min else 0.0
            distance = normal_min - value
            risk = 0.2 + (distance / range_below) * 0.8
            return min(1.0, risk)
        
        else:  # Above normal
            # Above normal: scale from 0.2 (at edge) to 1.0 (at critical)
            range_above = critical_high - normal_max
            if range_above <= 0:
                return 0.5 if value > normal_max else 0.0
            distance = value - normal_max
            risk = 0.2 + (distance / range_above) * 0.8
            return min(1.0, risk)
    
    # Calculate continuous risk contributions from key vitals
    vital_deviations = {}
    for param in ['HR', 'Temp', 'SBP', 'MAP', 'Resp', 'O2Sat', 'Glucose', 'Lactate', 'WBC']:
        value = form_data.get(param, '')
        if value:
            vital_deviations[param] = calculate_deviation_risk(value, param)
    
    # Combined vital risk: average of all deviations (gives equal weight to each vital)
    if vital_deviations:
        vital_risk = np.mean(list(vital_deviations.values()))
    else:
        vital_risk = 0.0
    
    # ===== MANDATORY CLINICAL TRIGGER CHECK =====
    # Count vitals with significant deviations (>0.3 risk contribution)
    significantly_abnormal = sum(1 for v in vital_deviations.values() if v > 0.3)
    
    # Count vitals with moderate deviations (0.15-0.3 risk)
    moderately_abnormal = sum(1 for v in vital_deviations.values() if 0.15 <= v <= 0.3)
    
    # Calculate abnormality burden
    abnormality_burden = (significantly_abnormal * 0.4) + (moderately_abnormal * 0.15)
    abnormality_burden = min(1.0, abnormality_burden)
    
    # MANDATORY RULE: Check if clinical trigger exists
    # Clinical trigger = abnormal values OR worsening trends OR subclinical instability
    # Be more permissive - if ANY vital shows deviation OR model has any risk, show prediction
    clinical_trigger_present = (
        significantly_abnormal > 0 or 
        moderately_abnormal >= 1 or  # Reduced from 2 to 1
        vital_risk > 0.10 or  # Reduced from 0.15 to 0.10
        current_sepsis_probability > 0.15  # Reduced from 0.20 to 0.15
    )
    
    # ===== GENERATE PREDICTION FOR ALL NON-NORMAL PATIENTS =====
    # Only skip prediction if truly all values are normal
    if not clinical_trigger_present and vital_risk < 0.05:
        return {
            'current_risk': 0.0,  # No risk when all normal
            'future_risk_6h': None,  # NOT INDICATED - no speculative percentages
            'trajectory': 'not_indicated',
            'risk_velocity': 0.0,
            'vital_deviations': vital_deviations,
            'abnormality_burden': 0.0,
            'clinical_trigger_present': False
        }
    
    # ===== STANDARD TRAJECTORY LOGIC (only when clinical trigger exists) =====
    # Blend with model's current sepsis probability
    # Current risk = 60% from model, 40% from vital deviations
    blended_current_risk = (0.6 * current_sepsis_probability) + (0.4 * vital_risk)
    blended_current_risk = max(0.0, min(1.0, blended_current_risk))
    
    # ===== 6-HOUR TRAJECTORY CALCULATION (only for patients with clinical triggers) =====
    if blended_current_risk >= 0.7:
        # Very high risk: monitor for stabilization or escalation
        if abnormality_burden >= 0.6:
            # Very high risk with severe abnormalities -> escalating
            risk_velocity = 0.12
            trajectory = 'escalating'
        elif abnormality_burden >= 0.3:
            # High risk with moderate abnormalities -> slightly escalating
            risk_velocity = 0.06
            trajectory = 'escalating'
        else:
            # High risk but fewer abnormalities -> stable or slight improvement
            risk_velocity = 0.02
            trajectory = 'stable'
    
    elif blended_current_risk >= 0.5:
        # Moderate-high risk
        if abnormality_burden >= 0.6:
            # Significant abnormalities -> escalate
            risk_velocity = 0.18
            trajectory = 'escalating'
        elif abnormality_burden >= 0.3:
            # Some abnormalities -> gradual escalation
            risk_velocity = 0.10
            trajectory = 'escalating'
        else:
            # Minimal abnormalities -> stable
            risk_velocity = 0.03
            trajectory = 'stable'
    
    elif blended_current_risk >= 0.3:
        # Moderate risk
        if abnormality_burden >= 0.5:
            # Significant abnormalities -> early warning escalates risk
            risk_velocity = 0.15
            trajectory = 'escalating'
        elif abnormality_burden >= 0.2:
            # Mild abnormalities -> slight escalation
            risk_velocity = 0.05
            trajectory = 'stable'
        else:
            # Minimal abnormalities -> improving
            risk_velocity = -0.02
            trajectory = 'improving'
    
    else:
        # Low current risk (1-30%)
        if abnormality_burden >= 0.4:
            # Emerging abnormalities in low-risk patient -> early warning signal
            # But cap escalation at reasonable levels
            risk_velocity = min(0.08, abnormality_burden * 0.15)
            trajectory = 'escalating'
        elif abnormality_burden >= 0.2:
            # Minimal abnormalities -> stay stable
            risk_velocity = 0.01
            trajectory = 'stable'
        else:
            # Very few abnormalities -> improve
            risk_velocity = -0.02
            trajectory = 'improving'
    
    # Calculate future risk with logical continuity
    future_risk = blended_current_risk + risk_velocity
    future_risk = max(0.0, min(1.0, future_risk))
    
    return {
        'current_risk': blended_current_risk,
        'future_risk_6h': future_risk,
        'trajectory': trajectory,
        'risk_velocity': risk_velocity,
        'vital_deviations': vital_deviations,
        'abnormality_burden': abnormality_burden,
        'clinical_trigger_present': True  # Only reaches here if trigger exists
    }

def get_sepsis_risk_label(probability):
    """
    Strict probability-to-label mapping for SEPSIS RISK (ML-based).
    
    0–20% → Low Sepsis Risk
    21–50% → Moderate Sepsis Risk
    51–75% → High Sepsis Risk
    76–100% → Critical Sepsis Risk
    """
    prob_percent = probability * 100
    
    if prob_percent <= 20:
        return 'Low Sepsis Risk', '#51cf66', 'green'
    elif prob_percent <= 50:
        return 'Moderate Sepsis Risk', '#facc15', 'yellow'
    elif prob_percent <= 75:
        return 'High Sepsis Risk', '#ff9f43', 'orange'
    else:  # > 75%
        return 'Critical Sepsis Risk', '#ff6b6b', 'red'


def get_clinical_instability_label(severity_score, abnormal_count):
    """
    Label for CLINICAL INSTABILITY (rule-based, non-sepsis).
    """
    if severity_score >= 5 or abnormal_count >= 5:
        return 'High Clinical Instability', '#ff6b6b', 'red'
    elif severity_score >= 3 or abnormal_count >= 3:
        return 'Moderate Clinical Instability', '#ff9f43', 'orange'
    elif severity_score >= 1 or abnormal_count >= 1:
        return 'Mild Clinical Instability', '#facc15', 'yellow'
    else:
        return 'Stable', '#51cf66', 'green'


@app.route('/predict', methods=['POST'])
def predict():
    '''
    Predict CURRENT sepsis risk based on patient vital signs and lab values.
    
    Returns:
    - "Prone to Sepsis" if ML risk >= 50%
    - "Clinically Unstable" if ML risk < 50% but severe vital abnormalities
    - "Not Prone to Sepsis" if ML risk < 50% and stable vitals
    
    Note: This model predicts CURRENT sepsis risk only.
    '''
    # Default safe values in case of any failure
    prediction_status = "unknown"
    current_risk = 0.0
    risk_label = "Unknown"
    prediction_success = False
    error_message = None
    
    try:
        # Check if model is loaded
        if model is None:
            return render_template(
                'index.html',
                prediction_text="Model Not Loaded",
                confidence="0.00%",
                explanation="<div style='color: #ff6b6b;'>ML model is not available. Please check server configuration.</div>",
                risk_level="Not Prone to Sepsis",
                model_version="No Model",
                phase3_risk="",
                is_normal_state=True,
                prediction_status="error"
            )
        
        # Get form data
        form_data = request.form.to_dict()
        features = []
        
        # Convert to float, handle empty values with 0
        for feature_name in FEATURE_NAMES:
            try:
                val = float(form_data.get(feature_name, 0))
            except:
                val = 0
            features.append(val)
        
        final_features = np.array(features).reshape(1, -1)
        
        # Apply scaler if available
        if scaler is not None:
            final_features = scaler.transform(final_features)
        
        # ===== MAKE PREDICTION =====
        probability = model.predict_proba(final_features)[0]
        prob_sepsis = float(probability[1])  # Probability of sepsis (class 1)
        
        # Apply probability scaling if available
        if scaling_params is not None:
            prob_min = scaling_params['prob_min']
            prob_max = scaling_params['prob_max']
            prob_sepsis = (prob_sepsis - prob_min) / (prob_max - prob_min)
        
        # Ensure probability is in valid range [0, 1]
        current_risk = max(0.0, min(1.0, prob_sepsis))
        prediction_success = True
        
        # ===== CHECK FOR ABNORMAL VALUES (for clinical alerts only, NOT sepsis determination) =====
        abnormal_features = get_abnormal_features(form_data)
        vital_instability = detect_vital_instability(form_data)
        
        has_abnormal_values = len(abnormal_features) > 0
        has_vital_instability = vital_instability['severity_score'] > 0
        
        # ===== DETERMINE SEPSIS PRONE STATUS =====
        # Sepsis status determined ONLY by ML model output
        # Threshold: >= 50% = Prone to Sepsis
        # Clinical communication clarity for vital instability
        
        is_prone_to_sepsis = (current_risk >= 0.5)
        is_critically_unstable = (vital_instability['severity_score'] >= 3) or (len(abnormal_features) >= 3)
        
        # Get clinical instability label (rule-based, separate from sepsis)
        instability_label, instability_color, instability_class = get_clinical_instability_label(
            vital_instability['severity_score'], len(abnormal_features)
        )
        
        if is_prone_to_sepsis:
            # ===== PRONE TO SEPSIS (ML Sepsis Risk >= 50%) =====
            prediction_status = "prone"
            risk_label, label_color, label_class = get_sepsis_risk_label(current_risk)
            
            prediction_text = f"Prone to Sepsis"
            confidence_display = f"{current_risk * 100:.2f}%"
            
            explanation_html = generate_explanation(form_data, 1, current_risk * 100)
            
            prone_banner = f"""
            <div style="background: rgba(255, 107, 107, 0.15); border: 2px solid rgba(255, 107, 107, 0.4); 
                        border-radius: 10px; padding: 15px; margin-bottom: 15px;">
                <h5 style="color: #ff6b6b; margin-top: 0;">⚠️ Patient is Prone to Sepsis</h5>
                <p style="color: #b0b0b0; margin-bottom: 10px;">
                    <strong>ML Sepsis Risk:</strong> {current_risk * 100:.1f}% — {risk_label}
                </p>
                <p style="color: #b0b0b0; margin-bottom: 10px;">
                    <strong>Clinical Instability:</strong> {instability_label}
                </p>
                <p style="color: #b0b0b0;">
                    <strong>Recommendation:</strong> Immediate clinical evaluation recommended. Consider sepsis protocols.
                </p>
            </div>
            """
            explanation_html = prone_banner + explanation_html
            
            return render_template(
                'index.html',
                prediction_text=prediction_text,
                confidence=confidence_display,
                explanation=explanation_html,
                risk_level=risk_label,
                model_version="Phase 1 MLP",
                phase3_risk="",
                is_normal_state=False,
                prediction_status=prediction_status
            )
        
        elif is_critically_unstable:
            # ===== HIGH CLINICAL INSTABILITY (Non-Sepsis) =====
            # ML sepsis risk is LOW, but vital signs are critically abnormal
            prediction_status = "unstable"
            sepsis_risk_label, _, _ = get_sepsis_risk_label(current_risk)
            risk_label = instability_label  # Use clinical instability label
            confidence_display = f"{current_risk * 100:.1f}%"
            prediction_text = f"{instability_label} (Non-Sepsis)"
            
            explanation_html = f"""
            <div style="background: rgba(255, 159, 67, 0.15); border: 2px solid rgba(255, 159, 67, 0.4); 
                        border-radius: 10px; padding: 20px; margin-bottom: 15px;">
                <h5 style="color: #ff9f43; margin-top: 0;">⚠️ {instability_label} (Non-Sepsis)</h5>
                <p style="color: #b0b0b0; margin-bottom: 10px;">
                    <strong>ML Sepsis Risk:</strong> {current_risk * 100:.1f}% — {sepsis_risk_label} (below sepsis threshold)
                </p>
                <p style="color: #b0b0b0; margin-bottom: 10px;">
                    <strong>Clinical Instability:</strong> {instability_label} — Significant physiological abnormalities detected.
                </p>
                <p style="color: #b0b0b0;">
                    <strong>Recommendation:</strong> Investigate underlying cause of instability. Do NOT initiate sepsis protocols based on vitals alone.
                </p>
            </div>
            """
            
            # Add detailed abnormal values
            explanation_html += generate_explanation(form_data, 0, current_risk * 100)
            
            return render_template(
                'index.html',
                prediction_text=prediction_text,
                confidence=confidence_display,
                explanation=explanation_html,
                risk_level=risk_label,
                model_version="Phase 1 MLP",
                phase3_risk="",
                is_normal_state=False,
                prediction_status=prediction_status
            )
        
        else:
            # ===== NOT PRONE TO SEPSIS (Low ML risk AND stable vitals) =====
            prediction_status = "not_prone"
            sepsis_risk_label, _, _ = get_sepsis_risk_label(current_risk)
            risk_label = "Not Prone to Sepsis"
            confidence_display = f"{current_risk * 100:.1f}%"
            prediction_text = "Not Prone to Sepsis"
            
            explanation_html = f"""
            <div style="background: rgba(81, 207, 102, 0.1); border: 2px solid rgba(81, 207, 102, 0.3); 
                        border-radius: 10px; padding: 20px; margin-bottom: 15px;">
                <h5 style="color: #4ade80; margin-top: 0;">✓ Patient is Not Prone to Sepsis</h5>
                <p style="color: #b0b0b0; margin-bottom: 10px;">
                    <strong>ML Sepsis Risk:</strong> {current_risk * 100:.1f}% — {sepsis_risk_label}
                </p>
                <p style="color: #b0b0b0; margin-bottom: 10px;">
                    <strong>Clinical Instability:</strong> {instability_label}
                </p>
                <p style="color: #b0b0b0;">
                    <strong>Recommendation:</strong> Continue routine clinical monitoring.
                </p>
            </div>
            """
            
            # Add minor abnormalities if present (not critical)
            if has_vital_instability or has_abnormal_values:
                explanation_html += generate_explanation(form_data, 0, current_risk * 100)
            
            return render_template(
                'index.html',
                prediction_text=prediction_text,
                confidence=confidence_display,
                explanation=explanation_html,
                risk_level=risk_label,
                model_version="Phase 1 MLP",
                phase3_risk="",
                is_normal_state=True,
                prediction_status=prediction_status
            )
    
    except Exception as e:
        # ===== ERROR HANDLING - Return safe defaults =====
        error_message = str(e)
        print(f"[ERROR] Prediction failed: {error_message}")
        
        return render_template(
            'index.html',
            prediction_text="Prediction Error",
            confidence="0.00%",
            explanation=f"<div style='color: #ff6b6b;'>An error occurred during prediction: {error_message}</div>",
            risk_level="Not Prone to Sepsis",
            model_version="Error",
            phase3_risk="",
            is_normal_state=True,
            prediction_status="error"
        )


@app.route('/predict_phase3', methods=['POST'])
def predict_phase3():
    """
    Phase 3: LSTM-based 6-hour advance prediction
    Requires 12-hour historical patient data (sequence of measurements)
    """
    try:
        if not phase3_available:
            return render_template('index.html', 
                error="Phase 3 LSTM model not available. Using Phase 1/2 prediction instead.")
        
        form_data = request.form.to_dict()
        
        # Build 12-timestep sequence from historical data
        sequence = []
        for t in range(12):
            timestep = []
            for feature in PHASE3_FEATURES:
                field_name = f"{feature}_t{t}"
                try:
                    val = float(form_data.get(field_name, 0))
                except (ValueError, TypeError):
                    val = 0
                timestep.append(val)
            sequence.append(timestep)
        
        # Convert to numpy array and reshape
        X_sequence = np.array([sequence])  # Shape: (1, 12, 20)
        
        # Scale the sequence
        n_samples, n_timesteps, n_features = X_sequence.shape
        X_reshaped = X_sequence.reshape(-1, n_features)
        X_scaled = phase3_scaler.transform(X_reshaped)
        X_sequence_scaled = X_scaled.reshape(n_samples, n_timesteps, n_features)
        
        # Make prediction
        predictions = phase3_lstm_model.predict(X_sequence_scaled, verbose=0)
        
        # Get 6-step ahead average prediction (next 6 hours)
        sepsis_risk_6h = float(np.mean(predictions[0, :6, 0]))  # Average of first 6 timesteps
        sepsis_risk_6h = max(0.0, min(1.0, sepsis_risk_6h))  # Clip to [0, 1]
        
        # Determine risk level
        if sepsis_risk_6h >= 0.5:
            risk_level = "HIGH RISK (6-hour)"
            prediction_text = f"⚠️ 6-Hour Advance Warning: {sepsis_risk_6h*100:.1f}% Sepsis Risk"
            confidence = sepsis_risk_6h * 100
        else:
            risk_level = "LOW RISK (6-hour)"
            prediction_text = f"✓ 6-Hour Outlook: {(1-sepsis_risk_6h)*100:.1f}% Probability of Remaining Stable"
            confidence = (1 - sepsis_risk_6h) * 100
        
        # Generate Phase 3 specific explanation
        explanation = f"""
        <div class="phase3-explanation">
            <h4><i class="fas fa-clock"></i> 6-Hour Advance Prediction (Phase 3 LSTM)</h4>
            <p>This prediction analyzes the temporal patterns from the past 12 hours of patient data
            to forecast sepsis risk for the next 6 hours.</p>
            <div class="risk-details">
                <p><strong>Predicted Risk (6h ahead):</strong> {sepsis_risk_6h*100:.1f}%</p>
                <p><strong>Clinical Action:</strong> 
                {'Start prophylactic monitoring and prepare early interventions' if sepsis_risk_6h >= 0.5 else 'Continue standard monitoring'}
                </p>
            </div>
        </div>
        """
        
        return render_template(
            'index.html',
            prediction_text=prediction_text,
            confidence=f"{confidence:.2f}%",
            explanation=explanation,
            risk_level=risk_level,
            model_version="LSTM Time-Series (6-hour forecast)",
            is_phase3=True
        )
    
    except Exception as e:
        error_msg = f"Phase 3 Error: {str(e)}"
        return render_template('index.html', prediction_text=error_msg, error=error_msg)


if __name__ == '__main__':
    app.run(debug=True)

