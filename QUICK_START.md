# Quick Start Guide - Early-Detection-Of-Sepsis System

## 🚀 Launch Application

```powershell
cd "c:\Users\muska\Downloads\Early-Detection-Of-Sepsis-master\Early-Detection-Of-Sepsis-master"
python app.py
```

Then open: **http://127.0.0.1:5000**

---

## 🧪 Test the System

### Scenario 1: Normal Patient (Automatic Detection)
1. Click **"Generate Random Values"** (1st time - should generate HIGH RISK case)
2. Click again (2nd time - should generate LOW RISK case)
3. Click **"Predict Sepsis Risk"**
4. **Expected**: 
   - Message: "No current evidence of sepsis risk"
   - Green theme
   - **No 6-hour prediction card visible**
   - **No timeline visible**

### Scenario 2: High-Risk Patient
1. Click **"Generate Random Values"** (1st time or next odd click)
2. Click **"Predict Sepsis Risk"**
3. **Expected**:
   - Risk percentage (usually 70-95%)
   - Label: "High Risk" or "Critical Risk" (red/orange)
   - **6-hour prediction card VISIBLE**
   - 6h risk showing escalating trajectory
   - **Timeline VISIBLE**
   - Clinical explanation with abnormal features

---

## 📋 Feature Checklist

✅ **Normal State Detection**
- Automatically detects all-normal patient vitals
- Returns "No current evidence of sepsis risk" message
- Hides 6-hour prediction card and timeline

✅ **6-Hour Advance Prediction**
- Calculates continuous probabilistic trajectory
- Shows escalating/stable/improving status
- Displays risk velocity (% change per 6 hours)

✅ **Input Validation**
- All 23 fields have clinical maximum constraints
- JavaScript capping prevents invalid values
- Type checking on form submission

✅ **Continuous Risk Model**
- No binary thresholds (not "yes/no" for sepsis)
- Smooth Gaussian curves from optimal ranges
- Blends model probability (60%) + vital deviations (40%)

✅ **Mandatory Label Mapping**
```
0-20%    → Low Risk (green)
21-50%   → Moderate Risk (yellow)
51-75%   → High Risk (orange)
76-100%  → Critical Risk (red)
```

✅ **Clinical Safety**
- Baseline rule: Healthy → cap future at 5%
- No false alarms for normal patients
- Vital instability checking
- Probability-label consistency

---

## 📊 Input Parameters (Copy-Paste Template)

**Manually enter values** (Normal Ranges):

**Vitals**:
- Heart Rate: **72** (60-100)
- Temperature: **37.0** (36.5-37.5)
- Systolic BP: **120** (90-140)
- Mean Arterial Pressure: **90** (70-100)
- Diastolic BP: **80** (60-90)
- Respiration Rate: **16** (12-20)
- Oxygen Saturation: **98** (95-100)

**Labs**:
- Base Excess: **0** (-2 to +2)
- HCO3: **24** (22-26)
- FiO2: **21** (21 room air)
- PaCO2: **40** (35-45)
- Creatinine: **1.0** (0.6-1.2)
- Glucose: **100** (70-100)
- Lactate: **1.5** (0.5-2.0)
- Magnesium: **2.2** (1.7-2.2)
- Phosphate: **3.5** (2.5-4.5)
- Bilirubin (Direct): **0.2** (0-0.3)
- Bilirubin (Total): **0.8** (0.1-1.2)
- Hemoglobin: **13.5** (12-17)
- WBC: **7.5** (4.5-11.0)
- Fibrinogen: **300** (200-400)
- Platelets: **200** (150-400)

**Demographics**:
- Age: **45**

---

## 🎯 System Behavior

### Request Flow
```
User Input → Validation → Model Prediction → 
Normal Check? 
  ├─ YES → "No evidence" + is_normal_state=True → Hide 6h card
  └─ NO → Continuous trajectory → Show 6h prediction
         → Return full results
```

### Response Fields
- `prediction_text`: Risk label + percentage (e.g., "Critical Risk (92.3%)")
- `confidence`: Probability as percentage
- `explanation`: Clinical details in HTML
- `risk_level`: Risk category name
- `phase3_risk`: 6-hour forecast (0.0-1.0) or null
- `is_normal_state`: True/False flag for template

### Template Behavior
- **If `is_normal_state=True`**:
  - Hide 6-hour card with `display: none`
  - Hide timeline with `display: none`
  - Show "No current evidence" message
  - Green theme applied

- **If `is_normal_state=False`**:
  - Show all prediction elements
  - Display 6-hour risk card
  - Show timeline visualization
  - Apply appropriate color theme

---

## 🔍 Debugging

### Check Flask Logs
```
[INFO] Using Random Forest with linear probability scaling
[INFO] Phase 3 LSTM model loaded - 6-hour advance prediction available
 * Running on http://127.0.0.1:5000
```

### Check Browser Console (F12)
- JavaScript errors will show in Console tab
- Network tab shows POST request to `/predict`
- Response shows HTML with prediction results

### Common Issues

**Issue**: "No current evidence" not showing
- **Cause**: Form has invalid values
- **Fix**: Use "Generate Random Values" button to fill valid data

**Issue**: 6-hour card still visible for normal case
- **Cause**: Template not checking `is_normal_state` flag
- **Fix**: Verify lines 710, 715, 725 in index.html have conditional display

**Issue**: Model prediction always same value
- **Cause**: Model not loaded correctly
- **Fix**: Check Flask startup logs for model loading messages

**Issue**: Python errors on prediction
- **Cause**: Missing dependencies
- **Fix**: Run `pip install -r requirements.txt`

---

## 📁 Key Files Modified

| File | What Changed | Why |
|------|--------------|-----|
| `app.py` (Lines 553-650) | Added normal state detection in `/predict` route | To skip 6h prediction for normal patients |
| `app.py` (Lines 532-550) | Added `get_sepsis_risk_label()` function | Enforce mandatory label-probability mapping |
| `templates/index.html` (Lines 710, 715, 725) | Added `{% if is_normal_state %}style="display: none;"{% endif %}` | Hide 6h card & timeline for normal state |

---

## 🎨 Visual Indicators

| Element | Normal Patient | High-Risk Patient |
|---------|---|---|
| Current Risk Card | Hidden* | Visible, Red/Orange |
| 6-Hour Card | Hidden | Visible, Red/Orange |
| Timeline | Hidden | Visible with 0h→6h→24h |
| Message | "No evidence" | Risk label + % |
| Theme | Green | Red/Orange |

*Normal card hidden via `display: none` CSS

---

## 📊 Example: Normal Patient Response

```html
<div class="risk-card current-risk" style="background: rgba(81, 207, 102, 0.1);">
    <div class="card-header">
        <i class="fas fa-heart-pulse"></i>
        <span class="time-label">NOW</span>
    </div>
    <div class="risk-value-large">No current evidence of sepsis risk</div>
    <div class="risk-label">Not Prone to Sepsis</div>
    <div class="risk-status green">✓ NORMAL</div>
</div>

<!-- Next elements are HIDDEN -->
<div class="prediction-arrow" style="display: none;"> ... </div>
<div class="risk-card future-risk" style="display: none;"> ... </div>
<div class="timeline-section" style="display: none;"> ... </div>
```

---

## ✅ Validation Steps

1. **Start Flask**
   - [ ] No errors in startup logs
   - [ ] "Phase 3 LSTM model loaded" message appears

2. **Open http://127.0.0.1:5000**
   - [ ] Form displays with all 23 fields
   - [ ] "Generate Random Values" button works
   - [ ] Values alternate between high/low risk

3. **Test Normal State**
   - [ ] Generate values twice (first HIGH, second LOW)
   - [ ] Click predict on LOW case
   - [ ] See "No current evidence" message
   - [ ] 6-hour card is HIDDEN
   - [ ] Timeline is HIDDEN

4. **Test High-Risk State**
   - [ ] Generate values (odd click = HIGH)
   - [ ] Click predict
   - [ ] See risk percentage with label
   - [ ] 6-hour card is VISIBLE
   - [ ] Timeline shows 0h→6h→24h

---

## 🎓 Clinical Interpretation Guide

### Low Risk (0-20%, Green)
- **Meaning**: Minimal current sepsis risk
- **Action**: Continue standard monitoring
- **Example**: Normal vitals, normal labs, low model score

### Moderate Risk (21-50%, Yellow)
- **Meaning**: Early warning signals present
- **Action**: Increase monitoring frequency, consider prophylaxis
- **Example**: One abnormal vital, some elevated labs

### High Risk (51-75%, Orange)
- **Meaning**: Significant sepsis risk, early intervention indicated
- **Action**: Consider empiric antibiotics, blood cultures, aggressive fluid management
- **Example**: Multiple abnormal vitals, elevated lactate/WBC

### Critical Risk (76-100%, Red)
- **Meaning**: Severe sepsis risk, immediate action required
- **Action**: ICU monitoring, broad-spectrum antibiotics, aggressive resuscitation
- **Example**: Shock indices, severe organ dysfunction, severe abnormalities

---

## 📞 Support Resources

**Files Included**:
- `NORMAL_STATE_IMPLEMENTATION.md` - Technical details
- `SYSTEM_COMPLETE_SUMMARY.md` - Full architecture guide
- `app.py` - Backend source code with comments
- `templates/index.html` - Frontend HTML/JS
- `static/style.css` - Styling

**For More Info**:
- Review docstrings in `app.py`
- Check HTML comments in `index.html`
- Read comprehensive summaries in markdown files

---

**System Ready**: ✅ All features implemented and tested
**Status**: Production deployment ready
**Last Update**: 2024

