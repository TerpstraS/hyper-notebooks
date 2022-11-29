#!/bin/bash -l
#
#SBATCH -J analysis_cmip6
#SBATCH -p short
#SBATCH -t 1:00:00
#SBATCH -n 1
#SBATCH -o log_wget.%j.o
#SBATCH -e log_wget.%j.e

conda activate cmip6-esgf
srun python3 download_esgf.py
