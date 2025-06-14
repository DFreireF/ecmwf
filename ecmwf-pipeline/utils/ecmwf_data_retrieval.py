#!/usr/bin/env python3
"""
ECMWF Data Retrieval Functions
Can generate synthetic data for testing or retrieve real ERA5 data from
the Copernicus Climate Data Store (CDS) API. This version is robust
to filename changes by the CDS API.
"""
import logging
from pathlib import Path
import numpy as np
import netCDF4 as nc
from datetime import datetime
import shutil
import os

try:
    from cdsapi import Client as CDSClient
    ECMWF_API_AVAILABLE = True
except ImportError:
    ECMWF_API_AVAILABLE = False
    CDSClient = None

logger = logging.getLogger(__name__)

class ECMWFDataGenerator:
    """Generates and retrieves test data for the processing pipeline."""
    def __init__(self, use_real_data: bool = False):
        self.config = {"area": [55, -10, 45, 5], "grid": [0.25, 0.25]}
        self.cds_client = None
        self.use_real_data = use_real_data

        if self.use_real_data:
            if ECMWF_API_AVAILABLE:
                try:
                    self.cds_client = CDSClient(quiet=True, verify=True)
                    logger.info("CDS API client initialized successfully in REAL data mode.")
                except Exception:
                    logger.warning("Could not initialize CDS Client. Check API credentials in ~/.cdsapirc. Falling back to synthetic data.")
                    self.cds_client = None
            else:
                logger.warning("Real data requested, but 'cdsapi' library not found. Falling back to synthetic data.")

    def retrieve_surface_data(self, output_path: Path, date: str):
        """Main method to get data. Delegates to real or synthetic based on initialization."""
        if self.cds_client:
            self._retrieve_real_surface_data(output_path, date)
        else:
            if self.use_real_data:
                logger.info("Executing fallback: generating synthetic data.")
            self._generate_synthetic_surface_data(output_path, date)

    def _retrieve_real_surface_data(self, output_path: Path, date: str):
        """Retrieves real ERA5 data and ensures it is moved to the correct final path."""
        logger.info(f"Attempting to retrieve REAL surface data for {date}")
        
        # Define a temporary path for the download
        temp_path = output_path.with_suffix('.download')
        
        try:
            year, month, day = date.split('-')
            self.cds_client.retrieve(
                'reanalysis-era5-single-levels',
                {
                    'product_type': 'reanalysis',
                    'variable': ['2m_temperature', '10m_u_component_of_wind', '10m_v_component_of_wind', 'mean_sea_level_pressure'],
                    'year': year, 'month': month, 'day': day,
                    'time': ['00:00', '06:00', '12:00', '18:00'],
                    'area': self.config['area'], 'grid': self.config['grid'], 'format': 'netcdf',
                },
                str(temp_path))

            # Move the completed download to the final destination, overwriting if it exists.
            shutil.move(temp_path, output_path)
            logger.info(f"Successfully retrieved and saved REAL ERA5 surface data to {output_path}")

        except Exception as e:
            logger.error(f"Failed to retrieve ERA5 data from CDS: {e}", exc_info=True)
            logger.info("Executing fallback: generating synthetic data instead.")
            self._generate_synthetic_surface_data(output_path, date)
        finally:
            # Clean up temporary file if it still exists
            if os.path.exists(temp_path):
                os.remove(temp_path)


    def _generate_synthetic_surface_data(self, output_path: Path, date: str):
        logger.info(f"Generating SYNTHETIC surface data for {date} at {output_path}")
        with nc.Dataset(str(output_path), 'w', format='NETCDF4') as ds:
            lat_range = np.arange(self.config['area'][0], self.config['area'][2] - self.config['grid'][0], -self.config['grid'][0])
            lon_range = np.arange(self.config['area'][1], self.config['area'][3] + self.config['grid'][1], self.config['grid'][1])
            hours = [0, 6, 12, 18]
            
            ds.createDimension('latitude', len(lat_range)); ds.createVariable('latitude', 'f4', ('latitude',))[:] = lat_range
            ds.createDimension('longitude', len(lon_range)); ds.createVariable('longitude', 'f4', ('longitude',))[:] = lon_range
            # IMPORTANT: Add a 'time' variable to the synthetic data to match the real data structure
            ds.createDimension('time', len(hours)); ds.createVariable('time', 'i4', ('time',))[:] = hours
            
            shape = (len(hours), len(lat_range), len(lon_range))
            ds.createVariable('t2m', 'f4', ('time', 'latitude', 'longitude'))[:] = 285 + np.random.randn(*shape) * 10
            ds.createVariable('msl', 'f4', ('time', 'latitude', 'longitude'))[:] = 101325 + np.random.randn(*shape) * 500
            ds.createVariable('u10', 'f4', ('time', 'latitude', 'longitude'))[:] = 5 + np.random.randn(*shape) * 5
            ds.createVariable('v10', 'f4', ('time', 'latitude', 'longitude'))[:] = 2 + np.random.randn(*shape) * 5
        logger.info("Synthetic data generation complete.")