#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By: Sjoerd Terpstra
# Created Date: 21/11/2022
# ---------------------------------------------------------------------------
""" analysis_cmip6.py

Use edge detection to analysis a single cmip6 simulation (already downloaded)
"""
# ---------------------------------------------------------------------------
from datetime import date, timedelta
import os
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.colors as colors

import netCDF4
from scipy import ndimage, stats
import xarray as xr

from hyper_canny import cp_edge_thinning, cp_double_threshold

from hypercc.data.box import Box
from hypercc.data.data_set import DataSet
from hypercc.units import unit
from hypercc.plotting import (
    plot_mollweide, plot_orthographic_np, plot_plate_carree, earth_plot,
    plot_signal_histogram)
from hypercc.filters import (taper_masked_area, gaussian_filter, sobel_filter)
from hypercc.calibration import (calibrate_sobel)

DIR_DATA = os.path.join("/nethome", "terps020", "cmip6", "data")


def maybe_convert_lon_lat(fname):
    """Assume that if fname starts with 'converted', lon and lat are already converted
    to correct format

    Args:
        fname (str): fname without path specified

    Returns:
        fpath, fname (tuple): absolute path to file and file name
    """
    fpath = os.path.join(DIR_DATA, fname)
    if fname.startswith("converted"):
        return fpath, fname
    ds_disk = xr.open_dataset(fpath)
    ds_disk["lat"] = ds_disk.y
    ds_disk["lon"] = ds_disk.x
    fname = ".".join(["converted", fname])
    fpath = os.path.join(
        DIR_DATA,
        "converted.CMIP.NOAA-GFDL.GFDL-ESM4.piControl.r1i1p1f1.SImon.siconc.gr.nc"
    )
    ds_disk.to_netcdf(fpath)
    return fpath, fname


if __name__ == '__main__':
    variable = "siconc"      # variable from CMIP6
    model = "GFDL-ESM4"      # CMIP6 model
    month = 13
    fname = "CMIP.NOAA-GFDL.GFDL-ESM4.piControl.r1i1p1f1.SImon.siconc.gr.nc"
    fpath, fname = maybe_convert_lon_lat(fname)
    print("Using {}\n".format(fname))

    # download dataset (check how the [month-1::12] selection exactly works)
    data_set = DataSet.cmip6(
        path=Path(fpath),
        variable=variable
    )

    print(data_set)

    data_set = data_set[month-1::12]

    data = data_set.files[0].data

    for name, variable in data.variables.items():
        for attrname in variable.ncattrs():
            print("{} -- {}".format(attrname, getattr(variable, attrname)))

    box = data_set.box
    print(box)

    if not box.rectangular:
        print("box not rectangular")

    exit(0)

    # calibration of the aspect ratio is based on which quartile of the gradients
    # for climate models, use 3, for idealised test cases, use 4
    quartile_calibration=3

    # which month should be selected for the yearly time series (1-12; 13 is annual mean)
    month = 13

    ## smoothing scales
    sigma_d = unit('100 km')     # space
    sigma_t = unit('10 year')    # time

    # create box
    box = data_set.box
    print("({:.6~P}, {:.6~P}, {:.6~P}) per pixel".format(*box.resolution))
    for t in box.time[:3]:

        # there is a problem with timedelta() and np.int64.
        # Convert t to int to solve this issue for now
        print("# WARNING: converting to int...")
        t = int(t)
        print(box.date(t), end=', ')
    print(" ...")

    dt = box.time[1:] - box.time[:-1]
    print("time steps: max", dt.max(), "min", dt.min())

    # check if box is rectangular
    if not box.rectangular:
        print("Box is not rectangular. Stopping program...")
        exit(-1)

    # smooth over continental boundaries (only spatial, not time dimension)
    data = data_set.data
    print(data)
    taper_masked_area(data, [0, 5, 5], 50)

    # smoothing is not applied in time, 5 grid boxes wide in space (lat and lon),
    # iteration: 50 times
    smooth_data = gaussian_filter(box, data, [sigma_t, sigma_d, sigma_d])

    # Careful! Not calibrated!
    # scaling_factor is the aspect ratio between space and time
    # Here it is initialised as 1, but will be calibrated automatically later
    print("# WARNING: scaling_factor for Sobel operator is not calibrated...")
    scaling_factor = unit('30 km/year')
    sobel_delta_t = unit('10 year')                    # time scale
    sobel_delta_d = sobel_delta_t * scaling_factor    # length scale
    sobel_weights = [sobel_delta_t, sobel_delta_d, sobel_delta_d]

    sb = sobel_filter(box, smooth_data, weight=sobel_weights)
    pixel_sb = sobel_filter(box, smooth_data, physical=False)
    pixel_sb[3] = sb[3]

    # Careful! Not calibrated!
    print("# WARNING: hysteresis thresholds are not calibrated...")
    upper_threshold = 0.6
    lower_threshold = 0.3

    # use directions of pixel based sobel transform and magnitudes from calibrated physical sobel.
    dat = pixel_sb.transpose([3,2,1,0]).copy()
    mask = cp_edge_thinning(dat)
    thinned = mask.transpose([2, 1, 0])
    dat = sb.transpose([3,2,1,0]).copy()

    thinned *= ~data.mask
    thinned[:10] = 0
    thinned[-10:] = 0

    ## edge thinning
    edges = cp_double_threshold(data=dat, mask=thinned.transpose([2,1,0]), a=1/upper_threshold, b=1/lower_threshold)
    m = edges.transpose([2, 1, 0])

    ## a first look at the data (first time step)
    plot_mollweide(box, data_set.data[0])
    plot_orthographic_np(box, data_set.data[0])

    ## define colour scale for plotting with white where variable is 0
    my_cmap = matplotlib.cm.get_cmap('rainbow')
    matplotlib.rcParams['figure.figsize'] = (25,10)
    my_cmap.set_under('w')

    ## count how many separate edges can be distinguished
    # Here, result is one large event in the Arctic Ocean
    # This occurs because it is the same sea ice edge that shifts in space over time.
    labels, n_features = ndimage.label(m, ndimage.generate_binary_structure(3, 3))
    print(n_features)
    big_enough = [x for x in range(1, n_features+1) if (labels==x).sum() > 100]
    print(big_enough)
    labels = np.where(np.isin(labels, big_enough), labels, 0)

    #plot_plate_carree(yearly_box, labels.max(axis=0), cmap=my_cmap, vmin=0.1)
    plot_orthographic_np(yearly_box, labels.max(axis=0), cmap=my_cmap, vmin=0.1)

    ## event count plot: how many years are part of the edge at each grid cell
    #plot_plate_carree(yearly_box, np.sum(m, axis=0), cmap=my_cmap, vmin=0.1)
    plot_orthographic_np(yearly_box, np.sum(m, axis=0), cmap=my_cmap, vmin=0.1)
    #
    # ## calculate maximum excess time gradient at each grid cell (i.e. gradient after removing the mean trend)
    # tgrad=sb[0]/sb[3]
    # maxm=np.nanmax(m, axis=0)
    #
    # tgrad_residual = tgrad - np.mean(tgrad, axis=0)   # remove time mean
    # maxTgrad = np.max(abs(tgrad_residual), axis=0)    # maximum of time gradient
    # maxTgrad = maxTgrad * maxm
    #
    # #plot_plate_carree(box, maxTgrad, cmap=my_cmap, vmin=1e-30)
    # plot_orthographic_np(box, maxTgrad, cmap=my_cmap, vmin=1e-30)
    #
    # cutoff_length=2       # how many years to either side of the abrupt shift are cut off (the index of the event itself is always cut off)
    # chunk_max_length=30   # maximum length of chunk of time series to either side of the event
    # chunk_min_length=15   # minimum length of these chunks
    #
    # years = np.array([d.year for d in box.dates])
    # edges = cp_double_threshold(data=dat, mask=thinned.transpose([2,1,0]), a=1/upper_threshold, b=1/lower_threshold)
    # m = edges.transpose([2, 1, 0])
    # idx = np.where(m)
    # indices=np.asarray(idx)
    # abruptness3d=m*0.0
    #
    # shapeidx=np.shape(idx)
    # nofresults=shapeidx[1]
    #
    # for result in range(nofresults):
    #     [dim0,dim1,dim2]=indices[:,result]
    #
    #     if m[dim0, dim1, dim2] == 1:
    #         index=dim0
    #         chunk1_data=data[0:index-cutoff_length,dim1,dim2]
    #         chunk2_data=data[index+cutoff_length+1:,dim1,dim2]
    #         chunk1_years=years[0:index-cutoff_length]
    #         chunk2_years=years[index+cutoff_length+1:]
    #
    #         if size(chunk1_data) > chunk_max_length:
    #             chunk1_start=size(chunk1_data)-chunk_max_length
    #         else:
    #             chunk1_start=0
    #         if size(chunk2_data) > chunk_max_length:
    #             chunk2_end=chunk_max_length
    #         else:
    #             chunk2_end=size(chunk2_data)
    #
    #         chunk1_data_short=chunk1_data[chunk1_start:]
    #         chunk2_data_short=chunk2_data[0:chunk2_end]
    #
    #         N1=size(chunk1_data_short)
    #         N2=size(chunk2_data_short)
    #
    #         if not ((N1 < chunk_min_length) or (N2 < chunk_min_length)):
    #             chunk1_years_short=chunk1_years[chunk1_start:]-years[dim0]
    #             chunk2_years_short=chunk2_years[0:chunk2_end]-years[dim0]
    #
    #             slope_chunk1, intercept_chunk1, r_value, p_value, std_err = stats.linregress(chunk1_years_short, chunk1_data_short)
    #             chunk1_regline=intercept_chunk1 + slope_chunk1*chunk1_years_short
    #
    #             slope_chunk2, intercept_chunk2, r_value, p_value, std_err = stats.linregress(chunk2_years_short, chunk2_data_short)
    #             chunk2_regline=intercept_chunk2 + slope_chunk2*chunk2_years_short
    #
    #             mean_std=(np.nanstd(chunk1_data_short)+np.nanstd(chunk2_data_short))/2
    #             abruptness3d[dim0,dim1,dim2]=abs(intercept_chunk1-intercept_chunk2)/mean_std
    #
    # abruptness = np.max(abruptness3d,axis=0)
    #
    # # map of the maximum abruptness at each point
    # #plot_plate_carree(box, abruptness, cmap=my_cmap, vmin=1e-30)
    # plot_orthographic_np(box, abruptness, cmap=my_cmap, vmin=1e-30)
    #
    # ## year in which the maximum of abruptness occurs at each point
    # idx = np.where(m)
    # indices=np.asarray(idx)
    #
    # mask_max=m*0
    #
    # shapeidx=np.shape(idx)
    # nofresults=shapeidx[1]
    #
    # # mask_max is like m but only shows the time points with the maximum abruptness at each grid cell
    # for result in range(nofresults):
    #     [dim0,dim1,dim2]=indices[:,result]
    #     if ( abruptness3d[dim0, dim1, dim2] == abruptness[dim1,dim2]) and abruptness[dim1,dim2] > 0:
    #         mask_max[dim0, dim1, dim2] = 1
    #
    #
    # years_maxpeak=(years[:,None,None]*mask_max).sum(axis=0)
    #
    # minval = np.min(years_maxpeak[np.nonzero(years_maxpeak)])
    # maxval= np.max(years_maxpeak)
    # #plot_plate_carree(yearly_box, years_maxpeak,  cmap=my_cmap, vmin=minval, vmax=maxval) #, vmin=2000, vmax=2200)
    # plot_orthographic_np(yearly_box, years_maxpeak,  cmap=my_cmap, vmin=minval, vmax=maxval)
    #
    # ## Show (part of) the time series of the original data at the grid cell with the largest abruptness
    # # red: original data
    # # blue: smoothed data (in space and time)
    # # red vertical dashed line: identification of the position of the edge in time (based on smoothed data)
    #
    # lonind=np.nanargmax(np.nanmax(abruptness, axis=0))
    # latind=np.nanargmax(np.nanmax(abruptness, axis=1))
    #
    # tindex_ini=0
    # tindex_fin=2200-2006
    # years_window=years[tindex_ini:tindex_fin]
    #
    # ts=data[tindex_ini:tindex_fin,latind,lonind]
    # abruptness_max=abruptness[latind,lonind]
    # ts_smooth=smooth_data[tindex_ini:tindex_fin,latind,lonind]
    # fig = plt.figure()
    # ax = fig.add_subplot(111)
    # ax.plot(years_window, ts, 'k', years_window, ts_smooth, 'b--')
    #
    # ## determine year of abrupt shift
    # index=np.where(abruptness3d[:,latind,lonind]==abruptness_max)
    #
    # ax.axvline(x=years_window[index], ymin=0, ymax=1, color='r', linestyle="--")
    #
    # plt.ylabel('Sea-ice concentration (%)')
    # plt.xlabel('Time [year]')
    # matplotlib.rc('xtick', labelsize=20)
    # matplotlib.rc('ytick', labelsize=20)
    #
    # ax.tick_params(axis='both', which='major', labelsize=26)
    #
    # ymin=min(ts)
    # ymax=max(ts)
    # xmin=min(years_window)
    # xmax=max(years_window)
    # xrange=xmax-xmin
    # yrange=ymax-ymin
    # frac=0.025
    # ypos=ymax-0.025*yrange
    # xpos=xmin+0.01*xrange
    # ax.text(xpos,ypos,'abruptness: '+ '{:f}'.format(abruptness_max),color='r', size=30)
