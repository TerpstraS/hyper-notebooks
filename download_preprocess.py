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

from pyesgf.logon import LogonManager

import xmip.preprocessing as xmip_pre
from xmip.postprocessing import match_metrics

# import shapely
# import warnings
# from shapely.errors import ShapelyDeprecationWarning
# warnings.filterwarnings("ignore", ccmioategory=ShapelyDeprecationWarning)


def login(OPENID, PASSWORD):
    lm = LogonManager()
    if not lm.is_logged_on():
        lm.logon_with_openid(
            OPENID, password=PASSWORD, bootstrap=True
        )

    # check if it worked
    if not lm.is_logged_on():
        raise RuntimeError("Can't login to ESGF database. Exiting...")
    return lm


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

    # get essential info from bash script as input arguments
    OPENID = sys.argv[1]
    PASSWORD = sys.argv[2]

    # connection is needed to be able to execute the wget scripts
    ## TODO: crash program if this is unsuccessful
    lm = login(OPENID, PASSWORD)
    print(lm.is_logged_on())
    experiment_id = sys.argv[3]
    variable = sys.argv[4]
    wget_var = sys.argv[5]  # this is including the whole path
    wget_var = wget_var.split("/")[-1] # we want only file name, not path

    # directory where to save the downloaded files
    DIR_DATATEMP = os.path.join("/nethome", "terps020", "cmip6", "datatemp")
    if not os.path.isdir(DIR_DATATEMP):
        os.makedirs(DIR_DATATEMP)
    DIR_WGET_SCEN = os.path.join(
        "/nethome", "terps020", "cmip6", "wget", variable, experiment_id
    )
    DIR_WGET_PICONTROL = os.path.join(
        "/nethome", "terps020", "cmip6", "wget", variable, "piControl"
    )

    # check if piControl file exists
    wget_piControl = wget_var.split(".").copy()
    wget_piControl[2] = "piControl"
    wget_piControl = ".".join(wget_piControl)
    print(wget_var, wget_piControl)
    if not os.path.isfile(os.path.join(DIR_WGET_PICONTROL, wget_piControl)):
        raise RuntimeError("No associated piControl wget script to {}".format(wget_var))

    ## WARNING: temporary only use files that are already in gr format
    ## TODO: remapping files (either here or by using cdo in bash)
    print("# WARNING: temporary only using files that are already in gr format")
    if not wget_var.endswith("gr.sh"):
        raise RuntimeError(
            "# WARNING: temporary only using files that are already in gr format"
        )

    # make sure files are executable
    wget_var_path = os.path.join(DIR_WGET_SCEN, wget_var)
    wget_piControl_path = os.path.join(DIR_WGET_PICONTROL, wget_piControl)
    os.chmod(wget_var_path, 0o750)
    os.chmod(wget_piControl_path, 0o750)
    # subprocess.check_output("bash {} -H -d {} {}".format(wget_var_path, OPENID, PASSWORD), cwd=DIR_DATATEMP)
    # subprocess.check_output("{}".format(wget_piControl_path), cwd=DIR_DATATEMP)
    subprocess.Popen([wget_var_path, "-H"], cwd=DIR_DATATEMP)
    subprocess.Popen([wget_piControl_path, "-H"], cwd=DIR_DATATEMP)

    # open files and preprocess them
    #TODO: ds_var_fname --> how to obtain this?
    ds_var_fname = find_filename(DIR_DATATEMP, experiment_id)
    ds_var_path = os.path.join(DIR_DATATEMP, ds_var_fname)
    ds_var = xr.open_dataset(ds_var_path)
    ds_var = preprocessing_wrapper(ds_var)

    # save and remove from memory to speed-up and save space
    ## TODO: make sure to save to correct file name (should be correct now)
    ds_var_fname_save = ".".join(wget_var.split(".")[:-1]) + ".nc"
    ds_var.to_netcdf(os.path.join(DIR_DATATEMP, ds_var_fname_save))
    del ds_var

    ds_piControl_fname = find_filename(DIR_DATATEMP, "piControl")
    ds_piControl_path = os.path.join(DIR_DATATEMP, ds_piControl_fname)
    ds_piControl = xr.open_dataset(ds_piControl_path)
    ds_piControl = preprocessing_wrapper(ds_piControl)

    # save and remove from memory to speed-up and save space
    ## TODO: make sure to save to correct file name (should be correct now)
    # ds_piControl_fname = "CMIP.source_id.experiment_id.member_id.table_id.variable_id.gr.nc"
    ds_piControl_fname_save = ".".join(wget_piControl.split(".")[:-1]) + ".nc"
    ds_piControl.to_netcdf(os.path.join(DIR_DATATEMP, ds_piControl_fname_save))
    del ds_piControl
