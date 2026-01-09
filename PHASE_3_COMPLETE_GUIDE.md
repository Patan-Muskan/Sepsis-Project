# Phase 3 - LSTM Time-Series Sepsis Prediction - Complete Guide

## Overview

You've now entered **Phase 3** of the sepsis detection system! This phase implements a Bidirectional LSTM with Attention mechanism for temporal sepsis prediction.

## What is Phase 3?

### The Problem It Solves

**Phase 1-2** (Static/Trend Features):
```
Current Patient Status → "Patient is septic NOW"
Use Case: Point-of-care confirmation
⚠️ Limitation: Cannot predict in advance
```

**Phase 3** (LSTM Time-Series):
```
12 Hours of Patient History → "Patient will develop sepsis in 6 hours"
Use Case: Early warning system
✓ Advantage: Proactive interventions possible
```

### Key Innovation: Temporal Modeling

Instead of looking at a single snapshot, Phase 3 examines the **trajectory**:

```
Phase 1-2: HR=120, Temp=38.5, RR=22 → Sepsis Risk: 39%

Phase 3: 
  Hour 0:   HR=80,  Temp=37.0, RR=14  }
  Hour 1:   HR=85,  Temp=37.2, RR=15  }
  Hour 2:   HR=95,  Temp=37.8, RR=16  } ← LSTM analyzes trajectory
  ...                                 }
  Hour 12: HR=120, Temp=38.5, RR=22  }
  
  → "Deteriorating trend detected"
  → Predict 6 hours ahead: Sepsis Risk: 75%
```

## Architecture Deep Dive

### The LSTM (Long Short-Term Memory) Layer

**How LSTM Works:**

1. **Input Gate**: "What new information matters?"
2. **Forget Gate**: "What old information should I discard?"
3. **Cell State**: "What's the running memory?"
4. **Output Gate**: "What should I output?"

```python
# Visualization of one LSTM cell:
    
    previous output   new input
         |               |
         v               v
    ┌─────────────────────────┐
    │  Forget Gate (removes)  │
    │  Input Gate (adds)      │ ← Learning what matters
    │  Output Gate (outputs)  │
    └─────────────────────────┘
         |               |
         v               v
    cell state      current output
```

### Bidirectional Processing

```
Standard LSTM:  → → → (processes left to right only)
                "Future context missing"

Bidirectional:  ← ← ← (backward)
                → → → (forward)
                "Sees pattern from both directions"
```

**Benefit**: Detects patterns that require looking at both past and future context within the 12-hour window.

### Multi-Head Attention

Learns which timesteps are most important:

```
Hour 0-6:  Normal vitals              (attention: low)
Hour 6-9:  Gradual deterioration      (attention: medium)
Hour 9-12: Rapid tachycardia + fever  (attention: HIGH ⚠️)

The attention mechanism learns that hours 9-12 matter most
for predicting sepsis development.
```

## Model Specifications

```
INPUT LAYER
↓
Bidirectional LSTM (64 units)
  - Processes sequences forward & backward
  - Parameters: 47,104
↓
Multi-Head Attention (4 heads)
  - Learns importance of each timestep
  - Parameters: 33,088
↓
Layer Normalization
  - Stabilizes training
  - Parameters: 256
↓
Bidirectional LSTM (32 units)
  - Second-level pattern extraction
  - Parameters: 41,216
↓
Dense Layer (64 units, ReLU)
  - Feature synthesis
  - Parameters: 4,160
↓
Dropout (0.3)
  - Prevents overfitting
↓
Dense Layer (32 units, ReLU)
  - Feature refinement
  - Parameters: 2,080
↓
Dropout (0.2)
↓
Output Layer (1 unit, Sigmoid)
  - Binary sepsis/no-sepsis
  - Parameters: 33
↓
PROBABILITY (0-1)

Total Parameters: 127,937
```

## Data Processing

### Sequence Creation

The raw time-series data is transformed into sequences:

```
Raw Data (38,809 timesteps):
  [f1_t0, f2_t0, ..., f27_t0]
  [f1_t1, f2_t1, ..., f27_t1]
  ...
  [f1_t38808, f2_t38808, ..., f27_t38808]

↓

Sequences (38,792 sequences):
  Sequence 1: [timestep 0-11]  → Label: sepsis_at_hour_17?
  Sequence 2: [timestep 1-12]  → Label: sepsis_at_hour_18?
  Sequence 3: [timestep 2-13]  → Label: sepsis_at_hour_19?
  ...
  
Shape: (38792, 12, 27)
        samples, hours, features
```

### Train/Test Split

```
Dataset
  ├─ Training (31,033 sequences, 80%)
  │  └─ Used to learn LSTM weights
  │
  └─ Testing (7,759 sequences, 20%)
     └─ Unseen data for evaluation
```

### Class Imbalance Handling

```
Class Distribution:
  Non-Sepsis: 37,945 samples (97.77%)
  Sepsis:        864 samples (2.23%)

Problem: Model might just predict "no sepsis" for everything

Solution: Class Weights
  Weight_non_sepsis = 1 (normal)
  Weight_sepsis = 10 (emphasized)
  
Result: Sepsis cases given 10x importance during training
```

## Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Sequence Length** | 12 hours | Clinical window for trend observation |
| **Forecast Horizon** | 6 hours | Early warning for intervention |
| **Batch Size** | 32 | Balance between speed and stability |
| **Epochs** | 50 | With early stopping to prevent overfitting |
| **Learning Rate** | 0.001 | Stable convergence |
| **Optimizer** | Adam | Adaptive learning rates |
| **Loss** | Binary Crossentropy | Standard for binary classification |
| **Validation Split** | 20% | Monitor during training |
| **Class Weight** | {0: 1, 1: 10} | Address imbalance |

## Expected Performance

Based on Phase 1 & 2 trends:

```
Metric            Phase 1        Phase 2        Phase 3*
─────────────────────────────────────────────────────────
Accuracy          97.71%         97.77%         ~98%+
Precision         ~95%           ~96%           ~97%+
Recall (Sepsis)   100%           76%            ~85%+
F1-Score          ~97%           ~85%           ~90%+
ROC-AUC           0.9862         0.7044         ~0.92+

*Estimates based on typical LSTM improvements for temporal data
```

### Key Advantage

**Early Prediction Window**: Phase 3 predicts 6 hours in advance!

```
Phase 1-2 Timeline:
  T=0:    Patient admitted
  T=6:    Symptoms appear
  T=8:    Diagnosed as septic (TOO LATE)
  T=12:   Critical condition

Phase 3 Timeline:
  T=0:    Patient admitted
  T=6:    LSTM predicts sepsis in 6 hours ⚠️
  T=6:    Early interventions start
  T=12:   Patient stable (PREVENTED)
```

## Training Process

### Step-by-Step

```
[1/6] Load Data
      └─ 38,809 samples, 27 features
      └─ Identify sepsis cases (2.23%)

[2/6] Create Sequences
      └─ 38,792 sequences (12, 27) shape
      └─ Target: sepsis in next 6 hours?

[3/6] Scale & Split
      └─ StandardScaler normalization
      └─ 80% train, 20% test

[4/6] Build LSTM Model
      └─ 127,937 parameters
      └─ Bidirectional + Attention

[5/6] Train Model
      └─ 50 epochs (with early stopping)
      └─ Learns temporal patterns
      └─ ~10-20 minutes on CPU

[6/6] Evaluate & Save
      └─ Test set performance metrics
      └─ Save model, scaler, history
      └─ Generate visualizations
```

### Training Output Files

After completion, you'll have:

```
model_phase3_lstm.h5          ← LSTM weights and architecture
scaler_phase3.pkl             ← Feature normalizer
history_phase3.pkl            ← Training curves data
metrics_phase3.pkl            ← Performance metrics
training_history_phase3.png   ← Loss/Accuracy plots
confusion_matrix_phase3.png   ← Prediction accuracy heatmap
roc_curve_phase3.png          ← ROC-AUC visualization
phase3_training.log           ← Complete training log
```

## Comparison: All Three Phases

### Phase 1: Simple but Powerful

**Model**: Neural Network (MLPClassifier)
**Input**: 27 static features at one timepoint
**Training**: ~10 seconds
**Features**: High accuracy (97.71%), simple interpretation
**Limitation**: No temporal awareness

```python
# Usage
input: [HR=120, Temp=38.5, RR=22, ...]  # Single timepoint
       └─ phase1_model.predict()
output: Sepsis Probability = 0.39 (39%)
```

### Phase 2: Adds Trends

**Model**: Random Forest with trend features
**Input**: 27 static + 16 trend features (43 total)
**Training**: ~30 seconds
**Features**: Captures deterioration over 1-2 hours
**Limitation**: Limited temporal context, still reactive

```python
# Usage
input: [
  HR=120,            # Current value
  HR_trend_1h=+15,   # Change over past hour
  Temp=38.5,
  Temp_trend_1h=+0.8,
  ...
]  # Current state + recent trends
   └─ phase2_model.predict()
output: Sepsis Probability = 0.40 (40%)
```

### Phase 3: Temporal Intelligence

**Model**: Bidirectional LSTM with Attention
**Input**: 12-hour sequences (12 timesteps × 27 features)
**Training**: ~15 minutes
**Features**: Learns complex temporal patterns, predicts 6 hours ahead
**Advantage**: PROACTIVE - early warning system

```python
# Usage
input: [
  [HR_t0=85, Temp_t0=37.0, ...],  # 12 timesteps
  [HR_t1=87, Temp_t1=37.2, ...],  #
  ...                             #
  [HR_t12=120, Temp_t12=38.5, ...] # Current
]  # 12 hours of history
   └─ phase3_model.predict()
output: 6-Hour Ahead Sepsis Probability = 0.75 (75%)
        ↑ Much higher! Deterioration trend detected
```

## Integration with Flask

After Phase 3 training completes, integrate it:

```python
# app.py modifications

from phase3_utils import Phase3LSTMPredictor

# Initialize on app startup
phase3_model = Phase3LSTMPredictor(
    'model_phase3_lstm.h5',
    'scaler_phase3.pkl'
)

# In prediction route
@app.route('/predict', methods=['POST'])
def predict():
    # ...existing Phase 1-2 code...
    
    # Phase 3 prediction if available
    if phase3_model.ready:
        phase3_prob = phase3_model.predict(patient_history)
        result['phase3_6h_risk'] = phase3_prob
```

## Real-World Impact

### Example Case

**Patient admitted with suspected infection:**

**Phase 1 (Now):**
- Current vitals appear borderline
- Probability: 38% sepsis risk
- Doctor: "Monitor closely"

**Phase 2 (Now + trends):**
- Heart rate trending up (+15 bpm/hour)
- Temperature trending up (+0.8°C/hour)
- Probability: 40% sepsis risk  
- Doctor: "Antibiotic therapy started"

**Phase 3 (Now + 6-hour warning):**
- Historical deterioration pattern recognized
- Attention mechanism flags: "Hours 9-12 show critical indicators"
- Probability: 75% sepsis risk in 6 hours
- Doctor: "Aggressive ICU support initiated NOW"

### Outcome

```
Without Phase 3: Patient deteriorates to septic shock
With Phase 3:    Early intervention prevents crisis
```

## When Training Completes

1. **Check output files exist**:
   ```bash
   ls -la model_phase3_lstm.h5
   ls -la metrics_phase3.pkl
   ```

2. **Review metrics**:
   ```python
   import pickle
   metrics = pickle.load(open('metrics_phase3.pkl', 'rb'))
   print(f"Accuracy: {metrics['accuracy']:.4f}")
   print(f"ROC-AUC: {metrics['roc_auc']:.4f}")
   ```

3. **View visualizations**:
   - `training_history_phase3.png`: Loss curves
   - `confusion_matrix_phase3.png`: Prediction accuracy
   - `roc_curve_phase3.png`: ROC curve

4. **Deploy Phase 3 in Flask**:
   - Update `app.py` to load Phase 3 model
   - Add 6-hour risk prediction to UI
   - Display historical sequence graphs

## Next Steps After Phase 3

1. **Ensemble**: Combine Phase 1, 2, 3 predictions
2. **Real-time Deployment**: Add streaming predictions
3. **Monitoring**: Track model performance in production
4. **Continuous Learning**: Retrain as new data arrives
5. **Mobile App**: Extend to mobile platforms

---

**Status**: Phase 3 training in progress... ⏳

Check back in ~15 minutes for results!
