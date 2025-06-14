#!/usr/bin/env python3
import argparse
import sys
import yaml
import mlflow
from datetime import datetime
from pathlib import Path

# Add project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data_processor import NetCDFReader, BUFREncoder
from src.quality_control import QualityControl
from src.ml_quality_control import MLQualityControl
from utils.visualize_data import generate_comparison_plot

def main():
    parser = argparse.ArgumentParser(description="Processes NetCDF to BUFR and generates visualizations.")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format.")
    parser.add_argument("--config", required=True, help="Path to the config.yaml file.")
    args = parser.parse_args()
    
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    base_date = datetime.strptime(args.date, "%Y-%m-%d")
    date_fn_str = base_date.strftime('%Y%m%d')
    
    # Define file paths based on convention
    raw_dir = project_root / config['pipeline_paths']['raw_netcdf_dir']
    bufr_dir = project_root / config['pipeline_paths']['processed_bufr_dir']
    nc_filename = f"ecmwf-era5_{date_fn_str}_surface.nc"
    nc_filepath = raw_dir / nc_filename
    bufr_filename = f"ecmwf-era5_{date_fn_str}_surface.bufr"
    bufr_filepath = bufr_dir / bufr_filename

    if not nc_filepath.exists():
        print(f"ERROR: Input file not found: {nc_filepath}. Aborting.")
        sys.exit(1)

    # MLflow Setup
    mlflow.set_tracking_uri(f"file://{project_root / 'mlruns'}")
    mlflow.set_experiment("C3S Data Ingestion (ecFlow)")
    with mlflow.start_run(run_name=f"ingestion_{date_fn_str}") as run:
        mlflow.log_params({"run_date": args.date, "provider": "ecmwf-era5"})

        # Processing Logic
        qc = QualityControl(config['quality_control'])
        ml_qc = MLQualityControl(project_root / "models/qc_anomaly_model.joblib")
        provider_config = config['providers']['ecmwf-era5']
        
        reader = NetCDFReader(str(nc_filepath), provider_config['variable_map'], qc, base_date)
        observations, stats = reader.extract_surface_observations_with_stats(ml_qc) # Assumes method returns stats
        mlflow.log_metrics(stats)

        # BUFR Encoding
        if observations:
            encoder = BUFREncoder()
            encoder.encode(observations, str(bufr_filepath), 'surface')
            
            # Visualization
            viz_dir = project_root / config['pipeline_paths']['visualization_dir']
            viz_dir.mkdir(parents=True, exist_ok=True)
            date_title = base_date.strftime("%Y-%m-%d")
            plot_path = viz_dir / f"dashboard_{date_title}.png"
            generate_comparison_plot(str(nc_filepath), str(bufr_filepath), str(plot_path), date_title)
            mlflow.log_artifact(str(plot_path), "dashboard_plots")
        else:
            print("No valid observations found, skipping BUFR and plot generation.")

if __name__ == "__main__":
    main()