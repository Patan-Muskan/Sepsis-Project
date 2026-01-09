#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Train and save the sepsis detection model
"""

import numpy as np
import pandas as pd
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.utils import resample
import pickle

print("Loading dataset...")
dataset = pd.read_csv("sepsis.csv")

print("Dataset shape:", dataset.shape)
print("Class distribution:")
print(dataset['SepsisLabel'].value_counts())

# Resample to balance classes
print("\nBalancing classes...")
df_majority = dataset[dataset.SepsisLabel == 0]
df_minority = dataset[dataset.SepsisLabel == 1]

df_minority_upsampled = resample(df_minority, 
                                 replace=True,
                                 n_samples=37945,
                                 random_state=123)

df_upsampled = pd.concat([df_majority, df_minority_upsampled])
print("Balanced dataset shape:", df_upsampled.shape)

# Prepare features and labels
X = df_upsampled[df_upsampled.columns[0:40]].values
Y = df_upsampled[df_upsampled.columns[40:]].values

# Encode labels
labelencoder_Y = preprocessing.LabelEncoder()
Y = labelencoder_Y.fit_transform(Y)

# Split data
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.20, random_state=0)
print("\nTraining data shape:", X_train.shape)
print("Testing data shape:", X_test.shape)

# Train MLP model
print("\nTraining MLP model...")
mlp = MLPClassifier(
    activation='tanh',
    solver='lbfgs',
    early_stopping=False,
    hidden_layer_sizes=(40, 10, 10, 10, 10, 2),
    random_state=1,
    batch_size='auto',
    max_iter=13000,
    learning_rate_init=1e-5,
    tol=1e-4,
    verbose=1
)

mlp.fit(X_train, Y_train)

# Evaluate
train_predictions = mlp.predict(X_test)
from sklearn.metrics import accuracy_score
acc = accuracy_score(Y_test, train_predictions)
print("\nModel Accuracy: {:.4%}".format(acc))

# Save model
print("\nSaving model to model.pkl...")
pickle.dump(mlp, open('model.pkl', 'wb'))
print("Model saved successfully!")
