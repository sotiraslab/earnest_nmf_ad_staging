
"""Selects a subset of individuals (50 from each dataset) and creates a table for preprocessing."""

import os

import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import load_master, setup_outputs_folder

# config stuff
set_config('main')
OUTPUTDIRECTORY = get('output_directory')
setup_outputs_folder(OUTPUTDIRECTORY)

# set how many people are sampled from each dataset
SAMPLE_PER_DATASET = 30

# read in the master dataset
master = load_master()

# filter
print()
print('*** Filtering master dataset to only include people with present CDR information and scans')
master = master.dropna(axis=0, subset=['CDRBinned', 'PathT1', 'PathAmyloid', 'PathTau'])

# sample people with even CDR
datasets = master['DataSet'].unique()
subsamples = []
for dataset in datasets:
    sub = master[master['DataSet'].eq(dataset)].copy()
    cdr_counts = sub.groupby('CDRBinned')['Subject'].count()
    sample_per_cdr = SAMPLE_PER_DATASET // len(cdr_counts)

    subsample = []

    for cdr in cdr_counts.index:
        samecdr = sub[sub['CDRBinned'].eq(cdr)].copy()
        if len(samecdr) < sample_per_cdr:
            subsample.append(samecdr)
        else:
            subsample.append(samecdr.sample(n=sample_per_cdr, replace=False))
    subsample = pd.concat(subsample)

    # add output column
    subsample['OutputDirectory'] = os.path.join(OUTPUTDIRECTORY, 'preprocessing', 'images', dataset)

    # add to output
    subsamples.append(subsample)

# join into a preproc table
preproc_table = pd.concat(subsamples, ignore_index=True)
print()
print('Scans selected for preprocessing:')
print('----------')
print(pd.crosstab(preproc_table['DataSet'], preproc_table['CDRBinned']))
print()
print('TOTAL:', len(preproc_table))

# save
outpath = os.path.join(OUTPUTDIRECTORY, 'preprocessing', 'preproc_tables', 'mini_processing_30each.csv')
print()
print(f'Saving preproc table at {outpath}.')
preproc_table.to_csv(outpath, index=False)


