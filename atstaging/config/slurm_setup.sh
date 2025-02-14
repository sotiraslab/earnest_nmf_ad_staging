#!/bin/bash

module load afni
module load ants
module load c3d
module load fsl

# NOTE: loading FSL changes the default `python` on CHPC
# b/c it has its own installation
# and the FSL bin path is prepended to $PATH
# the last line tries to ensure we get the conda environment python
source ~/miniconda/bin/activate atstaging 
export PYTHONUNBUFFERED=1
export PATH=~/miniconda/envs/atstaging/bin:$PATH