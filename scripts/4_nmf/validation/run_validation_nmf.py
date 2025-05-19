
# imports
import os

from atstaging.config import get, set_config
from atstaging.nmf.run import NMFRunner
from atstaging.outputs import load_split, load_paths_tables

# config
set_config('main')
output_directory = get('output_directory')

# parameters
TAU_RANK = 11
AMYLOID_RANK = 10

# load master data
validationA = load_split(split='validation', longitudinal='baseline', validation_sub='A')
validationB = load_split(split='validation', longitudinal='baseline', validation_sub='B')
validationC = load_split(split='validation', longitudinal='baseline', validation_sub='C')

validationACN = validationA[validationA['CDRBinned'].eq('0.0') & ~ validationA['CDRBinned'].isna()]
validationBCN = validationB[validationB['CDRBinned'].eq('0.0') & ~ validationB['CDRBinned'].isna()]
validationCCN = validationC[validationC['CDRBinned'].eq('0.0') & ~ validationC['CDRBinned'].isna()]

# add paths to preprocessed images
paths = load_paths_tables()

validationA = validationA.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
validationB = validationB.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
validationC = validationC.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
validationACN = validationACN.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
validationBCN = validationBCN.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')
validationCCN = validationCCN.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')

# save record of input tables
validationA.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'validationA_master.csv'))
validationB.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'validationB_master.csv'))
validationC.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'validationC_master.csv'))
validationACN.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'validationACN_master.csv'))
validationBCN.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'validationBCN_master.csv'))
validationCCN.to_csv(os.path.join(output_directory, 'nmf', 'tables', 'validationCCN_master.csv'))

# VALIDATION A - TAU
validationATauNMF = NMFRunner(
    name='validationA_tau',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'validationA_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[TAU_RANK],
    master_table_path_column='tau_registered',
    use_mask=False
)

# VALIDATION A - AMYLOID
validationAAmyNMF = NMFRunner(
    name='validationA_amyloid',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'validationACN_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[AMYLOID_RANK],
    master_table_path_column='amyloid_registered',
    use_mask=False
)

# VALIDATION B - TAU
validationBTauNMF = NMFRunner(
    name='validationB_tau',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'validationB_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[TAU_RANK],
    master_table_path_column='tau_registered',
    use_mask=False
)

# VALIDATION B - AMYLOID
validationBAmyNMF = NMFRunner(
    name='validationB_amyloid',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'validationBCN_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[AMYLOID_RANK],
    master_table_path_column='amyloid_registered',
    use_mask=False
)


# VALIDATION C - TAU
validationCTauNMF = NMFRunner(
    name='validationC_tau',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'validationC_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[TAU_RANK],
    master_table_path_column='tau_registered',
    use_mask=False
)

# VALIDATION C - AMYLOID
validationCAmyNMF = NMFRunner(
    name='validationC_amyloid',
    master_table_path=os.path.join(output_directory, 'nmf', 'tables', 'validationCCN_master.csv'),
    output_root_folder=os.path.join(output_directory, 'nmf', 'runs'),
    ranks=[AMYLOID_RANK],
    master_table_path_column='amyloid_registered',
    use_mask=False
)

# Run
# Set dry=True to actually submit
dry = True

validationATauNMF.run_main(dry=dry)
validationAAmyNMF.run_main(dry=dry)
validationBTauNMF.run_main(dry=dry)
validationBAmyNMF.run_main(dry=dry)
validationCTauNMF.run_main(dry=dry)
validationCAmyNMF.run_main(dry=dry)