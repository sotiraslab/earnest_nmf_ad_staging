#!/bin/bash

source ~/miniconda/bin/activate atstaging

module load afni
module load ants
module load c3d
module load fsl

export PYTHONUNBUFFERED=1