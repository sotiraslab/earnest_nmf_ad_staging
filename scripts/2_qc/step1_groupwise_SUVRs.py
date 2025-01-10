# Imports
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder

# Configuration
set_config('main')
root_output_directory = get('output_directory')
setup_outputs_folder(root_output_directory)

# Settings
PLOT_REGIONS = [
    'left_acgg_anterior_cingulate_gyrus_SUVR',
    'left_ent_entorhinal_area_SUVR',
    'left_frp_frontal_pole_SUVR',
    'left_itg_inferior_temporal_gyrus_SUVR',
    'left_ocp_occipital_pole_SUVR',
    'left_pcu_precuneus_SUVR',
    'left_pog_postcentral_gyrus_SUVR',
    'right_acgg_anterior_cingulate_gyrus_SUVR',
    'right_ent_entorhinal_area_SUVR',
    'right_frp_frontal_pole_SUVR',
    'right_itg_inferior_temporal_gyrus_SUVR',
    'right_ocp_occipital_pole_SUVR',
    'right_pcu_precuneus_SUVR',
    'right_pog_postcentral_gyrus_SUVR',
]

# Load the regional SUVRs into a big table
def load_musestats(pettype, preproc_folder):
    dfs = []

    for dataset in os.listdir(preproc_folder):
        dataset_dir = os.path.join(preproc_folder, dataset)
        if not os.path.isdir(dataset_dir):
            continue
    
        qc_dir = os.path.join(dataset_dir, 'qc')
        
        if not os.path.isdir(qc_dir):
            print(f'Omitting directory {dataset_dir} because cannot find qc folder within.')
    
        musetable = os.path.join(qc_dir, f'musestats_{pettype}.csv')
        df = pd.read_csv(musetable, dtype={'Subject':str, 'Session':str})
        dfs.append(df)
        
    muse = pd.concat(dfs)
    return muse
    
preproc_folder = os.path.join(root_output_directory, 'preprocessing', 'images')
amy = load_musestats('amyloid', preproc_folder=preproc_folder)
tau = load_musestats('tau', preproc_folder=preproc_folder)

# Load the master table to get CDR/amyloid information
master_path = os.path.join(root_output_directory, 'masterTables', 'MASTER.csv')
master = pd.read_csv(master_path, dtype={'Subject':str, 'Session':str})

merger = master[['DataSet', 'Subject', 'Session', 'AmyloidPositive', 'CDRBinned']].copy()
amy = merger.merge(amy, on=['Subject', 'Session'], how='inner')
tau = merger.merge(tau, on=['Subject', 'Session'], how='inner')

# Plot: setup 
output_plots_directory = os.path.join(root_output_directory, 'plots', 'groupwise_regional_SUVR')
if not os.path.isdir(output_plots_directory):
    os.mkdir(output_plots_directory)

output_amyloid = os.path.join(output_plots_directory, 'amyloid')
if not os.path.isdir(output_amyloid):
    os.mkdir(output_amyloid)

output_tau = os.path.join(output_plots_directory, 'tau')
if not os.path.isdir(output_tau):
    os.mkdir(output_tau)

def suvr_boxplot(data, region, groupby):
    fig = sns.boxplot(data=data, x='DataSet', y=region, hue=groupby)
    plt.title(region)
    plt.ylabel('SUVR')
    return fig
    
# Plot: by Amyloid status
for i, region in enumerate(PLOT_REGIONS):

    print()
    print(f'>>> Plotting region {region} [{i+1}/{len(PLOT_REGIONS)}]')

    # amyloid by amyloid status
    fig = suvr_boxplot(amy, region=region, groupby='AmyloidPositive')
    savepath = os.path.join(output_amyloid, f'by_amyloid_{region}.png')
    plt.savefig(savepath, dpi=300)
    plt.close()

    # amyloid by CDR
    fig = suvr_boxplot(amy, region=region, groupby='CDRBinned')
    savepath = os.path.join(output_amyloid, f'by_cdr_{region}.png')
    plt.savefig(savepath, dpi=300)
    plt.close()

    # tau by amyloid status
    fig = suvr_boxplot(tau, region=region, groupby='AmyloidPositive')
    savepath = os.path.join(output_tau, f'by_amyloid_{region}.png')
    plt.savefig(savepath, dpi=300)
    plt.close()

    # tau by CDR
    fig = suvr_boxplot(tau, region=region, groupby='CDRBinned')
    savepath = os.path.join(output_tau, f'by_cdr_{region}.png')
    plt.savefig(savepath, dpi=300)
    plt.close()