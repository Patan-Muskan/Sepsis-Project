#!/usr/bin/env python
"""
Fast training script for 27-feature sepsis model.
Uses exact same features as inference in app.py.
"""

import pandas as pd
import pickle
import numpy as np
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.utils import resample
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("FAST TRAINING - 27 Feature Sepsis Model")
print("=" * 60)

# Exact 27 features used in app.py inference
FEATURE_NAMES = [
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp',
    'BaseExcess', 'HCO3', 'FiO2', 'PaCO2', 'SaO2', 'Creatinine',
    'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium', 'Phosphate',
    'Bilirubin_total', 'Hgb', 'WBC', 'Fibrinogen', 'Platelets',
    'Age', 'Gender', 'HospAdmTime', 'ICULOS'
]

print(f"\n[1/6] Loading dataset...")
dataset = pd.read_csv("sepsis.csv")
print(f"  Loaded: {dataset.shape[0]} rows")

print(f"\n[2/6] Selecting 27 features (matching inference)...")
dataset = dataset[FEATURE_NAMES + ['SepsisLabel']]

print(f"\n[3/6] Balancing classes...")
df_majority = dataset[dataset.SepsisLabel==0]
df_minority = dataset[dataset.SepsisLabel==1]
print(f"  No Sepsis: {len(df_majority)}, Sepsis: {len(df_minority)}")

df_minority_upsampled = resample(df_minority, replace=True, n_samples=len(df_majority), random_state=42)
df_balanced = pd.concat([df_majority, df_minority_upsampled])
print(f"  Balanced: {len(df_balanced)} total")

print(f"\n[4/6] Preparing train/test split...")
X = df_balanced[FEATURE_NAMES].values
Y = df_balanced['SepsisLabel'].values

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
print(f"  Train: {len(X_train)}, Test: {len(X_test)}")

print(f"\n[5/6] Scaling features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"\n[6/6] Training MLP (fast config)...")
model = MLPClassifier(
    hidden_layer_sizes=(64, 32, 16),
    activation='relu',
    solver='adam',
    max_iter=500,
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=20,
    random_state=42,
    verbose=False
)

model.fit(X_train_scaled, Y_train)

# Evaluate
Y_pred = model.predict(X_test_scaled)
Y_proba = model.predict_proba(X_test_scaled)[:, 1]

acc = accuracy_score(Y_test, Y_pred)
prec = precision_score(Y_test, Y_pred)
rec = recall_score(Y_test, Y_pred)
auc = roc_auc_score(Y_test, Y_proba)

print(f"\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"  Accuracy:  {acc:.4f} ({acc*100:.1f}%)")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  ROC-AUC:   {auc:.4f}")

tn, fp, fn, tp = confusion_matrix(Y_test, Y_pred).ravel()
print(f"\n  Confusion Matrix:")
print(f"    TN={tn}, FP={fp}")
print(f"    FN={fn}, TP={tp}")

# Save
print(f"\nSaving model and scaler...")
pickle.dump(model, open('model.pkl', 'wb'))
pickle.dump(scaler, open('scaler.pkl', 'wb'))
print(f"  model.pkl - saved")
print(f"  scaler.pkl - saved")

print(f"\n" + "=" * 60)
print("DONE - Model trained with exact 27 inference features")
print("=" * 60)
