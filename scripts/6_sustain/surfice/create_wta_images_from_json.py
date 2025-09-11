import json
import os

from atstaging.config import get, set_config
from atstaging.plotting import paint_winner_take_all

OVERWRITE = False

set_config('main')
root_output = get('output_directory')
odir = os.path.join(root_output, 'images', 'wta_paint')
os.makedirs(odir, exist_ok=True)

wta_json_dir = os.path.join(root_output, 'wta_json')
subfolders = [f for f in os.listdir(wta_json_dir) if os.path.isdir(os.path.join(wta_json_dir, f))]
n = len(subfolders)

for i, subfolder in enumerate(subfolders):

    subfolder_fullpath = os.path.join(wta_json_dir, subfolder)
    json_files = [f for f in os.listdir(subfolder_fullpath) if f.lower().endswith('.json')]
    this_odir = os.path.join(odir, subfolder)
    os.makedirs(this_odir, exist_ok=True)

    for j, name in enumerate(json_files):
        fullpath = os.path.join(subfolder_fullpath, name)
        base = name.replace('.json', '')
        opath_amyloid = os.path.join(this_odir, f'{base}_amyloid.nii.gz')
        opath_tau = os.path.join(this_odir, f'{base}_tau.nii.gz')

        print(f'> Reading "{name}"')
        with open(fullpath, 'r') as f:
            data = json.load(f)
        amyloid_assignments = {k:v for k, v in data.items() if 'PAC' in k}
        tau_assignments = {k:v for k, v in data.items() if 'PTC' in k}

        print()
        if os.path.isfile(opath_amyloid) and not OVERWRITE:
            print(f'> Existing amyloid output for "{name}"; skipping.')
        else:
            print(f'> Creating amyloid output for "{name}".')
            paint_winner_take_all(
                'amyloid',
                assignments=amyloid_assignments,
                threshold=0.5,
                use_saved=True,
                outpath=opath_amyloid
                )
            print(f'> Done [{opath_amyloid}].')

        if os.path.isfile(opath_tau) and not OVERWRITE:
            print(f'> Existing tau output for "{name}"; skipping.')
        else:
            print(f'> Creating tau output for "{name}".')
            paint_winner_take_all(
                'tau',
                assignments=tau_assignments,
                threshold=0.5,
                use_saved=True,
                outpath=opath_tau
                )
            print(f'> Done [{opath_tau}].')

