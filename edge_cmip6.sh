#!/bin/bash -l
#
#SBATCH -J edge_cmip6
#SBATCH -p short
#SBATCH -t 0:30:00
#SBATCH -n 1
#SBATCH -o log_edge_cmip6.%j.o
#SBATCH -e log_edge_cmip6.%j.e

conda activate cmip6-hypercc

hyperccpath="/nethome/terps020/edge/hypercc/bin"
outpath="/nethome/terps020/edge/output"
datapath="/nethome/terps020/cmip6/data"
lsmpath="/nethome/terps020/cmip6/lsmdata"

#option_single="--single"
option_month="--annual"

sigmaS="100"
sigmaT="10"
thresh1=pi-control-max
thresh2=pi-control-max*1/2

model="GFDL-ESM4"
scen="1pctCO2"
var="siconc"
rea="r1i1p1f1"
freq="SImon"
realm="ocean"

# This should be empty. Is used for masked data
option_extension=""

### clear cache - otherwise it fills the whole hard drive...
rm -f hypercc-cache.hdf5 cache.lock hypercc-cache.db

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
${hyperccpath}/hypercc --data-folder ${datapath} --pi-control-folder ${datapath}  \
  report --variable ${var} --model ${model} --scenario ${scen} --realization ${rea} \
  ${option_extension} --frequency ${freq} ${option_month} --sigma-t ${sigmaT} year \
  --sigma-x ${sigmaS} km


exit
