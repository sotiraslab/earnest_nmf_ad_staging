
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
path_record_tau = os.path.join(output_directory, 'nmf', 'tables', 'training_tau_master.csv')
path_record_amyloid = os.path.join(output_directory, 'nmf', 'tables', 'training_amyloid_master.csv')
path_splits_tau = os.path.join(output_directory, 'nmf', 'tables', 'training_tau_splits.csv')
path_splits_amyloid = os.path.join(output_directory, 'nmf', 'tables', 'training_amyloid_splits.csv')
dry=False

# LOAD DATA
training = load_split('training', 'baseline')
paths = load_paths_tables()

# whole training set
df = training.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
df.to_csv(path_record_tau)

# CNs only, used for amyloid
cn = df[df['CDRBinned'].eq('0.0') & ~df['CDRBinned'].isna()]
cn.to_csv(path_record_amyloid)

# TAU
taunmf = NMFRunner(
    name=name_tau,
    master_table_path=path_record_tau,
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[9, 10, 11, 12],
    master_table_path_column='tau_registered',
    use_mask=False
)

taunmf.run_main(dry=dry)
# taunmf.run_reproducibility(reproducibility_splits_path=path_splits_tau, dry=dry)

# AMYLOID
amyloidnmf = NMFRunner(
    name=name_amyloid,
    master_table_path=path_record_amyloid,
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[9, 10, 11, 12],
    master_table_path_column='amyloid_registered',
    use_mask=False
)

amyloidnmf.run_main(dry=dry)
# amyloidnmf.run_reproducibility(reproducibility_splits_path=path_splits_amyloid, dry=dry)
