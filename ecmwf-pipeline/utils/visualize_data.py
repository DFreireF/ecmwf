#!/usr/bin/env python3
"""
ECMWF Workflow Enhanced Visualization Tool

Generates a single, comprehensive 4-panel dashboard plot comparing
the input NetCDF grid with the processed point data from the output BUFR file.
"""
import logging
import argparse
from pathlib import Path
import numpy as np
import netCDF4 as nc
import eccodes as ec

# Use a non-interactive backend for saving files without a GUI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    CARTOPY_AVAILABLE = True
except ImportError:
    CARTOPY_AVAILABLE = False
    logging.warning("Cartopy library not found. Map plotting will be disabled.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_comparison_plot(netcdf_path: str, bufr_path: str, output_path: str, date_str: str):
    """
    Creates and saves a 4-panel plot for a side-by-side comparison of
    input gridded data and output point data.
    """
    if not CARTOPY_AVAILABLE:
        logger.error("Cannot generate plots: The 'cartopy' library is required.")
        return

    fig, axes = plt.subplots(
        2, 2,
        figsize=(20, 16),
        subplot_kw={'projection': ccrs.PlateCarree()},
        constrained_layout=True
    )
    fig.suptitle(f'Data Processing Dashboard for {date_str}', fontsize=24, weight='bold')

    # --- 1. Plot Input Gridded Data (Left Column) ---
    plot_input_grids(axes[:, 0], netcdf_path)

    # --- 2. Plot Output Point Data (Right Column) ---
    plot_output_points(axes[:, 1], bufr_path)

    logger.info(f"Saving comparison dashboard to {output_path}")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

def plot_input_grids(axes, netcdf_path):
    """Plots temperature, pressure, and wind from the source NetCDF onto two axes."""
    ax1, ax2 = axes
    logger.info(f"Visualizing input grids from {netcdf_path}")

    try:
        with nc.Dataset(netcdf_path, 'r') as ds:
            # Take the first time step for visualization
            t2m = ds.variables['t2m'][0, :, :]
            msl = ds.variables['msl'][0, :, :]
            u10 = ds.variables['u10'][0, :, :]
            v10 = ds.variables['v10'][0, :, :]
            lats = ds.variables['latitude'][:]
            lons = ds.variables['longitude'][:]
            lon_grid, lat_grid = np.meshgrid(lons, lats)

        # Plot 1: Input Air Temperature
        ax1.set_title("Input: Gridded 2m Temperature (K)", fontsize=14)
        mesh = ax1.pcolormesh(lon_grid, lat_grid, t2m, cmap='coolwarm', transform=ccrs.PlateCarree())
        plt.colorbar(mesh, ax=ax1, orientation='horizontal', pad=0.1, label='Temperature (K)')

        # Plot 2: Input Pressure and Wind
        ax2.set_title("Input: MSL Pressure (Pa) and 10m Wind", fontsize=14)
        mesh2 = ax2.pcolormesh(lon_grid, lat_grid, msl, cmap='viridis', transform=ccrs.PlateCarree())
        plt.colorbar(mesh2, ax=ax2, orientation='horizontal', pad=0.1, label='Mean Sea Level Pressure (Pa)')

        # Subsample wind data for a cleaner plot
        skip = max(1, len(lons) // 25) # Aim for ~25 arrows across
        q = ax2.quiver(lon_grid[::skip, ::skip], lat_grid[::skip, ::skip],
                       u10[::skip, ::skip], v10[::skip, ::skip],
                       transform=ccrs.PlateCarree(), color='white', scale=250)
        ax2.quiverkey(q, X=0.85, Y=1.05, U=20, label='20 m/s', labelpos='E', fontproperties={'size': 10})

        for ax in [ax1, ax2]:
            ax.add_feature(cfeature.COASTLINE)
            ax.add_feature(cfeature.BORDERS, linestyle=':')
            ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')

    except Exception as e:
        logger.error(f"Failed to plot input NetCDF data: {e}", exc_info=True)
        ax1.set_title("ERROR: Could not load input data", color='red')
        ax2.set_title("ERROR: Could not load input data", color='red')


def plot_output_points(axes, bufr_path):
    """Plots BUFR observation locations and temperature values."""
    ax1, ax2 = axes
    logger.info(f"Visualizing output points from {bufr_path}")

    lats, lons, temps, pressures = [], [], [], []
    try:
        with open(bufr_path, 'rb') as f:
            while True:
                bufr = ec.codes_bufr_new_from_file(f)
                if bufr is None: break
                
                ec.codes_set(bufr, 'unpack', 1)
                # Not all messages have all keys, so read safely
                try:
                    lats.append(ec.codes_get(bufr, '#1#latitude'))
                    lons.append(ec.codes_get(bufr, '#1#longitude'))
                    temps.append(ec.codes_get(bufr, '#1#airTemperature'))
                    pressures.append(ec.codes_get(bufr, '#1#nonCoordinatePressure'))
                except ec.CodesInternalError:
                    pass # Ignore messages missing one of these keys
                finally:
                    ec.codes_release(bufr)
    except Exception as e:
         logger.error(f"Failed to read BUFR file {bufr_path}: {e}")

    if not lats:
        logger.warning("No valid data points found in BUFR file to plot.")
        ax1.set_title("Output: No BUFR data found", color='orange')
        ax2.set_title("Output: No BUFR data found", color='orange')
        for ax in [ax1, ax2]: ax.add_feature(cfeature.COASTLINE) # Still draw map
        return

    # Plot 1: Processed Temperature at Observation Locations
    ax1.set_title(f"Output: Processed Temperature ({len(temps)} points)", fontsize=14)
    sc = ax1.scatter(lons, lats, c=temps, cmap='coolwarm', s=5, transform=ccrs.PlateCarree(), vmin=np.min(temps), vmax=np.max(temps))
    plt.colorbar(sc, ax=ax1, orientation='horizontal', pad=0.1, label='Temperature (K)')

    # Plot 2: Observation Locations (Sanity Check)
    ax2.set_title(f"Output: Observation Locations ({len(lats)} points)", fontsize=14)
    ax2.scatter(lons, lats, color='dodgerblue', s=3, transform=ccrs.PlateCarree(), label='Observation Point')
    ax2.legend(loc='upper right')

    for ax in [ax1, ax2]:
        ax.set_global()
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')


def main():
    parser = argparse.ArgumentParser(description="ECMWF Workflow Enhanced Visualization Tool")
    parser.add_argument('--netcdf_file', required=True, help='Path to the input NetCDF file')
    parser.add_argument('--bufr_file', required=True, help='Path to the output BUFR file')
    parser.add_argument('--output_dir', required=True, help='Directory to save the plot dashboard')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Extract date from filename for the plot title, e.g., ecmwf-era5_20250603_surface.nc -> 2025-06-03
    try:
        date_str_iso = Path(args.netcdf_file).stem.split('_')[1]
        date_title = f"{date_str_iso[0:4]}-{date_str_iso[4:6]}-{date_str_iso[6:8]}"
    except IndexError:
        date_title = "Unknown Date"
        
    output_file = output_dir / f"dashboard_{date_title}.png"
    
    generate_comparison_plot(args.netcdf_file, args.bufr_file, str(output_file), date_title)


if __name__ == '__main__':
    main()