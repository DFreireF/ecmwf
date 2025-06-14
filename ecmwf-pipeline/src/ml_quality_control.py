import logging
import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MLQualityControl:
    """
    Applies machine learning-based quality control by checking for anomalies.
    """
    def __init__(self, model_path: Path):
        self.model = None
        if not model_path.exists():
            logger.error(f"ML model file not found at {model_path}! ML QC will be disabled.")
        else:
            try:
                self.model = joblib.load(model_path)
                logger.info(f"Successfully loaded ML anomaly detection model from {model_path}.")
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}. ML QC will be disabled.")
    
    def check_observation_anomaly(self, obs: Dict[str, Any]) -> bool:
        """
        Uses the loaded IsolationForest model to predict if an observation is an anomaly.

        Returns:
            True if the observation is NOT an anomaly (is an inlier).
            False if the observation IS an anomaly (is an outlier).
        """
        if not self.model:
            return True # If model isn't loaded, approve everything.

        try:
            # Create a feature vector from the observation, in the same order as training
            wind_speed = np.sqrt(obs['u_wind']**2 + obs['v_wind']**2)
            features = np.array([[
                obs['temperature'],
                obs['pressure'],
                wind_speed
            ]])
            
            # predict() returns 1 for inliers and -1 for outliers (anomalies)
            prediction = self.model.predict(features)
            
            if prediction[0] == -1:
                logger.debug(f"ML QC FAIL: Observation flagged as anomaly: {obs}")
                return False
            
            return True

        except Exception as e:
            logger.warning(f"Could not perform ML QC check due to error: {e}")
            return True # Fail open: if check fails, approve the data