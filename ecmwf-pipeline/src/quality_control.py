import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class QualityControl:
    """
    Performs initial quality control on observational and model-generated data.
    Configuration is passed on initialization.
    """
    def __init__(self, qc_params: Dict):
        self.params = qc_params
        logger.info(f"QC module initialized with params: {self.params}")

    def _check_range(self, value: float, key: str) -> bool:
        """Checks if a value is within the configured min/max range."""
        if key not in self.params:
            # If no check is defined, it passes.
            return True
        param_range = self.params[key]
        if not (param_range['min'] <= value <= param_range['max']):
            logger.debug(f"QC FAIL: {key} value {value} out of range [{param_range['min']}, {param_range['max']}].")
            return False
        return True

    def check_surface_observation(self, obs: Dict[str, Any]) -> bool:
        """
        Runs all configured QC checks for a single surface observation.
        Returns True if all checks pass, False otherwise.
        """
        checks = {
            "temperature_K": self._check_range(obs.get('temperature', 0), 'temperature_K'),
            "pressure_Pa": self._check_range(obs.get('pressure', 0), 'pressure_Pa'),
            "u_wind_ms": self._check_range(obs.get('u_wind', 0), 'wind_component_ms'),
            "v_wind_ms": self._check_range(obs.get('v_wind', 0), 'wind_component_ms'),
        }
        
        # Returns False if any of the check values are False
        return all(checks.values())