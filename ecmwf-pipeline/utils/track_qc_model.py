#!/usr/bin/env python3
"""
Registers the pre-trained Quality Control model with the MLflow Model Registry.

This script should be run once after the model has been created by
'create_qc_model.py'. It establishes a baseline version of the model,
allowing for tracking and governance, which is a key MLOps practice.
"""
import mlflow
import joblib
from pathlib import Path
from sklearn.utils import estimator_html_repr

def log_model_to_registry():
    """
    Loads the trained IsolationForest model and registers it with MLflow.
    """
    project_root = Path(__file__).resolve().parent.parent
    model_path = project_root / "models/qc_anomaly_model.joblib"
    model_registry_name = "c3s_qc_anomaly_detector"
    
    # Check if the model file exists first
    if not model_path.exists():
        print(f"ERROR: Model file not found at {model_path}")
        print("Please run 'python utils/create_qc_model.py' first.")
        return

    # Set the MLflow tracking URI to use a local directory named 'mlruns'
    # This ensures MLflow saves its data inside your project directory.
    mlflow.set_tracking_uri(f"file://{project_root / 'mlruns'}")
    
    print(f"Loading model from disk: {model_path}...")
    model = joblib.load(model_path)

    # Start an MLflow run to contain the model registration artifacts
    with mlflow.start_run(run_name="Register QC Anomaly Model") as run:
        print(f"Logging model '{model_registry_name}' to MLflow registry...")
        run_id = run.info.run_id
        print(f"MLflow Run ID: {run_id}")

        # Log the model's hyperparameters for reproducibility
        print("Logging model parameters...")
        mlflow.log_params(model.get_params())
        
        # Log a visual HTML representation of the scikit-learn pipeline/model
        # This is a great artifact for understanding the model's structure
        model_details_path = Path("model_details.html")
        with open(model_details_path, "w", encoding="utf-8") as f:
            f.write(estimator_html_repr(model))
        
        print("Logging model visualization artifact...")
        mlflow.log_artifact(str(model_details_path), "model_visualization")
        # Clean up the local HTML file
        model_details_path.unlink()

        # The most important step: Log the model to the registry
        # MLflow's sklearn integration makes this easy.
        # This will create version 1 of the model in the registry.
        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model", # The sub-folder within the run's artifacts
            registered_model_name=model_registry_name
        )
        print(f"Model logged successfully. URI: {model_info.model_uri}")

    print("\n--- Model Registration Complete ---")
    print(f"Model '{model_registry_name}' (Version 1) is now in the registry.")
    print(f"To view, run 'mlflow ui' from the project directory ('{project_root}') and navigate to the 'Models' tab.")

if __name__ == "__main__":
    log_model_to_registry()