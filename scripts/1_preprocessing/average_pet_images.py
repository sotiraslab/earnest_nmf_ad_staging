# IMPORTS
import os
from os.path import join as pjoin

from atstaging.config import get, set_config
from atstaging.outputs import load_paths_tables, load_split
from atstaging.plotting import make_average_pet_image

# CONFIG
set_config('main')

# OUTPUTS
OUTDIR = os.path.join(get('output_directory'), 'plots', 'average_pet_images')
os.makedirs(OUTDIR, exist_ok=True)

# TRAINING
training = load_split('training', 'baseline')
paths = load_paths_tables()
training = training.merge(paths[['Subject', 'Session', 'tau_registered', 'amyloid_registered']], on=['Subject', 'Session'], how='left')

cn = training[training['CDRBinned'].eq('0.0') & training['FinalAmyloidStatus'].eq(0)]
preclinical = training[training['FinalAmyloidStatus'].eq(1.0) & training['CDRBinned'].eq('0.0')]
early = training[training['FinalAmyloidStatus'].eq(1.0) & training['CDRBinned'].ne('0.0') & training['GMMTauStatus'].eq(0)]
late = training[training['FinalAmyloidStatus'].eq(1.0) & training['CDRBinned'].ne('0.0') & training['GMMTauStatus'].eq(1)]

# plot - amyloid
make_average_pet_image(
    images=cn['amyloid_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_cn_amyloid.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_cn_amyloid.jpeg'),
    )

make_average_pet_image(
    images=preclinical['amyloid_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_preclinical_amyloid.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_preclinical_amyloid.jpeg'),
    )

make_average_pet_image(
    images=early['amyloid_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_earlydem_amyloid.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_earlydem_amyloid.jpeg'),
    )

make_average_pet_image(
    images=late['amyloid_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_latedem_amyloid.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_latedem_amyloid.jpeg'),
    )

make_average_pet_image(
    images=training['amyloid_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_all_amyloid.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_all_amyloid.jpeg'),
    )

# plot - tau
make_average_pet_image(
    images=cn['tau_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_cn_tau.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_cn_tau.jpeg'),
    )

make_average_pet_image(
    images=preclinical['tau_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_preclinical_tau.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_preclinical_tau.jpeg'),
    )

make_average_pet_image(
    images=early['tau_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_earlydem_tau.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_earlydem_tau.jpeg'),
    )

make_average_pet_image(
    images=late['tau_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_latedem_tau.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_latedem_tau.jpeg'),
    )

make_average_pet_image(
    images=training['tau_registered'].to_list(),
    out_nii=pjoin(OUTDIR, 'training_all_tau.nii.gz'),
    out_figure=pjoin(OUTDIR, 'training_all_tau.jpeg'),
    )