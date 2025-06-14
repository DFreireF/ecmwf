#!/usr/bin/env python3
"""
Meteorological Data Processor
This is the final, robust version. It adopts the logic from the original
working script, using a base_date and the actual shape of the data to
determine time, making it resilient to missing time steps from the API.

It also returns detailed QC statistics for monitoring and tracking.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta
import numpy as np
import netCDF4 as nc
import eccodes as ec
from .quality_control import QualityControl
# Use a string literal for the type hint to avoid circular import issues
from src.ml_quality_control import MLQualityControl


logger = logging.getLogger(__name__)

class NetCDFReader:
    def __init__(self, filepath: str, var_map: Dict, qc: QualityControl, base_date: datetime):
        """
        Initializes the reader. A base_date is now required as the source of truth for time.
        Args:
            filepath (str): Path to the NetCDF file.
            var_map (Dict): Configuration for mapping standard variable names to file-specific names.
            qc (QualityControl): An instance for performing physical range checks.
            base_date (datetime): The UTC date for the start of the observation period (T00:00:00).
        """
        self.filepath = Path(filepath)
        self.var_map = var_map
        self.qc = qc
        self.base_date = base_date
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")

    def _get_var(self, ds: nc.Dataset, standard_name: str, obs_type: str) -> nc.Variable:
        """Looks up a variable in the NetCDF dataset using the configuration map."""
        provider_var_name = self.var_map[obs_type].get(standard_name)
        if provider_var_name and provider_var_name in ds.variables:
            return ds.variables[provider_var_name]
        
        # Fallback for common alternative names if not in map
        fallbacks = {'latitude': 'lat', 'longitude': 'lon'}
        if standard_name in fallbacks and fallbacks[standard_name] in ds.variables:
            return ds.variables[fallbacks[standard_name]]
            
        raise KeyError(f"Could not find variable for standard name '{standard_name}' in {self.filepath}.")

    def extract_surface_observations_with_stats(self, ml_qc: 'MLQualityControl') -> (List[Dict], Dict):
        """
        Extracts observations and now explicitly returns a dictionary of QC statistics
        for logging in MLflow or other monitoring systems.

        Args:
            ml_qc (MLQualityControl): An instance for performing ML-based anomaly checks.
        
        Returns:
            A tuple containing:
            - A list of valid observation dictionaries.
            - A dictionary of detailed QC statistics.
        """
        observations = []
        stats = {
            'obs_initial_count': 0,
            'obs_pass_physical_qc': 0,
            'obs_fail_physical_qc': 0,
            'obs_pass_ml_qc': 0,
            'obs_fail_ml_qc': 0,
            'obs_final_count': 0
        }
        
        logger.info(f"Extracting surface observations from {self.filepath.name}")
        
        # A predefined list of the hours we *expect* based on our API request.
        possible_hours = [0, 6, 12, 18]
        
        with nc.Dataset(self.filepath, 'r') as ds:
            # Read the data variables first using the mapping
            lats = self._get_var(ds, 'latitude', 'surface')[:]
            lons = self._get_var(ds, 'longitude', 'surface')[:]
            t2m = self._get_var(ds, 'temperature', 'surface')
            msl = self._get_var(ds, 'pressure', 'surface')
            u10 = self._get_var(ds, 'u_wind', 'surface')
            v10 = self._get_var(ds, 'v_wind', 'surface')

            # --- Resilient Time Logic ---
            # Get the number of time steps actually present in the data variable.
            num_steps_in_file = t2m.shape[0]
            if num_steps_in_file > len(possible_hours):
                raise ValueError(f"File contains more time steps ({num_steps_in_file}) than expected ({len(possible_hours)}).")
            
            # Use only the hours corresponding to the data we actually have.
            hours_to_process = possible_hours[:num_steps_in_file]
            logger.info(f"Data file contains {num_steps_in_file} time steps. Processing hours: {hours_to_process}")

            # --- Loop with Statistics Gathering ---
            stats['obs_initial_count'] = t2m.size # Total number of grid points across all time steps

            for t_idx, hour in enumerate(hours_to_process):
                obs_time = self.base_date + timedelta(hours=int(hour))
                for lat_idx, lat in enumerate(lats):
                    for lon_idx, lon in enumerate(lons):
                        obs_data = {
                            'latitude': float(lat), 'longitude': float(lon), 'time': obs_time,
                            'temperature': float(t2m[t_idx, lat_idx, lon_idx]),
                            'pressure': float(msl[t_idx, lat_idx, lon_idx]),
                            'u_wind': float(u10[t_idx, lat_idx, lon_idx]),
                            'v_wind': float(v10[t_idx, lat_idx, lon_idx]),
                        }

                        # Apply QC checks in sequence
                        if self.qc.check_surface_observation(obs_data):
                            stats['obs_pass_physical_qc'] += 1
                            
                            if ml_qc.check_observation_anomaly(obs_data):
                                stats['obs_pass_ml_qc'] += 1
                                observations.append(obs_data)
                            else:
                                stats['obs_fail_ml_qc'] += 1
                        else:
                            stats['obs_fail_physical_qc'] += 1
            
            stats['obs_final_count'] = len(observations)
            logger.info(f"QC Complete. Final observation count: {stats['obs_final_count']}/{stats['obs_initial_count']}.")
            return observations, stats


class BUFREncoder:
    """Encodes a list of observation dictionaries into a BUFR file."""

    def encode(self, observations: List[Dict], output_file: str, obs_type: str):
        """
        Main encoding method.
        Args:
            observations (List[Dict]): The list of valid observation data.
            output_file (str): The path to write the BUFR file to.
            obs_type (str): The type of observation ('surface' or 'upper_air').
        """
        encoder_map = {'surface': self._encode_surface, 'upper_air': self._encode_upper_air}
        if obs_type not in encoder_map:
            raise ValueError(f"Unknown observation type for BUFR encoding: {obs_type}")

        count = 0
        try:
            with open(output_file, 'wb') as f:
                for obs in observations:
                    bufr_msg_handle = None
                    try:
                        bufr_msg_handle = encoder_map[obs_type](obs)
                        if bufr_msg_handle:
                            ec.codes_write(bufr_msg_handle, f)
                            count += 1
                    except Exception as e:
                        logger.error(f"Failed to encode observation: {e}", exc_info=False)
                    finally:
                        if bufr_msg_handle:
                            ec.codes_release(bufr_msg_handle)
            logger.info(f"Successfully encoded {count} BUFR messages to {output_file}")
        except IOError as e:
            logger.critical(f"Could not write to output file {output_file}: {e}")
            raise

    def _encode_surface(self, obs: Dict) -> int:
        """Encodes a single surface observation into a BUFR message handle."""
        bufr = ec.codes_bufr_new_from_samples("BUFR4_local")
        
        # Set BUFR headers and descriptors
        # This sequence represents a standard surface observation
        ec.codes_set_array(bufr, "unexpandedDescriptors", [
            301021, 4001, 4002, 4003, 4004, 4005, 12101, 10004, 11003, 11004
        ])
        
        ec.codes_set(bufr, "unpack", 1) # Must unpack before setting data values

        # Set data values using BUFR keys
        ec.codes_set(bufr, "#1#latitude", obs['latitude'])
        ec.codes_set(bufr, "#1#longitude", obs['longitude'])
        
        obs_time = obs['time']
        ec.codes_set(bufr, "#1#year", obs_time.year)
        ec.codes_set(bufr, "#1#month", obs_time.month)
        ec.codes_set(bufr, "#1#day", obs_time.day)
        ec.codes_set(bufr, "#1#hour", obs_time.hour)
        ec.codes_set(bufr, "#1#minute", obs_time.minute)
        
        ec.codes_set(bufr, "#1#airTemperature", obs['temperature'])
        ec.codes_set(bufr, "#1#nonCoordinatePressure", obs['pressure'])
        ec.codes_set(bufr, "#1#u", obs['u_wind'])
        ec.codes_set(bufr, "#1#v", obs['v_wind'])
        
        ec.codes_set(bufr, "pack", 1) # Pack the message before writing
        
        return bufr

    def _encode_upper_air(self, obs: Dict):
        bufr = ec.codes_bufr_new_from_samples("BUFR4")
        profile = obs['profile']; num_levels = len(profile)
        ec.codes_set_array(bufr, "unexpandedDescriptors", [309056])
        ec.codes_set(bufr, "pack", 1)
        obs_time = obs['time']
        ec.codes_set(bufr, "#1#year", obs_time.year); ec.codes_set(bufr, "#1#month", obs_time.month)
        ec.codes_set(bufr, "#1#day", obs_time.day); ec.codes_set(bufr, "#1#hour", obs_time.hour)
        ec.codes_set(bufr, "#1#latitude", obs['latitude']); ec.codes_set(bufr, "#1#longitude", obs['longitude'])
        ec.codes_set(bufr, "delayedDescriptorReplicationFactor", num_levels)
        ec.codes_set_array(bufr, "pressure", [p['pressure'] for p in profile])
        ec.codes_set_array(bufr, "airTemperature", [p['temperature'] for p in profile])
        ec.codes_set_array(bufr, "uComponentOfWind", [p['u_wind'] for p in profile])
        ec.codes_set_array(bufr, "vComponentOfWind", [p['v_wind'] for p in profile])
        return bufr