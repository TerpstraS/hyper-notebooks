#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By: Sjoerd Terpstra
# Created Date: 29/11/2022
# ---------------------------------------------------------------------------
""" download_esgf.py
Download climate data wget scripts using esgf-pyclient
"""
# ---------------------------------------------------------------------------
import os
import sys

from pyesgf.logon import LogonManager
from pyesgf.search import SearchConnection

DIR_WGET = os.path.join("/nethome", "terps020", "cmip6", "wget")
URL_NODES = [
    "https://esgf-data.dkrz.de/esg-search",
    "https://esgf-node.llnl.gov/esg-search"
]


def download_wget(file_ctx, facets, dir=DIR_WGET, override=False, verbose=False):
    """Dowload single wget script for a given result

    Based on
    https://esgf-pyclient.readthedocs.io/en/latest/notebooks/examples/download.html

    Args:
        file_ctx [file_context]: file_context of single search result
    Optional:
        override [boolean]: whether already downloaded files will be dowloaded again

    Returns:
        success [boolean]: whether dowload was successful
    """

    # obtain file name with all the important descriptors in the name, i.e.
    # CMIP.model.scenario.member_id.table_id.variable_id.grid_label, e.g.
    # "CMIP.CAMS-CSM1-0.1pctCO2.r1i1p1f1.Amon.tas.gn"
    fname = list(file_ctx.facet_constraints.items())[0][1].split(".")
    ind = [1, 3, 4, 5, 6, 7, 8]
    fname = [fname[i] for i in ind]
    fname = ".".join(fname)

    freq = fname.split(".")[4]
    freq_list = [
        "Amon", "SImon", "0mon", "AERmon", "AERmonZ", "CFmon", "Emon", "EmonZ",
        "ImonAnt", "ImonGre"
    ]
    if freq not in freq_list:
        if verbose:
            print(f"{fname} has incorrect frequency")
        return True

    # check if wget script for this exact simulation already exists for another grid
    # grid_label = list(file_ctx._SearchContext__facet_counts["grid_label"].keys())[0]
    for file in os.listdir(os.fsencode(dir)):
        fname_dir = os.fsdecode(file)
        # remove .sh extension and grid_label
        if fname_dir.split(".")[:-2] == fname:
            # check which one has better grid
            if fname_dir.split(".")[-2] == "gr":
                return True
            elif fname.split(".")[-1] == "gr":
                break
            else:
                if fname_dir.split(".")[-2] == "gn":
                    return True
                else:
                    break

    # add .sh extension to file name
    if not fname.endswith(".sh"):
        fname = fname + ".sh"

    script_path = os.path.join(dir, fname)

    # check if wget script already exists to prevent unnecessarily dowloading it again,
    # unless override=True: then the file will be downloaded again
    if os.path.isfile(script_path) and not override:
        if verbose:
            print(f"{fname} already downloaded, skipping...")
        return True

    wget_script_content = file_ctx.get_download_script(facets=facets)

    # create file to save the wget script as .sh executable
    with open(script_path, "w") as writer:
        writer.write(wget_script_content)

    # make wget script executable
    os.chmod(script_path, 0o750)

    if verbose:
        print(f"Succesfully downloaded wget script: {fname}")
    return True


def list_downloaded_wget(dir=DIR_WGET, path=False):
    """Return a list of all wget files in a given directory

    Args:
    Optional:
        dir [string]: path to directory containing wget files
        path [boolean]: whether to return the file name or the whole (absolute) path
    Returns:
        files [np array]: list of all wget files in directory
    """
    files = []
    for file in os.listdir(dir):
        if file.endswith(".sh"):
            if path:
                files.append(os.path.join(dir, file))
            else:
                files.append(file)
    return files


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


def print_downloaded_wget(dir=DIR_WGET, path=False):
    """Prints and returns a list of all wget files in a given directory

    Args:
    Optional:
        dir [string]: path to directory containing wget files
        path [boolean]: whether to return the file name or the whole (absolute) path
    Returns:
        files [np array]: list of all wget files in directory
    """
    files = list_downloaded_wget(dir=dir, path=path)
    if files:
        print(f"Found the following wget scripts in {dir}:")
        for file in files:
            print(file)
        print("")
    else:
        print(f"No wget scripts found in {dir}.\n")
    return files


def search_and_download_wget(ctx, facets, override=False, verbose=False):
    """Perform search of selected DatasetSearchContext ctx and download
    wget scripts for all search results

    Args:
        DatasetSearchContext object from pyesgf
    Optional:
        override [boolean]: whether already downloaded files will be dowloaded again
    """
    # perform search based on criteria
    results = ctx.search()

    # get wget script for all results
    number_downloads_failed = 0
    n_results = 0
    for i, result in enumerate(results):
        file_ctx = result.file_context()
        success = download_wget(file_ctx, facets, override=override, verbose=verbose)
        if not success:
            number_downloads_failed += 1
        n_results += 1

    print(f"{number_downloads_failed} out of {n_results} failed.\n")


if __name__ == '__main__':

    # model="GFDL-ESM4"
    # scen="1pctCO2"
    # var="siconc"
    # rea="r1i1p1f1"
    # freq="SImon"
    # realm="ocean"

    # for security reasons, give openid and password when running this script.
    # do not store them here, because the github repository is public!
    OPENID = sys.argv[1]
    print(OPENID)
    PASSWORD = sys.argv[2]
    login(OPENID, PASSWORD)

    # sometimes the node is not available for search, so try a few different ones
    for URL_NODE in URL_NODES:
        conn = SearchConnection(URL_NODE, distrib=True)
        if conn is not None:
            break
    else:
        print("Not able to connect to any of the given nodes:")
        print(URL_NODES)
        print("Exiting...")
        exit(-2)

    facets = "source_id,experiment_id,variable"
    search = ({
        "project": "CMIP6",
        "experiment_id": "1pctCO2",
        "variable": "tas",
        "facets": facets,
        "replica": True,
        "latest": True
    })
    ctx = conn.new_context(
        **search
    )
    search_and_download_wget(ctx, facets, verbose=True)

    search_piControl = search.copy()
    search_piControl["experiment_id"] = "piControl"
    ctx_piControl = conn.new_context(
        **search_piControl
    )
    search_and_download_wget(ctx_piControl, facets, verbose=True)

    print_downloaded_wget()
    #TODO: download per scenario, per model, lsm files
    # search_lsm = ({
    #     "project": "CMIP6",
    #     "realm": "land"
    #     "facets": "source_id,experiment_id,variable",
    #     "replica": True,
    #     "latest": True
    # })
    # ctx_lsm = conn.new_context(
    #     **search_lsm
    # )
    # search_and_download_wget(ctx_lsm)
