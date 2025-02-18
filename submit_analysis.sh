#!/bin/bash -l
#
#SBATCH -J analysis_cmip6
#SBATCH -p short
#SBATCH -t 0:10:00
#SBATCH -n 1
#SBATCH -o log_pytest.%j.o
#SBATCH -e log_pytest.%j.e

conda activate cmip6-hypercc
srun python3 analysis_cmip6.py
