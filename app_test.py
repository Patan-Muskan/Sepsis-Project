#!/usr/bin/env python
# coding: utf-8
"""
Minimal test version to identify blocking issues
"""

from flask import Flask, request, render_template

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Static test response - no ML model"""
    # Return static test values
    prediction_text = "Test Mode - Low Risk (25.0%)"
    confidence = "25.00%"
    risk_label = "Low Risk"
    phase3_risk = 0.30  # 30% future risk for testing
    
    explanation_html = """
    <div style="background: rgba(81, 207, 102, 0.1); border: 2px solid rgba(81, 207, 102, 0.3); 
                border-radius: 10px; padding: 20px; margin-bottom: 15px;">
        <h5 style="color: #4ade80; margin-top: 0;">Test Mode Active</h5>
        <p style="color: #b0b0b0;">This is a static test response to verify the UI is working.</p>
    </div>
    """
    
    return render_template(
        'index.html',
        prediction_text=prediction_text,
        confidence=confidence,
        explanation=explanation_html,
        risk_level=risk_label,
        model_version="Test Mode",
        phase3_risk=phase3_risk,
        is_normal_state=False
    )

if __name__ == '__main__':
    print("[TEST] Starting minimal Flask server...")
    app.run(debug=False, port=5000)
