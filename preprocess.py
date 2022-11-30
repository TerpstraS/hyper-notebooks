#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By: Sjoerd Terpstra
# Created Date: 29/11/2022
# ---------------------------------------------------------------------------
""" download_esgf.py
Download climate data from wget scripts and preprocess using xmip
"""
# ---------------------------------------------------------------------------
import os
import subprocess
import sys

import xarray as xr

import xmip.preprocessing as xmip_pre
from xmip.postprocessing import match_metrics

# import shapely
# import warnings
# from shapely.errors import ShapelyDeprecationWarning
# warnings.filterwarnings("ignore", ccmioategory=ShapelyDeprecationWarning)


def preprocessing_wrapper(ds):

    # fix naming
    ds = xmip_pre.rename_cmip6(ds)

    # promote empty dims to actual coordinates
    ds = xmip_pre.promote_empty_dims(ds)

    # demote coordinates from data_variables
    ds = xmip_pre.correct_coordinates(ds)

    # broadcast lon/lat
    ds = xmip_pre.broadcast_lonlat(ds)

    # shift all lons to consistent 0-360
    ds = xmip_pre.correct_lon(ds)

    # fix the units
    ds = xmip_pre.correct_units(ds)

    # rename the `bounds` according to their style (bound or vertex)
    ds = xmip_pre.parse_lon_lat_bounds(ds)

    # sort verticies in a consistent manner
    ds = xmip_pre.sort_vertex_order(ds)

    # convert vertex into bounds and vice versa, so both are available
    ds = xmip_pre.maybe_convert_bounds_to_vertex(ds)
    ds = xmip_pre.maybe_convert_vertex_to_bounds(ds)

    ds = xmip_pre.fix_metadata(ds)
    _drop_coords = ["bnds", "vertex"]
    ds = ds.drop_vars(_drop_coords, errors="ignore")

    ds = xmip_pre.replace_x_y_nominal_lat_lon(ds)

    # put x and y values to lon and lat respectively, because hypercc expects this format
    ds.coords["lon"] = ds["x"]
    ds.coords["lat"] = ds["y"]

    return ds


def find_filename(dir, experiment_id):
    """Find file name for given experiment_id in dir (assumes only one file for each
    scenario/experiment_id) --> works only in connection with edge_cmip6.sh workflow.
    """
    for file in os.listdir(os.fsencode(dir)):
        fname_in_dir = os.fsdecode(file)
        if experiment_id in fname_in_dir:
            if fname_in_dir.endswith(".sh"):
                return fname_in_dir
    else:
        raise FileNotFoundError(
            f"Could not found file for experiment_id: {experiment_id}..."
        )


if __name__ == '__main__':

    experiment_id = sys.argv[1]
    variable = sys.argv[2]

    # directory where to save the downloaded files
    DIR_DATATEMP = os.path.join("/nethome", "terps020", "cmip6", "datatemp")
    if not os.path.isdir(DIR_DATATEMP):
        os.makedirs(DIR_DATATEMP)

    # open files and preprocess them
    #TODO: ds_var_fname --> how to obtain this?
    ds_var_fname = find_filename(DIR_DATATEMP, experiment_id)
    ds_var_path = os.path.join(DIR_DATATEMP, ds_var_fname)
    ds_var = xr.open_dataset(ds_var_path)
    ds_var = preprocessing_wrapper(ds_var)

    ## TODO: Concatenate files if necessary

    # save and remove from memory to speed-up and save space
    ## TODO: make sure to save to correct file name (should be correct now)
    ds_var_fname_save = ".".join(wget_var.split(".")[:-1]) + ".nc"
    ds_var.to_netcdf(os.path.join(DIR_DATATEMP, ds_var_fname_save))
    del ds_var

    ds_piControl_fname = find_filename(DIR_DATATEMP, "piControl")
    ds_piControl_path = os.path.join(DIR_DATATEMP, ds_piControl_fname)
    ds_piControl = xr.open_dataset(ds_piControl_path)
    ds_piControl = preprocessing_wrapper(ds_piControl)

    ## TODO: Concatenate files if necessary

    # save and remove from memory to speed-up and save space
    ## TODO: make sure to save to correct file name (should be correct now)
    # ds_piControl_fname = "CMIP.source_id.experiment_id.member_id.table_id.variable_id.gr.nc"
    ds_piControl_fname_save = ".".join(wget_piControl.split(".")[:-1]) + ".nc"
    ds_piControl.to_netcdf(os.path.join(DIR_DATATEMP, ds_piControl_fname_save))
    del ds_piControl
