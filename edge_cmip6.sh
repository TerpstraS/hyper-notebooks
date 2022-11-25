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
#option_single="--single"
option_month="--annual"

sigmaS="100"
sigmaT="10"
thresh1=pi-control-max
thresh2=pi-control-max*1/2

model="IPSL-CM6A-LR"
scen="1pctCO2"
var="tas"
rea="r1i1p1f1"
freq="Amon"

### clear cache - otherwise it fills the whole hard drive...
rm -f hypercc-cache.hdf5 cache.lock hypercc-cache.db

${hyperccpath}/hypercc --data-folder ${datapath} --pi-control-folder ${datapath}  \
  report --variable ${var} --model ${model} --scenario ${scen} --realization ${rea} \
  --frequency ${freq} ${option_month} --sigma-t ${sigmaT} year --sigma-x ${sigmaS} km
