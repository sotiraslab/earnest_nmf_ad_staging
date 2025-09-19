import os

import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import load_subtyped_data

set_config('main')
root_output = get('output_directory')

# set up I/O
infolder = os.path.join(root_output, 'sila', 'input')
outfolder = os.path.join(root_output, 'sila', 'output')
os.makedirs(infolder, exist_ok=True)
os.makedirs(outfolder, exist_ok=True)

# Load data
df = load_subtyped_data('training', include_longitudinal=True)
s1 = df[df['TrainingMLSubtype'].eq('S1')]
s2 = df[df['TrainingMLSubtype'].eq('S2')]
s3 = df[df['TrainingMLSubtype'].eq('S3')]

# save
s1.to_csv(os.path.join(infolder, 's1.csv'), index=False)
s2.to_csv(os.path.join(infolder, 's2.csv'), index=False)
s3.to_csv(os.path.join(infolder, 's3.csv'), index=False)
