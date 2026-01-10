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
    Optimized: Calculate continuous risk trajectory efficiently.
    - Early return for normal patients
    - Cached ranges to avoid dict lookups
    - Minimal redundant calculations
    
    Returns:
        dict: {
            'current_risk': float (0-1),
            'future_risk_6h': float (0-1),
            'trajectory': str ('escalating', 'stable', 'improving'),
            'risk_velocity': float (-1 to 1),
            'vital_deviations': dict,
            'abnormality_burden': float
        }
    """
    
    # Cached optimal ranges (precomputed to avoid dict lookups)
    OPTIMAL_RANGES = {
        'HR': (70, 60, 100, 40, 150),
        'Temp': (37.0, 36.5, 37.5, 35, 40),
        'SBP': (110, 90, 130, 70, 200),
        'MAP': (85, 70, 100, 50, 150),
        'DBP': (70, 60, 85, 40, 120),
        'Resp': (16, 12, 20, 8, 40),
        'O2Sat': (97, 95, 100, 88, 100),
        'Glucose': (85, 70, 100, 40, 300),
        'Lactate': (1.2, 0.5, 2.0, 0.2, 10),
        'WBC': (7, 4.5, 11, 1, 50),
    }
    
    KEY_VITALS = ['HR', 'Temp', 'SBP', 'MAP', 'Resp', 'O2Sat', 'Glucose', 'Lactate', 'WBC']
    
    def fast_deviation_risk(value, param_name):
        """Fast cached deviation calculation."""
        try:
            val = float(value)
        except (ValueError, TypeError):
            return 0.0
        
        if param_name not in OPTIMAL_RANGES:
            return 0.0
        
        optimal, norm_min, norm_max, crit_low, crit_high = OPTIMAL_RANGES[param_name]
        
        if norm_min <= val <= norm_max:
            center_dist = abs(val - optimal)
            norm_range = (norm_max - norm_min) / 2
            return min(0.2, (center_dist / norm_range) * 0.2)
        elif val < norm_min:
            range_below = norm_min - crit_low
            if range_below <= 0:
                return 0.5
            dist = norm_min - val
            return min(1.0, 0.2 + (dist / range_below) * 0.8)
        else:  # val > norm_max
            range_above = crit_high - norm_max
            if range_above <= 0:
                return 0.5
            dist = val - norm_max
            return min(1.0, 0.2 + (dist / range_above) * 0.8)
    
    # Calculate vital deviations
    vital_deviations = {}
    for param in KEY_VITALS:
        value = form_data.get(param, '')
        if value:
            vital_deviations[param] = fast_deviation_risk(value, param)
    
    # Quick early exit for normal patients
    if not vital_deviations:
        return {
            'current_risk': current_sepsis_probability,
            'future_risk_6h': current_sepsis_probability,
            'trajectory': 'stable',
            'risk_velocity': 0.0,
            'vital_deviations': {},
            'abnormality_burden': 0.0
        }
    
    vital_risk = np.mean(list(vital_deviations.values()))
    
    # Early exit for truly normal patients
    if vital_risk < 0.05 and current_sepsis_probability < 0.15:
        return {
            'current_risk': 0.05,
            'future_risk_6h': 0.05,
            'trajectory': 'stable',
            'risk_velocity': 0.0,
            'vital_deviations': vital_deviations,
            'abnormality_burden': 0.0
        }
    
    # Count abnormalities (cached)
    sig_abnormal = sum(1 for v in vital_deviations.values() if v > 0.3)
    mod_abnormal = sum(1 for v in vital_deviations.values() if 0.15 <= v <= 0.3)
    abnormality_burden = min(1.0, (sig_abnormal * 0.4) + (mod_abnormal * 0.15))
    
    # Blend current risk
    blended_risk = max(0.0, min(1.0, (0.6 * current_sepsis_probability) + (0.4 * vital_risk)))
    
    # Calculate trajectory using lookup table (instead of nested ifs)
    if blended_risk >= 0.7:
        risk_velocity = 0.12 if abnormality_burden >= 0.6 else (0.06 if abnormality_burden >= 0.3 else 0.02)
        trajectory = 'escalating' if risk_velocity > 0.04 else 'stable'
    elif blended_risk >= 0.5:
        risk_velocity = 0.18 if abnormality_burden >= 0.6 else (0.10 if abnormality_burden >= 0.3 else 0.03)
        trajectory = 'escalating' if risk_velocity > 0.05 else 'stable'
    elif blended_risk >= 0.3:
        risk_velocity = 0.15 if abnormality_burden >= 0.5 else (0.05 if abnormality_burden >= 0.2 else -0.02)
        trajectory = 'escalating' if risk_velocity > 0.05 else ('stable' if risk_velocity > -0.01 else 'improving')
    else:
        risk_velocity = min(0.08, abnormality_burden * 0.15) if abnormality_burden >= 0.4 else (0.01 if abnormality_burden >= 0.2 else -0.02)
        trajectory = 'escalating' if risk_velocity > 0.05 else ('stable' if risk_velocity > -0.01 else 'improving')
    
    future_risk = max(0.0, min(1.0, blended_risk + risk_velocity))
    
    return {
        'current_risk': blended_risk,
        'future_risk_6h': future_risk,
        'trajectory': trajectory,
        'risk_velocity': risk_velocity,
        'vital_deviations': vital_deviations,
        'abnormality_burden': abnormality_burden
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
    Predict CURRENT sepsis risk - optimized for clarity and clinical sense.
    '''
    prediction_status = "unknown"
    
    try:
        if model is None:
            return render_template('index.html',
                prediction_text="Model Not Loaded",
                confidence="0.00%",
                explanation="<div style='color: #ff6b6b;'>ML model unavailable. Check server.</div>",
                risk_level="Error",
                model_version="No Model",
                phase3_risk="",
                is_normal_state=True,
                prediction_status="error"
            )
        
        form_data = request.form.to_dict()
        
        # Fast feature extraction
        features = []
        for feature_name in FEATURE_NAMES:
            try:
                val = float(form_data.get(feature_name, 0))
            except (ValueError, TypeError):
                val = 0
            features.append(val)
        
        final_features = np.array(features).reshape(1, -1)
        
        # Scale if available
        if scaler is not None:
            final_features = scaler.transform(final_features)
        
        # Make prediction
        probability = model.predict_proba(final_features)[0]
        prob_sepsis = float(probability[1])
        
        # Apply probability scaling if available
        if scaling_params is not None:
            prob_min = scaling_params['prob_min']
            prob_max = scaling_params['prob_max']
            prob_sepsis = (prob_sepsis - prob_min) / (prob_max - prob_min)
        
        current_risk = max(0.0, min(1.0, prob_sepsis))
        
        # Get abnormal features
        abnormal_features = get_abnormal_features(form_data)
        vital_instability = detect_vital_instability(form_data)
        
        # Simple, sensible logic
        is_high_risk = current_risk >= 0.5
        is_unstable = vital_instability['severity_score'] >= 2 or len(abnormal_features) >= 3
        is_normal = current_risk < 0.2 and len(abnormal_features) == 0
        
        # Determine output
        if is_high_risk:
            # HIGH SEPSIS RISK
            prediction_status = "high_risk"
            prediction_text = "HIGH SEPSIS RISK"
            confidence_display = f"{current_risk * 100:.1f}%"
            
            if current_risk >= 0.8:
                risk_label = "Critical Risk (>80%)"
                color = "#ff4444"
            elif current_risk >= 0.65:
                risk_label = "High Risk (65-80%)"
                color = "#ff9234"
            else:
                risk_label = "Moderate-High Risk (50-65%)"
                color = "#ffb81c"
            
            explanation_html = f"""
            <div style="background: rgba(255, 68, 68, 0.15); border: 2px solid {color}; 
                        border-radius: 10px; padding: 20px; margin-bottom: 15px;">
                <h4 style="color: {color}; margin-top: 0;">⚠️ High Sepsis Risk Detected</h4>
                <p style="color: #b0b0b0;"><strong>ML Risk Score:</strong> {current_risk * 100:.1f}% — {risk_label}</p>
                <p style="color: #b0b0b0;"><strong>Clinical Recommendation:</strong> 
                    Immediate clinical evaluation and sepsis protocol initiation recommended.
                </p>
            </div>
            """
            
        elif is_unstable and not is_high_risk:
            # UNSTABLE BUT NOT SEPSIS
            prediction_status = "unstable"
            prediction_text = "CLINICALLY UNSTABLE (Non-Sepsis)"
            confidence_display = f"{current_risk * 100:.1f}%"
            risk_label = "Clinical Instability Detected"
            color = "#ff9f43"
            
            explanation_html = f"""
            <div style="background: rgba(255, 159, 67, 0.15); border: 2px solid {color}; 
                        border-radius: 10px; padding: 20px; margin-bottom: 15px;">
                <h4 style="color: {color}; margin-top: 0;">⚠️ Clinical Instability (Non-Sepsis)</h4>
                <p style="color: #b0b0b0;"><strong>ML Sepsis Risk:</strong> {current_risk * 100:.1f}% (below sepsis threshold)</p>
                <p style="color: #b0b0b0;"><strong>Clinical Note:</strong> 
                    Abnormal vitals detected. Investigate underlying cause. Do NOT automatically initiate sepsis protocols.
                </p>
            </div>
            """
            
        elif is_normal:
            # NORMAL PATIENT
            prediction_status = "normal"
            prediction_text = "No Current Evidence of Sepsis"
            confidence_display = f"{current_risk * 100:.1f}%"
            risk_label = "Low Risk (Normal)"
            color = "#4ade80"
            
            explanation_html = f"""
            <div style="background: rgba(74, 222, 128, 0.15); border: 2px solid {color}; 
                        border-radius: 10px; padding: 20px; margin-bottom: 15px;">
                <h4 style="color: {color}; margin-top: 0;">✓ Patient Status Normal</h4>
                <p style="color: #b0b0b0;"><strong>ML Sepsis Risk:</strong> {current_risk * 100:.1f}% — No current evidence of sepsis.</p>
                <p style="color: #b0b0b0;"><strong>Clinical Recommendation:</strong> 
                    Continue routine monitoring.
                </p>
            </div>
            """
            
        else:
            # MODERATE RISK
            prediction_status = "moderate_risk"
            prediction_text = "Moderate Sepsis Risk"
            confidence_display = f"{current_risk * 100:.1f}%"
            risk_label = "Moderate Risk (20-50%)"
            color = "#ffd700"
            
            explanation_html = f"""
            <div style="background: rgba(255, 215, 0, 0.15); border: 2px solid {color}; 
                        border-radius: 10px; padding: 20px; margin-bottom: 15px;">
                <h4 style="color: {color}; margin-top: 0;">⚠️ Moderate Sepsis Risk</h4>
                <p style="color: #b0b0b0;"><strong>ML Risk Score:</strong> {current_risk * 100:.1f}% — {risk_label}</p>
                <p style="color: #b0b0b0;"><strong>Clinical Recommendation:</strong> 
                    Enhanced monitoring recommended. Prepare for possible sepsis protocols.
                </p>
            </div>
            """
        
        explanation_html += generate_explanation(form_data, 1 if is_high_risk else 0, current_risk * 100)
        
        return render_template(
            'index.html',
            prediction_text=prediction_text,
            confidence=confidence_display,
            explanation=explanation_html,
            risk_level=risk_label,
            model_version="Optimized Phase 1",
            phase3_risk="",
            is_normal_state=(prediction_status == "normal"),
            prediction_status=prediction_status
        )
    
    except Exception as e:
        error_message = str(e)
        print(f"[ERROR] {error_message}")
        
        return render_template(
            'index.html',
            prediction_text="Prediction Error",
            confidence="0.00%",
            explanation=f"<div style='color: #ff6b6b;'>Error: {error_message}</div>",
            risk_level="Error",
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

