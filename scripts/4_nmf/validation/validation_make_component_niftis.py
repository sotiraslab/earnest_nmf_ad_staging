
# IMPORTS
import os
import shutil

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_nmf_runner, mat_to_nifti

# CONFIG
set_config('main')
output_directory = get('output_directory')

# OUTPATH for saving images
root_savedir = os.path.join(output_directory, 'images')

# HELPER FUNCTION
def create_niftis(nmf_name, root_savedir, ranks):
    path_nmf = os.path.join(output_directory, 'nmf', 'runs', nmf_name)
    nmf = load_nmf_runner(path_nmf)
    results = nmf.get_main_resultsmats()

    savedir = os.path.join(root_savedir, f'{nmf_name}_components')
    os.makedirs(savedir, exist_ok=True)

    for k in ranks:
        savedir_rank = os.path.join(savedir, f'rank{k}')
        os.makedirs(savedir_rank, exist_ok=True)
        mat_to_nifti(results[k], savedir_rank)

        srcpath = results[k]
        matname = os.path.basename(srcpath)
        destpath = os.path.join(savedir_rank, matname)
        shutil.copyfile(srcpath, destpath)

create_niftis('validationA_tau', root_savedir, [12])
create_niftis('validationA_amyloid', root_savedir, [11])
create_niftis('validationB_tau', root_savedir, [12])
create_niftis('validationB_amyloid', root_savedir, [11])
create_niftis('validationC_tau', root_savedir, [12])
create_niftis('validationC_amyloid', root_savedir, [11])
create_niftis('validationAll_tau', root_savedir, [12])
create_niftis('validationAll_amyloid', root_savedir, [11])