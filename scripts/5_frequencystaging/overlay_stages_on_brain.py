#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 11:51:04 2025

@author: earnestt1234
"""

import os

from atstaging.config import set_config, get
from atstaging.plotting import paint_winner_take_all

# PARAMETERS

amy_mapping = {
    'PACParietal': 1,
    'PACFrontal': 1,
    'PACSensorimotor': 2,
    'PACOccipital': 2
    }

tau_mapping = {
    'PTCMedialTemporal': 1,
    'PTCRightParietalTemporal': 2,
    'PTCLeftParietalTemporal': 2,
    'PTCOccipital': 3,
    'PTCFrontal': 4,
    'PTCSensorimotor': 4,
    'PTCInsularMedialFrontal': 4
    }

# MAIN

set_config('main')

output_root = get('output_directory')
outdir = os.path.join(output_root, 'images', 'staging_brains')
os.makedirs(outdir, exist_ok=True)

paint_winner_take_all('amyloid', amy_mapping, threshold=0.5,
                      outpath=os.path.join(outdir, 'training_staging_amyloid.nii.gz'))

paint_winner_take_all('tau', tau_mapping, threshold=0.5,
                      outpath=os.path.join(outdir, 'training_staging_tau.nii.gz'))

# create progressive staging brains
for i in [0, 1, 2]:
    mapping = {k:v for k, v in amy_mapping.items() if v <= i}
    paint_winner_take_all('amyloid', mapping, threshold=0.5,
                          outpath=os.path.join(outdir, f'training_staging_amyloid_stage{i}.nii.gz'))

for i in [0, 1, 2, 3, 4]:
    mapping = {k:v for k, v in tau_mapping.items() if v <= i}
    paint_winner_take_all('tau', mapping, threshold=0.5,
                          outpath=os.path.join(outdir, f'training_staging_tau_stage{i}.nii.gz'))
