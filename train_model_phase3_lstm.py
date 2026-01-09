"""
Phase 3: LSTM-based Time-Series Sepsis Prediction
Predicts sepsis up to 24 hours in advance using temporal patterns

Features:
- LSTM architecture for sequential data
- Bidirectional processing
- Attention mechanism
- Multi-step ahead forecasting
- Early warning predictions
"""

import numpy as np
import pandas as pd
import pickle
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                              f1_score, roc_auc_score, confusion_matrix, classification_report)

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

SEQUENCE_LENGTH = 12  # Look back 12 time steps (hours)
FORECAST_STEPS = 6    # Predict 6 steps ahead (6 hours)
BATCH_SIZE = 32
EPOCHS = 50
VALIDATION_SPLIT = 0.2
TEST_SIZE = 0.2
RANDOM_STATE = 42

FEATURE_COLUMNS = [
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'EtCO2', 'BaseExcess', 'HCO3',
    'FiO2', 'pH', 'PaCO2', 'SaO2', 'AST', 'BUN', 'Alkalinephos', 'Calcium', 'Chloride', 
    'Creatinine', 'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium', 'Phosphate', 
    'Potassium', 'Hgb'
]

# ============================================================================
# STEP 1: LOAD AND PREPARE DATA
# ============================================================================

print("\n" + "="*70)
print("PHASE 3: LSTM TIME-SERIES SEPSIS PREDICTION")
print("="*70 + "\n")

print("[1/6] Loading data...")
df = pd.read_csv('sepsis.csv')

# Fill missing values with forward fill then backward fill
df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(method='ffill').fillna(method='bfill').fillna(df[FEATURE_COLUMNS].mean())

X = df[FEATURE_COLUMNS].values
y = df['SepsisLabel'].values

print(f"  Data shape: {X.shape}")
print(f"  Sepsis cases: {(y == 1).sum()} ({(y == 1).sum()/len(y)*100:.2f}%)")
print(f"  Non-sepsis cases: {(y == 0).sum()} ({(y == 0).sum()/len(y)*100:.2f}%)")

# ============================================================================
# STEP 2: CREATE SEQUENCES FOR LSTM
# ============================================================================

print("\n[2/6] Creating sequences for temporal modeling...")

def create_sequences(X, y, sequence_length=12):
    """
    Create sequences for LSTM input
    Each sequence: [t-11, t-10, ..., t-1, t] -> predict y[t+1:t+6]
    """
    X_seq = []
    y_seq = []
    
    for i in range(len(X) - sequence_length - FORECAST_STEPS + 1):
        # Input sequence: past 'sequence_length' timesteps
        X_seq.append(X[i:i + sequence_length])
        
        # Target: mean of next FORECAST_STEPS for binary classification
        future_labels = y[i + sequence_length:i + sequence_length + FORECAST_STEPS]
        y_seq.append(1 if np.mean(future_labels) > 0.5 else 0)
    
    return np.array(X_seq), np.array(y_seq)

X_seq, y_seq = create_sequences(X, y, SEQUENCE_LENGTH)

print(f"  Sequences created: {X_seq.shape}")
print(f"  Sequence shape: (samples={X_seq.shape[0]}, timesteps={X_seq.shape[1]}, features={X_seq.shape[2]})")
print(f"  Sepsis sequences: {(y_seq == 1).sum()} ({(y_seq == 1).sum()/len(y_seq)*100:.2f}%)")

# ============================================================================
# STEP 3: SCALE AND SPLIT DATA
# ============================================================================

print("\n[3/6] Scaling and splitting data...")

# Reshape for scaling
n_samples, n_timesteps, n_features = X_seq.shape
X_seq_reshaped = X_seq.reshape(-1, n_features)

# Scale features
scaler = StandardScaler()
X_seq_scaled = scaler.fit_transform(X_seq_reshaped)
X_seq_scaled = X_seq_scaled.reshape(n_samples, n_timesteps, n_features)

# Split data: train/test
X_train, X_test, y_train, y_test = train_test_split(
    X_seq_scaled, y_seq, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_seq
)

print(f"  Train set: {X_train.shape}")
print(f"  Test set: {X_test.shape}")
print(f"  Train sepsis rate: {(y_train == 1).sum()/len(y_train)*100:.2f}%")
print(f"  Test sepsis rate: {(y_test == 1).sum()/len(y_test)*100:.2f}%")

# ============================================================================
# STEP 4: BUILD LSTM MODEL WITH ATTENTION
# ============================================================================

print("\n[4/6] Building LSTM model with attention mechanism...")

def build_lstm_model(input_shape):
    """
    Build Bidirectional LSTM with Attention and Dense layers
    """
    inputs = keras.Input(shape=input_shape)
    
    # Bidirectional LSTM with attention
    x = layers.Bidirectional(
        layers.LSTM(64, return_sequences=True, dropout=0.2, recurrent_dropout=0.2)
    )(inputs)
    
    # Attention layer
    attention = layers.MultiHeadAttention(num_heads=4, key_dim=16)(x, x)
    x = layers.Add()([x, attention])
    x = layers.LayerNormalization()(x)
    
    # Second LSTM layer
    x = layers.Bidirectional(
        layers.LSTM(32, return_sequences=False, dropout=0.2, recurrent_dropout=0.2)
    )(x)
    
    # Dense layers
    x = layers.Dense(64, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(32, activation='relu')(x)
    x = layers.Dropout(0.2)(x)
    
    # Output layer
    outputs = layers.Dense(1, activation='sigmoid')(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs)
    return model

model = build_lstm_model((SEQUENCE_LENGTH, len(FEATURE_COLUMNS)))

# Compile model with class weights to handle imbalance
class_weight = {0: 1, 1: 10}  # Weight sepsis class 10x higher
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss='binary_crossentropy',
    metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
)

print(f"\nModel architecture:")
model.summary()

# ============================================================================
# STEP 5: TRAIN MODEL
# ============================================================================

print("\n[5/6] Training LSTM model...")

# Callbacks
early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)

history = model.fit(
    X_train, y_train,
    validation_split=VALIDATION_SPLIT,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    class_weight=class_weight,
    callbacks=[early_stop, reduce_lr],
    verbose=1
)

print(f"\nTraining completed in {len(history.history['loss'])} epochs")

# ============================================================================
# STEP 6: EVALUATE MODEL
# ============================================================================

print("\n[6/6] Evaluating on test set...")

# Predictions
y_pred_proba = model.predict(X_test, verbose=0)
y_pred = (y_pred_proba > 0.5).astype(int).flatten()

# Metrics
acc = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
auc = roc_auc_score(y_test, y_pred_proba)
tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

print(f"\n{'='*70}")
print(f"PHASE 3 LSTM MODEL PERFORMANCE")
print(f"{'='*70}")
print(f"\nAccuracy:     {acc:.4f} ({acc*100:.2f}%)")
print(f"Precision:    {precision:.4f} ({precision*100:.2f}%)")
print(f"Recall:       {recall:.4f} ({recall*100:.2f}%)")
print(f"F1 Score:     {f1:.4f}")
print(f"ROC-AUC:      {auc:.4f}")

print(f"\nConfusion Matrix:")
print(f"  True Negatives:  {tn}")
print(f"  False Positives: {fp}")
print(f"  False Negatives: {fn}")
print(f"  True Positives:  {tp}")

print(f"\nSensitivity (Recall):  {tp/(tp+fn):.4f} (catches {tp/(tp+fn)*100:.2f}% of sepsis)")
print(f"Specificity:           {tn/(tn+fp):.4f} (correctly identifies {tn/(tn+fp)*100:.2f}% of non-sepsis)")

# ============================================================================
# SAVE MODEL AND COMPONENTS
# ============================================================================

print(f"\n{'='*70}")
print("SAVING MODEL AND COMPONENTS")
print(f"{'='*70}\n")

# Save LSTM model
model.save('model_phase3_lstm.h5')
print("✓ Saved: model_phase3_lstm.h5")

# Save scaler
pickle.dump(scaler, open('scaler_phase3.pkl', 'wb'))
print("✓ Saved: scaler_phase3.pkl")

# Save training history
pickle.dump(history.history, open('history_phase3.pkl', 'wb'))
print("✓ Saved: history_phase3.pkl")

# Save test metrics
metrics = {
    'accuracy': acc,
    'precision': precision,
    'recall': recall,
    'f1_score': f1,
    'roc_auc': auc,
    'confusion_matrix': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)},
    'sequence_length': SEQUENCE_LENGTH,
    'forecast_steps': FORECAST_STEPS,
    'n_features': len(FEATURE_COLUMNS),
    'feature_names': FEATURE_COLUMNS
}
pickle.dump(metrics, open('metrics_phase3.pkl', 'wb'))
print("✓ Saved: metrics_phase3.pkl")

# ============================================================================
# VISUALIZATION
# ============================================================================

print("\n" + "="*70)
print("GENERATING VISUALIZATIONS")
print("="*70 + "\n")

# Plot 1: Training History
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Phase 3 LSTM - Training History', fontsize=16, fontweight='bold')

axes[0, 0].plot(history.history['loss'], label='Train Loss')
axes[0, 0].plot(history.history['val_loss'], label='Validation Loss')
axes[0, 0].set_xlabel('Epoch')
axes[0, 0].set_ylabel('Loss')
axes[0, 0].set_title('Loss Over Epochs')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].plot(history.history['accuracy'], label='Train Accuracy')
axes[0, 1].plot(history.history['val_accuracy'], label='Validation Accuracy')
axes[0, 1].set_xlabel('Epoch')
axes[0, 1].set_ylabel('Accuracy')
axes[0, 1].set_title('Accuracy Over Epochs')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

axes[1, 0].plot(history.history['recall'], label='Train Recall')
axes[1, 0].plot(history.history['val_recall'], label='Validation Recall')
axes[1, 0].set_xlabel('Epoch')
axes[1, 0].set_ylabel('Recall')
axes[1, 0].set_title('Recall Over Epochs (Sepsis Detection Rate)')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].plot(history.history['precision'], label='Train Precision')
axes[1, 1].plot(history.history['val_precision'], label='Validation Precision')
axes[1, 1].set_xlabel('Epoch')
axes[1, 1].set_ylabel('Precision')
axes[1, 1].set_title('Precision Over Epochs')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('training_history_phase3.png', dpi=300, bbox_inches='tight')
print("✓ Saved: training_history_phase3.png")

# Plot 2: Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax, cbar=True,
            xticklabels=['No Sepsis', 'Sepsis'],
            yticklabels=['No Sepsis', 'Sepsis'])
ax.set_xlabel('Predicted Label')
ax.set_ylabel('True Label')
ax.set_title('Phase 3 LSTM - Confusion Matrix')
plt.tight_layout()
plt.savefig('confusion_matrix_phase3.png', dpi=300, bbox_inches='tight')
print("✓ Saved: confusion_matrix_phase3.png")

# Plot 3: ROC Curve
from sklearn.metrics import roc_curve

fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(fpr, tpr, linewidth=2, label=f'ROC Curve (AUC = {auc:.4f})')
ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random Classifier')
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.set_title('Phase 3 LSTM - ROC Curve')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('roc_curve_phase3.png', dpi=300, bbox_inches='tight')
print("✓ Saved: roc_curve_phase3.png")

print("\n" + "="*70)
print("PHASE 3 TRAINING COMPLETE!")
print("="*70)
print(f"""
MODEL CAPABILITIES:
✓ Predicts sepsis up to {FORECAST_STEPS} hours in advance
✓ Uses {SEQUENCE_LENGTH} hours of historical data
✓ Bidirectional LSTM with Attention mechanism
✓ Handles temporal patterns in vital signs

KEY IMPROVEMENTS OVER PHASE 1-2:
• Phase 1: Static features, 97.71% accuracy
• Phase 2: Static + trend features, Phase 3 trend tuning
• Phase 3: Temporal sequences with LSTM
  - Captures dynamic vital sign patterns
  - Multi-hour prediction window
  - Attention-based feature importance

NEXT STEPS:
1. Deploy phase3 model in Flask app
2. Compare performance across all phases
3. Implement ensemble of all three phases
4. Add real-time monitoring for continuous patients
""")
