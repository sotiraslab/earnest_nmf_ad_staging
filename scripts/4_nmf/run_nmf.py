
# IMPORTS
import os

from atstaging.config import get, set_config
from atstaging.nmf.run import NMFRunner
from atstaging.outputs import load_split, load_paths_tables

# VARIABLES
# NOTE: set `dry=False` to actually run the NMF
path_splits = '/scratch/tom.earnest/atstaging/nmf/tables/training1390_splits.csv'
dry=True

# CONFIG
set_config('main')
output_directory = get('output_directory')

# LOAD DATA
training = load_split('training', 'baseline')
paths = load_paths_tables()
df = training.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
df.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'training1390_master.csv'))

# TAU
taunmf = NMFRunner(
    name='tau1390',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'training1390_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=list(range(2, 21)),
    master_table_path_column='tau_registered',
    use_mask=False
)

taunmf.run_main(dry=dry)
taunmf.run_reproducibility(reproducibility_splits_path=path_splits, dry=dry)

# AMYLOID
amyloidnmf = NMFRunner(
    name='amyloid1390',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'training1390_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=list(range(2, 21)),
    master_table_path_column='amyloid_registered',
    use_mask=False
)

amyloidnmf.run_main(dry=dry)
amyloidnmf.run_reproducibility(reproducibility_splits_path=path_splits, dry=dry)
