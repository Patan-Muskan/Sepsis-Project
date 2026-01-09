#!/usr/bin/env python3
"""
Test script to validate normal state detection and 6-hour prediction logic.
Tests both normal and abnormal patient cases.
"""

import requests
import json
from typing import Dict, Tuple

BASE_URL = "http://127.0.0.1:5000"

# Test Case 1: All Normal Values
NORMAL_PATIENT_DATA = {
    'Heart_Rate': '72',
    'Temperature': '37.0',
    'Systolic_BP': '120',
    'Mean_Arterial_Pressure': '90',
    'Diastolic_BP': '80',
    'Respiration_Rate': '16',
    'Oxygen_Saturation': '98',
    'BaseExcess': '0',
    'HCO3': '24',
    'FiO2': '21',
    'PaCO2': '40',
    'Creatinine': '1.0',
    'Glucose': '100',
    'Lactate': '1.5',
    'Magnesium': '2.2',
    'Phosphate': '3.5',
    'Bilirubin_direct': '0.2',
    'Bilirubin_total': '0.8',
    'Haemoglobin': '13.5',
    'WBC': '7.5',
    'Fibrinogen': '300',
    'Platelets': '200',
    'Age': '45'
}

# Test Case 2: Abnormal Values (High Risk)
ABNORMAL_PATIENT_DATA = {
    'Heart_Rate': '125',  # High - abnormal
    'Temperature': '39.2',  # High - abnormal
    'Systolic_BP': '95',  # Low - abnormal
    'Mean_Arterial_Pressure': '65',  # Low - abnormal
    'Diastolic_BP': '50',  # Low
    'Respiration_Rate': '28',  # High - abnormal
    'Oxygen_Saturation': '92',  # Low - abnormal
    'BaseExcess': '-5',  # Abnormal
    'HCO3': '18',  # Low - abnormal
    'FiO2': '40',  # Elevated
    'PaCO2': '32',  # Low - abnormal
    'Creatinine': '2.1',  # High - abnormal
    'Glucose': '280',  # High - abnormal
    'Lactate': '3.5',  # High - abnormal
    'Magnesium': '1.8',  # Low - abnormal
    'Phosphate': '5.2',  # High
    'Bilirubin_direct': '0.8',  # High
    'Bilirubin_total': '2.1',  # High
    'Haemoglobin': '10.2',  # Low
    'WBC': '18.5',  # High - abnormal
    'Fibrinogen': '250',  # Low
    'Platelets': '95',  # Low
    'Age': '62'
}


def test_case(name: str, data: Dict) -> None:
    """Test a prediction case and validate output."""
    print(f"\n{'='*70}")
    print(f"TEST CASE: {name}")
    print(f"{'='*70}")
    
    try:
        # Make prediction request
        response = requests.post(f"{BASE_URL}/predict", data=data, timeout=10)
        response.raise_for_status()
        
        html_content = response.text
        
        # Check for normal state indicators
        is_normal = "No current evidence of sepsis risk" in html_content
        print(f"\n✓ Normal State Detected: {is_normal}")
        
        # Check for 6-hour prediction presence
        has_6h_prediction = "IN 6 HOURS" in html_content
        print(f"✓ 6-Hour Prediction Card Present: {has_6h_prediction}")
        
        # Extract risk percentage if present
        if "risk-value-large" in html_content:
            # Simple extraction
            import re
            matches = re.findall(r'<div class="risk-value-large"[^>]*>([^<]+)</div>', html_content)
            if matches:
                print(f"✓ Risk Percentage: {matches[0]}")
        
        # Check for clinical explanation
        has_explanation = "Clinical Assessment" in html_content
        print(f"✓ Clinical Explanation Present: {has_explanation}")
        
        # Validation logic
        print(f"\n{'─'*70}")
        print("VALIDATION:")
        print(f"{'─'*70}")
        
        if name == "NORMAL PATIENT":
            if is_normal and not has_6h_prediction:
                print("✅ PASS: Normal state correctly detected, 6h card hidden")
            else:
                print("❌ FAIL: Normal state not properly handled")
                if not is_normal:
                    print("  - Missing 'No current evidence' message")
                if has_6h_prediction:
                    print("  - 6h prediction card should be hidden for normal patients")
        
        elif name == "ABNORMAL PATIENT":
            if not is_normal and has_6h_prediction:
                print("✅ PASS: Abnormal state recognized, 6h prediction shown")
            else:
                print("❌ FAIL: Abnormal state not properly handled")
                if is_normal:
                    print("  - Incorrectly classified as normal")
                if not has_6h_prediction:
                    print("  - 6h prediction card should be visible for abnormal patients")
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all test cases."""
    print("\n" + "="*70)
    print("SEPSIS EARLY DETECTION SYSTEM - NORMAL STATE TEST SUITE")
    print("="*70)
    print(f"\nTarget: {BASE_URL}")
    
    # Test normal patient
    test_case("NORMAL PATIENT", NORMAL_PATIENT_DATA)
    
    # Test abnormal patient
    test_case("ABNORMAL PATIENT", ABNORMAL_PATIENT_DATA)
    
    print(f"\n\n{'='*70}")
    print("TEST SUITE COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
