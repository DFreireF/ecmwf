#!/usr/bin/env python3
"""
ECMWF Data Retrieval Functions for Observation Pipeline
"""
import logging
from pathlib import Path
from typing import Optional, List

import numpy as np
import netCDF4 as nc
from datetime import datetime, timedelta
import argparse

try:
    from cdsapi import Client as CDSClient
    ECMWF_API_AVAILABLE = True
except ImportError:
    ECMWF_API_AVAILABLE = False
    CDSClient = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not ECMWF_API_AVAILABLE:
    logging.warning("cdsapi library not found. Real data retrieval is disabled.")


class ECMWFTestDataGenerator:
    """Generates and retrieves test data using the stable ERA5 reanalysis datasets."""
    def __init__(self):
        self.config = {"area": [55, 5, 50, 15], "grid": [0.25, 0.25]}
        self.cds_client: Optional[CDSClient] = None
        if ECMWF_API_AVAILABLE:
            try:
                self.cds_client = CDSClient()
            except Exception as e:
                logger.warning(f"Failed to initialize CDS client: {e}. Real data retrieval disabled.")

    def retrieve_surface_data(self, output_path: str, date: str, use_real_data: bool = False) -> str:
        logger.info(f"Preparing surface data for {date}")
        if use_real_data and self.cds_client:
            return self._retrieve_real_surface_data(output_path, date)
        if use_real_data:
            logger.warning("Real data requested but CDS client is not available. Falling back to synthetic.")
        return self._generate_synthetic_surface_data(output_path, date)

    def retrieve_upper_air_data(self, output_path: str, date: str, use_real_data: bool = False) -> str:
        logger.info(f"Preparing upper-air data for {date}")
        if use_real_data and self.cds_client:
            return self._retrieve_real_upper_air_data(output_path, date)
        if use_real_data:
            logger.warning("Real data requested but CDS client is not available. Falling back to synthetic.")
        return self._generate_synthetic_upper_air_data(output_path, date)

    def _retrieve_real_surface_data(self, output_path: str, date: str) -> str:
        try:
            logger.info("Retrieving real surface data from CDS: 'reanalysis-era5-single-levels'")
            self.cds_client.retrieve(
                'reanalysis-era5-single-levels',
                {
                    'product_type': 'reanalysis',
                    'variable': ['2m_temperature', '10m_u_component_of_wind', '10m_v_component_of_wind', 'mean_sea_level_pressure'],
                    'year': date[:4], 'month': date[5:7], 'day': date[8:10],
                    'time': ['00:00', '06:00', '12:00', '18:00'],
                    'area': self.config['area'], 'grid': self.config['grid'], 'format': 'netcdf',
                },
                output_path)
            logger.info(f"Successfully retrieved ERA5 surface data to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to retrieve ERA5 surface data: {e}. Falling back to synthetic generation.")
            return self._generate_synthetic_surface_data(output_path, date)

    def _retrieve_real_upper_air_data(self, output_path: str, date: str) -> str:
        try:
            logger.info("Retrieving real upper-air data from CDS: 'reanalysis-era5-pressure-levels'")
            self.cds_client.retrieve(
                'reanalysis-era5-pressure-levels',
                {
                    'product_type': 'reanalysis',
                    'variable': ['temperature', 'relative_humidity', 'u_component_of_wind', 'v_component_of_wind'],
                    'pressure_level': ['1000', '850', '700', '500', '300'],
                    'year': date[:4], 'month': date[5:7], 'day': date[8:10],
                    'time': ['00:00', '12:00'],
                    'area': self.config['area'], 'grid': self.config['grid'], 'format': 'netcdf',
                },
                output_path)
            logger.info(f"Successfully retrieved ERA5 pressure level data to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to retrieve ERA5 pressure level data: {e}. Falling back to synthetic generation.")
            return self._generate_synthetic_upper_air_data(output_path, date)

    def _generate_synthetic_surface_data(self, output_path: str, date: str) -> str:
        logger.info(f"Generating synthetic surface data with compliant time axis: {output_path}")
        with nc.Dataset(output_path, 'w', format='NETCDF4') as ds:
            lat_range = np.arange(self.config['area'][0], self.config['area'][2] - self.config['grid'][0], -self.config['grid'][0])
            lon_range = np.arange(self.config['area'][1], self.config['area'][3] + self.config['grid'][1], self.config['grid'][1])
            hours = [0, 6, 12, 18]
            
            ds.createDimension('latitude', len(lat_range)); ds.createVariable('latitude', 'f4', ('latitude',))[:] = lat_range
            ds.createDimension('longitude', len(lon_range)); ds.createVariable('longitude', 'f4', ('longitude',))[:] = lon_range
            
            # --- IMPROVEMENT: Create CF-compliant time variable ---
            ds.createDimension('time', len(hours))
            time_var = ds.createVariable('time', 'i4', ('time',))
            time_var.units = f"hours since {date} 00:00:00"
            time_var.calendar = "gregorian"
            time_var[:] = hours
            
            var_shape_names = ('time', 'latitude', 'longitude')
            var_shape_sizes = (len(hours), len(lat_range), len(lon_range))
            
            # Use real CDS variable names for better compatibility
            ds.createVariable('2t', 'f4', var_shape_names)[:] = 285 + np.random.randn(*var_shape_sizes) * 5
            ds.createVariable('msl', 'f4', var_shape_names)[:] = 101325 + np.random.randn(*var_shape_sizes) * 500
            ds.createVariable('10u', 'f4', var_shape_names)[:] = 5 + np.random.randn(*var_shape_sizes) * 3
            ds.createVariable('10v', 'f4', var_shape_names)[:] = 2 + np.random.randn(*var_shape_sizes) * 3
        return output_path

    def _generate_synthetic_upper_air_data(self, output_path: str, date: str) -> str:
        logger.info(f"Generating synthetic upper-air data with compliant time axis: {output_path}")
        with nc.Dataset(output_path, 'w', format='NETCDF4') as ds:
            lat_range = np.arange(self.config['area'][0], self.config['area'][2] - self.config['grid'][0], -self.config['grid'][0])
            lon_range = np.arange(self.config['area'][1], self.config['area'][3] + self.config['grid'][1], self.config['grid'][1])
            hours = [0, 12]
            levels = [1000, 850, 700, 500, 300]
            
            ds.createDimension('latitude', len(lat_range)); ds.createVariable('latitude', 'f4', ('latitude',))[:] = lat_range
            ds.createDimension('longitude', len(lon_range)); ds.createVariable('longitude', 'f4', ('longitude',))[:] = lon_range
            ds.createDimension('level', len(levels)); ds.createVariable('level', 'i4', ('level',))[:] = levels

            # --- IMPROVEMENT: Create CF-compliant time variable ---
            ds.createDimension('time', len(hours))
            time_var = ds.createVariable('time', 'i4', ('time',))
            time_var.units = f"hours since {date} 00:00:00"
            time_var.calendar = "gregorian"
            time_var[:] = hours

            var_shape_names = ('time', 'level', 'latitude', 'longitude')
            var_shape_sizes = (len(hours), len(levels), len(lat_range), len(lon_range))

            ds.createVariable('t', 'f4', var_shape_names)[:] = 270 + np.random.randn(*var_shape_sizes) * 10
            ds.createVariable('r', 'f4', var_shape_names)[:] = np.clip(50 + np.random.randn(*var_shape_sizes) * 20, 0, 100)
            ds.createVariable('u', 'f4', var_shape_names)[:] = 5 + np.random.randn(*var_shape_sizes) * 10
            ds.createVariable('v', 'f4', var_shape_names)[:] = 0 + np.random.randn(*var_shape_sizes) * 10
        return output_path

def main():
    parser = argparse.ArgumentParser(
        description="ECMWF ERA5 Test Data Generator. Retrieves real data from CDS or generates synthetic data.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory for the generated NetCDF files.")
    parser.add_argument("-t", "--type", choices=["surface", "upper_air", "all"], default="all", help="Type of data to generate/retrieve.")
    parser.add_argument("-d", "--date", help="Date in YYYY-MM-DD format (default: 30 days ago).")
    parser.add_argument("--real", action="store_true", help="Attempt to retrieve real ERA5 data from CDS.")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.date:
        try:
            date_to_use = datetime.strptime(args.date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            logger.error("Invalid date format. Please use YYYY-MM-DD.")
            return
    else:
        date_to_use = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
    date_str_for_filename = date_to_use.replace('-', '')
    
    generator = ECMWFTestDataGenerator()

    if args.type in ["surface", "all"]:
        outfile = output_dir / f"surface_era5_{date_str_for_filename}.nc"
        generator.retrieve_surface_data(str(outfile), date_to_use, args.real)
        print(f"Surface data file is ready: {outfile}")

    if args.type in ["upper_air", "all"]:
        outfile = output_dir / f"upper_air_era5_{date_str_for_filename}.nc"
        generator.retrieve_upper_air_data(str(outfile), date_to_use, args.real)
        print(f"Upper-air data file is ready: {outfile}")

if __name__ == "__main__":
    main()
