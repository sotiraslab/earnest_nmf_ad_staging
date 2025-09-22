import os

from atstaging.config import get, set_config
from atstaging.outputs import load_musestats
from atstaging.preprocessing.segmentation import load_muse_roi_table_cleaned

set_config('main')
root_output = get('output_directory')

preproc_dir = '/ceph/chpc/shared/aristeidis_sotiras_group/tom_pet_processing/'

odir = os.path.join(root_output, 'muse')
os.makedirs(odir, exist_ok=True)

amy = load_musestats(kind='amyloid', output_directory=preproc_dir)
tau = load_musestats(kind='tau', output_directory=preproc_dir)
muse = load_muse_roi_table_cleaned()

amy.to_csv(os.path.join(odir, 'amyloid_rois.csv'), index=False)
tau.to_csv(os.path.join(odir, 'tau_rois.csv'), index=False)
muse.to_csv(os.path.join(odir, 'muse_dict.csv'), index=False)