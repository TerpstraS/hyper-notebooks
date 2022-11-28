import os
from timeit import default_timer as timer

import dask
import intake
import xarray as xr
xr.set_options(display_style='html')

import xmip.preprocessing as xmip_pre
from xmip.postprocessing import match_metrics

# import shapely
# import warnings
# from shapely.errors import ShapelyDeprecationWarning
# warnings.filterwarnings("ignore", ccmioategory=ShapelyDeprecationWarning)

# directory where to save the downloaded files
DIR_DATA = os.path.join("/nethome", "terps020", "cmip6", "data")

# URL of cmip6 catalogue
CAT_URL = "https://storage.googleapis.com/cmip6/pangeo-cmip6.json"


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


def build_query(scen, var, realm, model=None, freq="Amon", member_id=None):
    query_var = dict(
        experiment_id=scen, variable_id=var, source_id=model, member_id=member_id,
        table_id=freq
    )

    query_piControl = dict(
        experiment_id=scen, variable_id="piControl", source_id=model, member_id=member_id,
        table_id=freq
    )

    # if realm is not atmosphere, we need to mask the data
    if realm != "atmos":
        query_mask = dict(
            experiment_id=scen, variable_id="sftlf", source_id=model
        )
        return query_var, query_piControl, query_mask
    else:
        return query_var, query_piControl, None


def retrieve_data_sets(search_var, search_piControl, search_mask=None, kwargs=None):
    if kwargs is None:
        kwargs = {
            "xarray_open_kwargs":{
                "consolidated": True,
                "decode_times": True,
                "use_cftime": True
            },
            "aggregate": False,
            "progressbar": True,
            "skip_on_error": False,
            "preprocess": preprocessing_wrapper
        }

    with dask.config.set(**{"array.slicing.split_large_chunks": True}):
        dset_var = search_var.to_dataset_dict(**kwargs)
    with dask.config.set(**{"array.slicing.split_large_chunks": True}):
        dset_piControl = search_piControl.to_dataset_dict(**kwargs)
    if search_mask is not None:
        with dask.config.set(**{"array.slicing.split_large_chunks": True}):
            dset_mask = search_mask.to_dataset_dict(**kwargs)
        return dset_var, dset_piControl, dset_mask
    else:
        return dset_var, dset_piControl, None


def search_query(cat, query_var, query_piControl, query_mask=None):
    search_var = cat.search(**query_var)
    if search_var.df.size == 0:
        print(f"No result found for search:\{query_var}")
        raise FileNotFoundError("Search result not found.")

    search_piControl = cat.search(**query_piControl)
    if search_piControl.df.size == 0:
        print(f"No result found for search:\{query_piControl}")
        raise FileNotFoundError("Search result not found.")

    if query_mask is not None:
        search_mask = cat.search(**query_mask)
        if search_mask.df.size == 0:
            print(f"No result found for search:\{query_mask}")
            raise FileNotFoundError("Search result not found.")
        return search_var, search_piControl, search_mask
    else:
        return search_var, search_piControl, None


if __name__ == '__main__':

    scen = "1pctCO2"
    var = "tas"
    realm = "atmos"
    model = None

    cat = intake.open_esm_datastore(cat_url)

    query = build_query(scen, var, realm, model=model)
    search_result = search_query(cat, *query)
    dset = retrieve_data_sets(*search_result)
