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

OPENID="https://esgf-node.llnl.gov/esgf-idp/openid/TerpstraS"
PASSWORD=$1 # get password via command line. Do not save to github!

hyperccpath="/nethome/terps020/edge/hypercc/bin"
outpath="/nethome/terps020/edge/output"
datatemppath="/nethome/terps020/cmip6/datatemp"
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
directory="${wgetpath}/${var}/${scen}"
for FILE in "${directory}"/*; do
  if [[ -f ${FILE} ]]; then

  echo ${FILE}

  # call python script to:
  # 1. check if it has an associated piControl. If not continue with next file
  # 2. check lsmfile if realm is not atmos (later TODO)
  # 3. download both scenario and picontrol files
  # 4. preprocess data
  # Careful! Uses different conda environment as hypercc
  #WARNING: set correct conda environment (should be correct now)
  #NOTE: above implemented except step 2. Not tested, but should work.
  #conda activate cmip6-download
  #srun python3 download_preprocess.py ${OPENID} ${PASSWORD} ${scen} ${var} ${FILE}
  #conda deactivate

  # call
  # 1. python script to find correct wget files and put them in datatemp/wget
  # 2. run wget from bash script
  # 3. run python to preprocess downloaded files
  conda activate cmip6-download
  srun python3 prepare_wget.py ${scen} ${var} ${FILE}

  wgetdirectory="${datatemppath}"
  for WGETFILE in "${wgetdirectory}"/*; do
    if [[ -f ${WGETFILE} ]]; then
    echo "${WGETFILE}"
    # bash ${WGETFILE} -s
    fi
  done
  exit
  srun python3 preprocess.py ${scen} ${var}
  conda deactivate

  # apply mask to data
  if [[ ${realm} == "land" ]]; then
    lsmfile=${lsm_path}/${model}.${scen}.binary.nc
  elif [[ ${realm} == "ocean" ]]; then
    lsmfile=${lsm_path}/${model}.${scen}.inverse_binary.nc
  fi

  # check if lsmfile exists and if realm is not atmosphere (no mask needed for atmosphere)
  if [[ -f ${lsmfile} && ! ${realm} == "atmos" ]]; then
    # for the scenario file
    file_var=${datatemppath}.CMIP.${model}.${scen}.${rea}.${freq}.${var}.gr.nc
    cdo -s ifthen ${lsmfile} ${file_var} ${file_var}_masked

    # for the piControl file
    file_piControl=${datatemppath}.CMIP.${model}.piControl.${rea}.${freq}.${var}.gr.nc
    cdo -s ifthen ${lsmfile} ${file_piControl} ${file_piControl}_masked
    option_extension="--extension gr.nc_masked"
  fi

  # run the hypercc program for edge detection
  conda activate cmip6-hypercc
  ${hyperccpath}/hypercc --data-folder ${datatemppath} --pi-control-folder ${datatemppath}  \
    report --variable ${var} --model ${model} --scenario ${scen} --realization ${rea} \
    ${option_extension} --frequency ${freq} ${option_month} --sigma-t ${sigmaT} year \
    --sigma-x ${sigmaS} km
  conda deactivate

  #TODO remove files from datapath directory
  # rm -r ${datatemppath}

  #WARNING: remove exit after testing
  echo "Program exit after one iteration of loop for debugging purposes..."
  exit
  fi
done

exit
