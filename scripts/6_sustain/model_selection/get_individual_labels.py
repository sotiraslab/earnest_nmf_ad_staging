import os

import numpy as np
import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import load_split
from atstaging.sustain import SustainManager

set_config('main')
root_output = get('output_directory')

# load data
master = load_split(None, None, verbose=False)
wdata = master[master.columns[master.columns.str.contains('WScore')]].copy().to_numpy()

# load sustain
training_sustain = SustainManager(os.path.join(root_output, 'sustain', 'training'))
validation_sustain = SustainManager(os.path.join(root_output, 'sustain', 'validation'))

# predictions
tmodel_predictions = training_sustain.predict(wdata, n_subtypes=3, prefix='Training')
vmodel_predictions = validation_sustain.predict(wdata, n_subtypes=3, prefix='Validation')[['ValidationMLSubtype', 'ValidationMLStage']]
s7_predictions = training_sustain.predict(wdata, n_subtypes=7, prefix='S7')[['S7MLSubtype', 'S7MLStage']]

features = pd.concat([master[['Subject', 'Session']], tmodel_predictions, vmodel_predictions, s7_predictions], axis=1)

# add binned stages
features['TrainingMLStageBinned'] = pd.cut(features['TrainingMLStage'], [1, 5, 9, np.inf], labels=['1-4', '5-8', '9+'], right=False)
features.loc[features['TrainingMLStage'].isna(), 'TrainingMLStageBinned'] = np.nan

features['ValidationMLStageBinned'] = pd.cut(features['ValidationMLStage'], [1, 5, 9, np.inf], labels=['1-4', '5-8', '9+'], right=False)
features.loc[features['ValidationMLStage'].isna(), 'ValidationMLStageBinned'] = np.nan

# save
opath = os.path.join(root_output, 'masterTables', 'FEATURE_SUSTAIN.csv')
features.to_csv(opath, index=False)

# save for R
tmp = load_split(None, None, verbose=False)
tmp.to_csv(os.path.join(root_output, 'filesForR', 'master_with_sustain.csv'), index=False)