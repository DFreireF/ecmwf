#!/usr/bin/env python3
import pytest
import numpy as np
import netCDF4 as nc
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.quality_control import QualityControl
from src.data_processor import NetCDFReader
# We mock the ML QC for this unit test to keep it simple
from unittest.mock import MagicMock

@pytest.fixture
def test_config():
    """Provides a sample QC configuration for tests."""
    return {
        'temperature_K': {'min': 250.0, 'max': 320.0},
        'pressure_Pa': {'min': 95000.0, 'max': 105000.0}
    }

@pytest.fixture
def synthetic_nc_file(tmp_path):
    """Creates a temporary NetCDF file for testing."""
    p = tmp_path / "test_surface_20230101.nc"
    with nc.Dataset(p, 'w', format='NETCDF4') as ds:
        ds.createDimension('latitude', 2); ds.createDimension('longitude', 2); ds.createDimension('time', 1)
        ds.createVariable('latitude', 'f4', ('latitude',))[:] = [50.0, 51.0]
        ds.createVariable('longitude', 'f4', ('longitude',))[:] = [0.0, 1.0]
        
        # Data points for testing QC logic
        temp_data = np.array([[[290.0, 100.0], [300.0, 305.0]]]) # 100K is bad
        pres_data = np.array([[[101000.0, 102000.0], [90000.0, 104000.0]]]) # 90000 Pa is bad
        
        ds.createVariable('t2m', 'f4', ('time', 'latitude', 'longitude'))[:] = temp_data
        ds.createVariable('msl', 'f4', ('time', 'latitude', 'longitude'))[:] = pres_data
        ds.createVariable('u10', 'f4', ('time', 'latitude', 'longitude'))[:] = np.ones((1, 2, 2))
        ds.createVariable('v10', 'f4', ('time', 'latitude', 'longitude'))[:] = np.ones((1, 2, 2))
    return p

def test_data_processing_and_qc_stats(test_config, synthetic_nc_file):
    """
    Tests the main data processor, ensuring it provides correct output
    and accurate QC statistics.
    """
    # 1. SETUP
    qc = QualityControl(test_config)
    var_map = {
        'surface': {
            'latitude': 'latitude', 'longitude': 'longitude',
            'temperature': 't2m', 'pressure': 'msl',
            'u_wind': 'u10', 'v_wind': 'v10'
        }
    }
    test_base_date = datetime(2023, 1, 1)

    # Mock the ML QC class. For this test, we assume all data that passes
    # physical QC also passes ML QC.
    mock_ml_qc = MagicMock()
    mock_ml_qc.check_observation_anomaly.return_value = True # Always returns True

    # 2. EXECUTION
    reader = NetCDFReader(
        str(synthetic_nc_file), var_map, qc, base_date=test_base_date
    )
    # The new method name is required here
    observations, stats = reader.extract_surface_observations_with_stats(mock_ml_qc)
    
    # 3. ASSERTION
    # There were 4 total data points in the file
    assert stats['obs_initial_count'] == 4
    
    # Check physical QC stats: 2 points had bad values (temp and pressure)
    assert stats['obs_pass_physical_qc'] == 2
    assert stats['obs_fail_physical_qc'] == 2
    
    # Check ML QC stats: Of the 2 that passed physical, our mock passes both
    assert stats['obs_pass_ml_qc'] == 2
    assert stats['obs_fail_ml_qc'] == 0
    
    # Final check: The number of returned observations should match the final count
    assert stats['obs_final_count'] == 2
    assert len(observations) == 2
    
    # Verify it's the correct observations that remain
    remaining_temps = {obs['temperature'] for obs in observations}
    assert remaining_temps == {290.0, 305.0}