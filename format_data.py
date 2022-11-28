import os
import xarray as xr


DIR_DATA = os.path.join("/nethome", "terps020", "cmip6", "data")

fname = os.path.join(DIR_DATA, "CMIP.GFDL-ESM4.1pctCO2.r1i1p1f1.SImon.siconc.gr.nc")
ds_disk = xr.open_dataset(fname)
ds_disk["lat"] = ds_disk.y
ds_disk["lon"] = ds_disk.x
fname = os.path.join(DIR_DATA, "CMIP.GFDL-ESM4.1pctCO2.r1i1p1f1.SImon.siconc.gr.nc")
ds_disk.to_netcdf(os.path.join(DIR_DATA, fname))
del ds_disk


fname = os.path.join(DIR_DATA, "CMIP.GFDL-ESM4.piControl.r1i1p1f1.SImon.siconc.gr.nc")
ds_disk = xr.open_dataset(fname)
ds_disk["lat"] = ds_disk.y
ds_disk["lon"] = ds_disk.x
fname = os.path.join(DIR_DATA, "CMIP.GFDL-ESM4.piControl.r1i1p1f1.SImon.siconc.gr.nc")
ds_disk.to_netcdf(os.path.join(DIR_DATA, fname))
del ds_disk
