#!/usr/bin/env python3
"""
ECMWF Workflow Visualization Tool

This script provides functions to visualize the input NetCDF data and the
output BUFR data. It correctly unpacks BUFR messages to read their contents.
"""
import logging
import argparse
from pathlib import Path
import numpy as np
import netCDF4 as nc
import eccodes as ec

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    CARTOPY_AVAILABLE = True
except ImportError:
    CARTOPY_AVAILABLE = False
    logging.warning("Cartopy library not found. Map plotting is disabled.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def plot_input_netcdf(filepath: str, output_path: str):
    if not CARTOPY_AVAILABLE:
        logger.warning("Cannot plot input map: Cartopy is not installed.")
        return

    logger.info(f"Visualizing input NetCDF file: {filepath}")
    with nc.Dataset(filepath, 'r') as ds:
        main_var_name = 't2m' if 't2m' in ds.variables else 't'
        lats = ds.variables['latitude'][:]
        lons = ds.variables['longitude'][:]
        var_data = ds.variables[main_var_name]
        
        data_slice = var_data[0, :, :] if len(var_data.shape) == 3 else var_data[0, 0, :, :]
        
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        mesh = ax.pcolormesh(lons, lats, data_slice, transform=ccrs.PlateCarree(), cmap='viridis')
        ax.add_feature(cfeature.COASTLINE); ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.gridlines(draw_labels=True)
        units_label = f"({var_data.units})" if hasattr(var_data, 'units') else "(units not specified)"
        plt.colorbar(mesh, ax=ax, orientation='vertical', label=f'{main_var_name} {units_label}')
        ax.set_title(f'Input Data from {Path(filepath).name}\n(First Time Step)')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Input data map saved to: {output_path}")
        plt.close(fig)

def plot_output_bufr(filepath: str, output_path: str):
    if not CARTOPY_AVAILABLE:
        logger.warning("Cannot plot output map: Cartopy is not installed.")
        return
        
    logger.info(f"Visualizing output BUFR file: {filepath}")
    lats, lons = [], []
    msg_count = valid_points = 0

    with open(filepath, 'rb') as f:
        while True:
            # 1) grab the handle (or EOF)
            try:
                bufr = ec.codes_bufr_new_from_file(f)
            except ec.CodesInternalError:
                # true EOF for this API
                break

            if bufr is None:
                # some bindings return None at EOF instead of raising
                break

            msg_count += 1
            try:
                # unpack and read array keys
                ec.codes_set(bufr, 'unpack', 1)

                try:
                    lat_arr = ec.codes_get_array(bufr, 'latitude')
                    lon_arr = ec.codes_get_array(bufr, 'longitude')
                except ec.CodesInternalError:
                    # fallback station keys
                    lat_arr = ec.codes_get_array(bufr, 'stationLatitude')
                    lon_arr = ec.codes_get_array(bufr, 'stationLongitude')

                for lat, lon in zip(lat_arr, lon_arr):
                    if np.isfinite(lat) and np.isfinite(lon):
                        lats.append(lat)
                        lons.append(lon)
                        valid_points += 1

            except Exception as e:
                logger.debug(f"Skipping message #{msg_count}: {e}")

            finally:
                # only release if we got a real handle
                ec.codes_release(bufr)

    logger.info(f"Processed {msg_count} messages, found {valid_points} valid locations")
    if not lats:
        logger.warning("No valid locations found – skipping plot.")
        return

    fig = plt.figure(figsize=(12, 8))
    ax  = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.scatter(lons, lats,
               marker='.', s=10,
               transform=ccrs.PlateCarree(),
               label='BUFR Obs')
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.gridlines(draw_labels=True)
    ax.legend()
    ax.set_global()
    ax.set_title(
        f'BUFR observation locations\n'
        f'({valid_points} points from {msg_count} messages)'
    )
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Output data map saved to: {output_path}")
    plt.close(fig)



def main():
    parser = argparse.ArgumentParser(description="ECMWF Workflow Visualization Tool")
    parser.add_argument('--netcdf_file', required=True, help='Path to the input NetCDF file')
    parser.add_argument('--bufr_file', required=True, help='Path to the output BUFR file')
    parser.add_argument('--output_dir', required=True, help='Directory to save the plots')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    plot_input_netcdf(args.netcdf_file, str(output_dir / 'input_data_map.png'))
    plot_output_bufr(args.bufr_file, str(output_dir / 'output_locations_map.png'))

if __name__ == '__main__':
    main()
