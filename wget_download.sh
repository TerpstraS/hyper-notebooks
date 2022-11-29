#!/bin/bash -l
#
#SBATCH -J wget_esgf
#SBATCH -p short
#SBATCH -t 1:00:00
#SBATCH -n 1
#SBATCH -o log_wget.%j.o
#SBATCH -e log_wget.%j.e

OPENID="https://esgf-node.llnl.gov/esgf-idp/openid/TerpstraS"
PASSWORD="" # fill in password. Do not save to github!

conda activate cmip6-esgf
srun python3 download_esgf.py ${OPENID} ${PASSWORD}
