#!/bin/bash -l
#
#SBATCH -J edge_cmip6
#SBATCH -p short
#SBATCH -t 0:30:00
#SBATCH -n 1
#SBATCH -o log_edge_cmip6.%j.o
#SBATCH -e log_edge_cmip6.%j.e

# Created by: Sjoerd Terpstra
# Date: 11/2022

hyperccpath="/nethome/terps020/edge/hypercc/bin"
outpath="/nethome/terps020/edge/output"
datapath="/nethome/terps020/cmip6/data"
wgetpath="/nethome/terps020/cmip6/wget"
lsmpath="/nethome/terps020/cmip6/lsmdata"

# if uncommented, run code on single core instead of parallel
# currently, code gives error if trying to run on single node
#option_single="--single"

# choose between monhtly or annual averages
option_month="--annual"

#TODO set these options to the right values
sigmaS="100"
sigmaT="10"
thresh1=pi-control-max
thresh2=pi-control-max*1/2

scen="1pctCO2"
var="tas"
realm="atmos"

# This should be empty. Is used for masked data
option_extension=""

### clear cache - otherwise it fills the whole hard drive...
rm -f hypercc-cache.hdf5 cache.lock hypercc-cache.db

# loop through wget scripts in the directory of the given scenario
cd "${wgetpath}/${var}/${scen}"
for FILE in *; do

  # call python script to:
  # 1. check if it has an associated piControl. If not continue with next file
  # 2. check lsmfile if realm is not atmos (later TODO)
  # 3. download both scenario and picontrol files
  # 4. preprocess data
  # Careful! Uses different conda environment as hypercc
  #WARNING: set correct conda environment
  conda activate cmip6-xmip
  srun python3 download_preprocess.py ${scen} ${var} ${FILE}
  conda deactivate

  # apply mask to data
  if [[ ${realm} == "land" ]]; then
    lsmfile=${lsm_path}/${model}.${scen}.binary.nc
  elif [[ ${realm} == "ocean" ]]; then
    lsmfile=${lsm_path}/${model}.${scen}.inverse_binary.nc
  fi

  # check if lsmfile exists and if realm is not atmosphere (no mask needed for atmosphere)
  if [[ -f ${lsmfile} && ! ${realm} == "atmos" ]]; then
    file=${datapath}.CMIP.${model}.${scen}.${rea}.${freq}.${var}.gr.nc
    cdo -s ifthen ${lsmfile} ${file} ${file}_masked
    option_extension="--extension gr.nc_masked"
  fi

  # run the hypercc program for edge detection
  conda activate cmip6-hypercc
  ${hyperccpath}/hypercc --data-folder ${datapath} --pi-control-folder ${datapath}  \
    report --variable ${var} --model ${model} --scenario ${scen} --realization ${rea} \
    ${option_extension} --frequency ${freq} ${option_month} --sigma-t ${sigmaT} year \
    --sigma-x ${sigmaS} km
  conda deactivate

  #TODO remove files from datapath directory

done

exit
