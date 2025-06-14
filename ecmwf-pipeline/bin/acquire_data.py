#!/usr/bin/env python3
import argparse
import sys
import yaml
from datetime import datetime
from pathlib import Path

# Add project root to sys.path to allow importing from 'src' and 'utils'
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.ecmwf_data_retrieval import ECMWFDataGenerator

def main():
    parser = argparse.ArgumentParser(description="Acquires data for a specific date.")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format.")
    parser.add_argument("--config", required=True, help="Path to the config.yaml file.")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    use_real_data = config.get('retrieval_mode', 'synthetic') == 'real'
    raw_dir = project_root / config['pipeline_paths']['raw_netcdf_dir']
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    date_dt = datetime.strptime(args.date, "%Y-%m-%d")
    nc_filename = f"ecmwf-era5_{date_dt.strftime('%Y%m%d')}_surface.nc"
    nc_filepath = raw_dir / nc_filename
    
    print(f"--- ACQUIRE TASK: Starting Data Acquisition for {args.date} ---")
    data_generator = ECMWFDataGenerator(use_real_data=use_real_data)
    data_generator.retrieve_surface_data(nc_filepath, args.date)
    print("--- ACQUIRE TASK: Finished ---")

if __name__ == "__main__":
    main()