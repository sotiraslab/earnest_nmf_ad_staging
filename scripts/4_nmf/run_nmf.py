
# IMPORTS
import os

from atstaging.config import get, set_config
from atstaging.nmf.run import NMFRunner
from atstaging.outputs import load_split, load_paths_tables

# CONFIG
set_config('main')
output_directory = get('output_directory')

# VARIABLES
# NOTE: set `dry=False` to actually run the NMF
name_tau = 'training_tau'
name_amyloid = 'training_amyloid'
path_master = os.path.join(output_directory, 'nmf', 'tables', 'training_master.csv')
path_splits = os.path.join(output_directory, 'nmf', 'tables', 'training_splits.csv')
dry=True

# LOAD DATA
training = load_split('training', 'baseline')
paths = load_paths_tables()

# whole training set
df = training.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
df.to_csv(path_master)

# TAU
taunmf = NMFRunner(
    name=name_tau,
    master_table_path=path_master,
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=list(range(2, 21)),
    master_table_path_column='tau_registered',
    use_mask=False
)

taunmf.run_main(dry=dry)
taunmf.run_reproducibility(reproducibility_splits_path=path_splits, dry=dry)

# AMYLOID
amyloidnmf = NMFRunner(
    name=name_amyloid,
    master_table_path=path_master,
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=list(range(2, 21)),
    master_table_path_column='amyloid_registered',
    use_mask=False
)

amyloidnmf.run_main(dry=dry)
amyloidnmf.run_reproducibility(reproducibility_splits_path=path_splits, dry=dry)
