
# IMPORTS
import os

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_nmf_runner, mat_to_nifti

# CONFIG
set_config('main')
output_directory = get('output_directory')

# OUTPATH
OUTDIR = os.path.join(output_directory, 'images')
OUTDIR_AMY = os.path.join(OUTDIR, 'amyloid_components')
OUTDIR_TAU = os.path.join(OUTDIR, 'tau_components')
os.makedirs(OUTDIR_AMY, exist_ok=True)
os.makedirs(OUTDIR_TAU, exist_ok=True)

# VARIABLES
nmf_name_tau = 'tau1390'
nmf_ranks_tau = [2, 11] 
nmf_name_amyloid = 'amyloidCN1183'
nmf_ranks_amyloid = [2, 10]

# TAU
path_tau_nmf = os.path.join(output_directory, 'nmf', 'runs', nmf_name_tau)
taunmf = load_nmf_runner(path_tau_nmf)
taunmf_results = taunmf.get_main_resultsmats()
for k in nmf_ranks_tau:
    outdir = os.path.join(OUTDIR_TAU, f'rank{k}')
    os.makedirs(outdir, exist_ok=True)
    mat_to_nifti(taunmf_results[k], outdir)

# AMYLOID
path_amy_nmf = os.path.join(output_directory, 'nmf', 'runs', nmf_name_amyloid)
amynmf = load_nmf_runner(path_amy_nmf)
amynmf_results = amynmf.get_main_resultsmats()
for k in nmf_ranks_amyloid:
    outdir = os.path.join(OUTDIR_AMY, f'rank{k}')
    os.makedirs(outdir, exist_ok=True)
    mat_to_nifti(amynmf_results[k], outdir)