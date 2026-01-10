#!/usr/bin/env python
# coding: utf-8
"""
Simplified Sepsis Risk Prediction Application
Works without complex ML dependencies
"""

from flask import Flask, request, render_template
import json

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')

# Clinical reference ranges
CLINICAL_RANGES = {
    'HR': {'optimal': 70, 'min': 60, 'max': 100, 'unit': 'bpm'},
    'Temp': {'optimal': 37.0, 'min': 36.5, 'max': 37.5, 'unit': '°C'},
    'SBP': {'optimal': 110, 'min': 90, 'max': 130, 'unit': 'mmHg'},
    'MAP': {'optimal': 85, 'min': 70, 'max': 100, 'unit': 'mmHg'},
    'DBP': {'optimal': 70, 'min': 60, 'max': 85, 'unit': 'mmHg'},
    'Resp': {'optimal': 16, 'min': 12, 'max': 20, 'unit': 'breaths/min'},
    'O2Sat': {'optimal': 97, 'min': 95, 'max': 100, 'unit': '%'},
    'Glucose': {'optimal': 85, 'min': 70, 'max': 100, 'unit': 'mg/dL'},
    'Lactate': {'optimal': 1.2, 'min': 0.5, 'max': 2.0, 'unit': 'mmol/L'},
    'WBC': {'optimal': 7, 'min': 4.5, 'max': 11, 'unit': 'K/uL'},
    'Creatinine': {'optimal': 1.0, 'min': 0.6, 'max': 1.2, 'unit': 'mg/dL'},
    'HCO3': {'optimal': 24, 'min': 22, 'max': 26, 'unit': 'mEq/L'},
}

def calculate_deviation_risk(value, param_name):
    """Calculate risk score (0-1) based on deviation from normal range."""
    try:
        val = float(value)
    except (ValueError, TypeError):
        return 0.0
    
    if param_name not in CLINICAL_RANGES:
        return 0.0
    
    ranges = CLINICAL_RANGES[param_name]
    opt = ranges['optimal']
    norm_min = ranges['min']
    norm_max = ranges['max']
    
    # Within normal range - minimal risk
    if norm_min <= val <= norm_max:
        center_dist = abs(val - opt)
        norm_range = (norm_max - norm_min) / 2
        return min(0.2, (center_dist / norm_range) * 0.2)
    
    # Below normal
    elif val < norm_min:
        deviation = norm_min - val
        max_deviation = norm_min - (norm_min * 0.5)  # Allow 50% deviation
        return min(1.0, 0.2 + (deviation / max_deviation) * 0.8)
    
    # Above normal
    else:
        deviation = val - norm_max
        max_deviation = (norm_max * 0.5)  # Allow 50% deviation
        return min(1.0, 0.2 + (deviation / max_deviation) * 0.8)


def calculate_sepsis_risk(form_data):
    """
    Calculate sepsis risk using SIRS criteria + organ dysfunction + sepsis indicators.
    Optimized for accurate clinical assessment.
    
    Returns: (risk_score, abnormal_params, clinical_status, color, recommendation)
    """
    
    # Track SIRS criteria
    sirs_count = 0
    abnormal_params = []
    critical_organ_dysfunction = []
    abnormality_count = 0
    
    # ===== TEMPERATURE CRITERION =====
    temp = form_data.get('Temp', '')
    if temp:
        try:
            temp_val = float(temp)
            if temp_val > 38.0 or temp_val < 36.0:
                sirs_count += 1
            if temp_val > 38.0 or temp_val < 36.0:
                abnormal_params.append({
                    'param': 'Temperature',
                    'value': temp_val,
                    'normal_range': '36.5-37.5',
                    'unit': '°C',
                    'severity': 'CRITICAL' if (temp_val > 40 or temp_val < 34) else 'HIGH'
                })
                abnormality_count += 1
                if temp_val > 40 or temp_val < 34:
                    critical_organ_dysfunction.append(('Severe Fever/Hypothermia', temp_val, 'Extreme temp range'))
        except ValueError:
            pass
    
    # ===== HEART RATE CRITERION =====
    hr = form_data.get('HR', '')
    if hr:
        try:
            hr_val = float(hr)
            if hr_val > 90 or hr_val < 60:
                sirs_count += 1
            if hr_val > 100 or hr_val < 50:
                abnormal_params.append({
                    'param': 'Heart Rate',
                    'value': hr_val,
                    'normal_range': '60-100',
                    'unit': 'bpm',
                    'severity': 'CRITICAL' if (hr_val > 130 or hr_val < 40) else 'HIGH'
                })
                abnormality_count += 1
                if hr_val > 130 or hr_val < 40:
                    critical_organ_dysfunction.append(('Severe Tachycardia/Bradycardia', hr_val, 'Cardiac instability'))
        except ValueError:
            pass
    
    # ===== RESPIRATORY RATE CRITERION =====
    resp = form_data.get('Resp', '')
    if resp:
        try:
            resp_val = float(resp)
            if resp_val > 20:
                sirs_count += 1
            if resp_val > 22:
                abnormal_params.append({
                    'param': 'Respiration Rate',
                    'value': resp_val,
                    'normal_range': '12-20',
                    'unit': 'breaths/min',
                    'severity': 'CRITICAL' if resp_val > 30 else 'HIGH'
                })
                abnormality_count += 1
                if resp_val > 30:
                    critical_organ_dysfunction.append(('Severe Tachypnea', resp_val, 'Respiratory distress'))
        except ValueError:
            pass
    
    # ===== WBC CRITERION =====
    wbc = form_data.get('WBC', '')
    if wbc:
        try:
            wbc_val = float(wbc)
            if wbc_val > 12 or wbc_val < 4:
                sirs_count += 1
            if wbc_val > 15 or wbc_val < 3:
                abnormal_params.append({
                    'param': 'WBC Count',
                    'value': wbc_val,
                    'normal_range': '4.5-11',
                    'unit': 'K/uL',
                    'severity': 'CRITICAL' if (wbc_val > 20 or wbc_val < 2) else 'HIGH'
                })
                abnormality_count += 1
        except ValueError:
            pass
    
    # ===== OXYGEN SATURATION =====
    o2 = form_data.get('O2Sat', '')
    if o2:
        try:
            o2_val = float(o2)
            if o2_val < 93:
                critical_organ_dysfunction.append(('Hypoxemia', o2_val, 'O2Sat < 93% = respiratory/tissue dysfunction'))
                abnormal_params.append({
                    'param': 'O₂ Saturation',
                    'value': o2_val,
                    'normal_range': '95-100',
                    'unit': '%',
                    'severity': 'CRITICAL' if o2_val < 88 else 'HIGH'
                })
                abnormality_count += 1
        except ValueError:
            pass
    
    # ===== SYSTOLIC BLOOD PRESSURE =====
    sbp = form_data.get('SBP', '')
    if sbp:
        try:
            sbp_val = float(sbp)
            if sbp_val < 90:
                critical_organ_dysfunction.append(('Hypotension', sbp_val, 'SBP < 90 = organ hypoperfusion'))
                abnormal_params.append({
                    'param': 'Systolic BP',
                    'value': sbp_val,
                    'normal_range': '90-140',
                    'unit': 'mmHg',
                    'severity': 'CRITICAL'
                })
                abnormality_count += 1
        except ValueError:
            pass
    
    # ===== LACTATE =====
    lactate = form_data.get('Lactate', '')
    if lactate:
        try:
            lac_val = float(lactate)
            if lac_val > 2.0:
                critical_organ_dysfunction.append(('Hyperlactatemia', lac_val, 'Lactate > 2 = tissue dysfunction'))
                severity = 'CRITICAL' if lac_val > 4 else 'HIGH'
                abnormal_params.append({
                    'param': 'Lactate',
                    'value': lac_val,
                    'normal_range': '0.5-2.0',
                    'unit': 'mmol/L',
                    'severity': severity
                })
                abnormality_count += 1
        except ValueError:
            pass
    
    # ===== CREATININE =====
    creatinine = form_data.get('Creatinine', '')
    if creatinine:
        try:
            crea_val = float(creatinine)
            if crea_val > 1.5:
                critical_organ_dysfunction.append(('Acute kidney dysfunction', crea_val, 'Creatinine > 1.5 = renal failure'))
                severity = 'CRITICAL' if crea_val > 3 else 'HIGH'
                abnormal_params.append({
                    'param': 'Creatinine',
                    'value': crea_val,
                    'normal_range': '0.6-1.2',
                    'unit': 'mg/dL',
                    'severity': severity
                })
                abnormality_count += 1
        except ValueError:
            pass
    
    # ===== CALCULATE FINAL RISK SCORE =====
    organ_dysfunction_count = len(critical_organ_dysfunction)
    
    # Weighted risk calculation
    if organ_dysfunction_count >= 3:
        sepsis_risk = 0.95  # Multiple organ dysfunction = almost certain sepsis
    elif organ_dysfunction_count >= 2:
        sepsis_risk = 0.85  # Multiple organ dysfunction
    elif organ_dysfunction_count >= 1 and sirs_count >= 2:
        sepsis_risk = 0.75  # Organ dysfunction + SIRS
    elif organ_dysfunction_count >= 1:
        sepsis_risk = 0.65  # Any organ dysfunction alone
    elif sirs_count >= 3 and abnormality_count >= 4:
        sepsis_risk = 0.60  # Strong SIRS + many abnormalities
    elif sirs_count >= 3:
        sepsis_risk = 0.50  # Strong SIRS
    elif sirs_count == 2 and abnormality_count >= 3:
        sepsis_risk = 0.40  # SIRS + multiple abnormalities
    elif sirs_count >= 2:
        sepsis_risk = 0.25  # Mild SIRS
    else:
        sepsis_risk = 0.05  # Essentially normal
    
    # ===== DETERMINE CLINICAL STATUS =====
    
    if organ_dysfunction_count >= 3:
        status = "SEPTIC SHOCK - CRITICAL"
        color = "#ff0000"
        recommendation = "🔴 CRITICAL: Multiple organ failure. Immediate ICU, vasopressors, aggressive resuscitation."
        clinical_state = "critical_shock"
    
    elif organ_dysfunction_count >= 2:
        status = "SEPTIC SHOCK / SEVERE SEPSIS"
        color = "#ff0000"
        recommendation = "🔴 CRITICAL: Multiple organ dysfunction. Activate sepsis protocol immediately. ICU required."
        clinical_state = "critical_sepsis"
    
    elif organ_dysfunction_count == 1 and sirs_count >= 2:
        status = "SEPSIS SUSPECTED"
        color = "#ff4444"
        recommendation = "🟠 HIGH PRIORITY: Organ dysfunction detected. Blood cultures, antibiotics, IV fluids, close monitoring."
        clinical_state = "suspected_sepsis"
    
    elif organ_dysfunction_count == 1:
        status = "ORGAN DYSFUNCTION - MONITOR"
        color = "#ff6b00"
        recommendation = "🟠 URGENT: Single organ dysfunction. Investigate cause. Enhanced monitoring required."
        clinical_state = "organ_dysfunction"
    
    elif sirs_count >= 3 and abnormality_count >= 4:
        status = "SIGNIFICANT CLINICAL INSTABILITY"
        color = "#ff9f43"
        recommendation = "🟡 HIGH RISK: Multiple vital sign abnormalities. Sepsis workup recommended. Frequent re-assessment."
        clinical_state = "high_risk"
    
    elif sirs_count >= 3:
        status = "MODERATE-HIGH RISK - SEPSIS POSSIBLE"
        color = "#ffb800"
        recommendation = "🟡 MODERATE RISK: Strong inflammatory response. Monitor closely. Consider sepsis protocol."
        clinical_state = "moderate_high_risk"
    
    elif sirs_count >= 2 and abnormality_count >= 3:
        status = "MODERATE RISK - OBSERVE"
        color = "#facc15"
        recommendation = "🟡 MODERATE RISK: Systemic inflammation detected. Close monitoring and investigation recommended."
        clinical_state = "moderate_risk"
    
    elif sirs_count >= 2 or abnormality_count >= 2:
        status = "LOW-MODERATE RISK"
        color = "#ffd700"
        recommendation = "🟡 LOW RISK: Minor abnormalities detected. Continue monitoring. Reassess as needed."
        clinical_state = "low_risk"
    
    else:
        status = "Normal - No Evidence of Sepsis"
        color = "#4ade80"
        recommendation = "🟢 NORMAL: Vital signs stable and within normal limits. Continue routine monitoring."
        clinical_state = "normal"
    
    return sepsis_risk, abnormal_params, status, color, recommendation


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    try:
        form_data = request.form.to_dict()
        
        # Calculate risk
        risk_score, abnormal_params, status, color, recommendation = calculate_sepsis_risk(form_data)
        
        # Format output
        confidence = f"{risk_score * 100:.1f}%"
        
        # Build explanation HTML
        explanation_html = f"""
        <div style="background: rgba({hex_to_rgb(color)}, 0.15); border: 2px solid {color}; 
                    border-radius: 10px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: {color}; margin-top: 0;">
                {'⚠️' if risk_score >= 0.5 else '✓'} {status}
            </h4>
            <p style="color: #b0b0b0;"><strong>Risk Score:</strong> {risk_score * 100:.1f}%</p>
            <p style="color: #b0b0b0;"><strong>Recommendation:</strong> {recommendation}</p>
        </div>
        """
        
        # Add abnormal values if present
        if abnormal_params:
            explanation_html += """
            <div style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.2); 
                        border-radius: 10px; padding: 15px; margin-bottom: 15px;">
                <h5 style="color: #ffd700;">⚠️ Abnormal Clinical Values</h5>
                <ul style="color: #b0b0b0; margin-left: 20px;">
            """
            for item in abnormal_params:
                explanation_html += f"""
                <li style="margin-bottom: 8px;">
                    <strong>{item['param']}</strong>: {item['value']:.2f} {item['unit']}
                    <span style="color: #999; font-size: 0.9em;">(Normal: {item['normal_range']} {item['unit']})</span>
                </li>
                """
            explanation_html += "</ul></div>"
        
        is_normal = risk_score < 0.25 and len(abnormal_params) == 0
        
        return render_template(
            'index.html',
            prediction_text=status,
            confidence=confidence,
            explanation=explanation_html,
            risk_level=status,
            model_version="Optimized Clinical Assessment",
            phase3_risk="",
            is_normal_state=is_normal,
            prediction_status="success"
        )
    
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] {error_msg}")
        
        return render_template(
            'index.html',
            prediction_text="Prediction Error",
            confidence="0.00%",
            explanation=f"<div style='color: #ff6b6b;'>Error: {error_msg}</div>",
            risk_level="Error",
            model_version="Error",
            phase3_risk="",
            is_normal_state=True,
            prediction_status="error"
        )


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple string."""
    hex_color = hex_color.lstrip('#')
    return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SEPSIS RISK PREDICTION SYSTEM - OPTIMIZED VERSION")
    print("="*70)
    print("\n✓ Model loaded and ready")
    print("✓ Server starting on http://127.0.0.1:5000")
    print("✓ Open your browser and navigate to the URL above\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
