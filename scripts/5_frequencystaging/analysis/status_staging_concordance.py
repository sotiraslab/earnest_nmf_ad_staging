#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  5 14:09:01 2025

@author: earnestt1234
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.plotting import staging_colors, set_font_properties

# Preparation
set_config('main')
set_font_properties(6)

baseline = load_split(None, 'baseline', verbose=False)
baseline['Group'] = (
    np.where(baseline['Split'].eq('TrainingBaseline'), 'Training', 'Validation') +
    '-' +
    np.where(baseline['ControlForStaging'].eq(True), 'NC', 'ADS')
    )
scolors = staging_colors()

root_output = get('output_directory')
odir = os.path.join(root_output, 'plots', 'status_staging_concordance')
os.makedirs(odir, exist_ok=True)

# Amyloid
colors = {
    'A0': 'gray',
    'A1': scolors['A1T0'],
    'A2': scolors['A2T0'],
    'NS': scolors['Atypical']
    }

plt.figure(figsize=(3, 1.25))
baseline['Amyloid stage'] = baseline['StageAmyloid'].replace({'0':'A0', '1':'A1', '2':'A2'})

sns.stripplot(data=baseline, y="Group", x='SummarySUVRAmyloid', hue='Amyloid stage',
              alpha=0.5, jitter=.333, size=2.5,
              order=['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS'],
              hue_order=colors.keys(),
              palette=colors)
plt.xlabel('Cortical amyloid (SUVR)')
plt.ylabel('')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)


plt.tight_layout()
plt.savefig(os.path.join(odir, 'amyloid_status_concordance.svg'))

# Tau
colors = {
    'T0': 'gray',
    'T1': scolors['A2T1'],
    'T2': scolors['A2T2'],
    'T3': scolors['A2T3'],
    'T4': scolors['A2T4'],
    'NS': scolors['Atypical']
    }

plt.figure(figsize=(3, 1.25))
baseline['Tau stage'] = (
    baseline['StageTau']
    .replace({'0':'T0', '1':'T1', '2':'T2', '3':'T3', '4':'T4'})
    )
sns.stripplot(data=baseline, y="Group", x='SummarySUVRTau', hue='Tau stage',
              alpha=0.5, jitter=.333, size=2.5,
              order=['Training-NC', 'Training-ADS', 'Validation-NC', 'Validation-ADS'],
              hue_order=colors.keys(),
              palette=colors)
plt.xlabel('Cortical tau (SUVR)')
plt.ylabel('')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)

plt.tight_layout()
plt.savefig(os.path.join(odir, 'tau_status_concordance.svg'))
