#!/usr/bin/env python3
"""
One-time script to create and save a simple ML model for Quality Control.
This simulates a model provided by a data science team.
"""
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from pathlib import Path

def create_model():
    """
    Creates a simple IsolationForest model and saves it.
    IsolationForest is good for anomaly detection.
    """
    # Create a sample of "normal" data. In the real world, this would
    # be a large historical dataset of valid observations.
    print("Generating sample 'normal' data for model training...")
    rng = np.random.RandomState(42)
    X_train = rng.randn(1000, 3) # 1000 observations, 3 features (temp, pressure, wind_speed)
    # Simulate realistic ranges
    X_train[:, 0] = X_train[:, 0] * 10 + 288  # Temperature ~288K
    X_train[:, 1] = X_train[:, 1] * 500 + 101325 # Pressure ~101325 Pa
    X_train[:, 2] = X_train[:, 2] * 5 + 10 # Wind speed ~10 m/s
    
    # Train the IsolationForest model
    print("Training IsolationForest model...")
    # contamination='auto' is a modern standard.
    # The model learns the general distribution of the data.
    model = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
    model.fit(X_train)
    
    # Save the trained model to a file
    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / "qc_anomaly_model.joblib"
    print(f"Saving model to {model_path}...")
    joblib.dump(model, model_path)
    
    print("\nModel creation successful. You can now use this model in the main pipeline.")
    print("Make sure to commit 'models/qc_anomaly_model.joblib' to your Git repository.")

if __name__ == "__main__":
    create_model()