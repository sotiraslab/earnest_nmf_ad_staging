
import os

from atstaging.config import get, set_config
from atstaging.preprocessing.qc_tools import setup_qc

set_config('main')

# get a list of all dataset outputs
output_directory = get('output_directory')
preproc_directory = os.path.join(output_directory, 'preprocessing', 'images')
dataset_folders = [os.path.join(preproc_directory, folder)
                   for folder in os.listdir(preproc_directory)]

# run setup_qc for each
for folder in dataset_folders:
    if not os.path.isdir(folder):
        continue
    
    setup_qc(
        preproc_dir=folder,
        screenshot_save_behavior='update',
        screenshot_backup=True,
        rerun_imagestats=False
    )