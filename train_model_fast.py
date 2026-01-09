#!/usr/bin/env python
# Fast model training script - skips visualizations and extra classifiers

import pandas as pd
import pickle
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.utils import resample

print("Loading dataset...")
dataset = pd.read_csv("sepsis.csv")

print("Balancing classes...")
df_majority = dataset[dataset.SepsisLabel==0]
df_minority = dataset[dataset.SepsisLabel==1]

df_minority_upsampled = resample(df_minority, 
                                 replace=True,
                                 n_samples=37945,
                                 random_state=123)

df_upsampled = pd.concat([df_majority, df_minority_upsampled])

print("Preparing features and labels...")
X = df_upsampled[df_upsampled.columns[0:40]].values
Y = df_upsampled[df_upsampled.columns[40:]].values

labelencoder_Y = preprocessing.LabelEncoder()
Y = labelencoder_Y.fit_transform(Y)

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.20, random_state=0)

print("Training MLP model (this may take a few minutes)...")
model = MLPClassifier(
    activation='tanh',
    solver='lbfgs',
    early_stopping=False,
    hidden_layer_sizes=(40,10,10,10,10, 2),
    random_state=1,
    batch_size='auto',
    max_iter=13000,
    learning_rate_init=1e-5,
    tol=1e-4,
    verbose=1
)

model.fit(X_train, Y_train)

print("\nSaving model...")
pickle.dump(model, open('model.pkl', 'wb'))
print("Model saved successfully to model.pkl")

# Quick test
from sklearn.metrics import accuracy_score
train_predictions = model.predict(X_test)
acc = accuracy_score(Y_test, train_predictions)
print(f"Model Accuracy on test set: {acc:.4%}")
