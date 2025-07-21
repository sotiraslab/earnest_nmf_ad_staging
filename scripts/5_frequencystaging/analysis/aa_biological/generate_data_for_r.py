import os

from atstaging.config import get, set_config 
from atstaging.outputs import load_split, load_musestats
from atstaging.preprocessing.segmentation import load_muse_roi_table_cleaned

set_config('main')

# path to moved preprocessing
output_directory_with_outputs = '/ceph/chpc/shared/aristeidis_sotiras_group/tom_pet_processing/'

# setup output
root_output = get('output_directory')
odir = os.path.join(root_output, 'filesForR')
os.makedirs(odir, exist_ok=True)

# MUSE ROIs table
musedict = load_muse_roi_table_cleaned()
musedict.to_csv(os.path.join(odir, 'muse_data_dict.csv'), index=False)

# Main dataframe
df = load_split(None, None)
df.to_csv(os.path.join(odir, 'maindata.csv'), index=False)

# MUSE values for all subjects
taumuse = load_musestats('tau', output_directory=output_directory_with_outputs)
taumuse = df[['Subject', 'Session']].merge(taumuse, on=['Subject', 'Session'], how='left')
taumuse.to_csv(os.path.join(odir, 'tau_muse_for_maindata.csv'), index=False)

# Create volume weighted ROIs for Braak (MTL / neo) regions

# "The regional tau-PET SUVR
# in the medial temporal region was extracted using the
# weighted average of the amygdala, entorhinal cortex, and
# parahippocampal gyrus"
braak_mtl_regions = [
    'left_amygdala',
    'left_ent_entorhinal_area',
    'left_phg_parahippocampal_gyrus',
    'left_itg_inferior_temporal_gyrus',
    'left_tmp_temporal_pole',
]
braak_mtl_regions = braak_mtl_regions + [x.replace('left', 'right') for x in braak_mtl_regions]
braak_mtl_regions = list(set(braak_mtl_regions))

# The neocortex SUVR was extracted
# from the weighted average of Braak 4, 5, and 6 composite
# regions of interest (ROIs), which included middle temporal
# gyrus, caudal anterior cingulate cortex, rostral anterior cin-
# gulate cortex, posterior cingulate cortex, isthmus of the cin-
# gulate cortex, insula, inferior temporal gyrus, temporal pole,
# superior frontal gyrus, lateral orbitofrontal cortex, medial
# orbitofrontal cortex, frontal pole, caudal middle frontal cortex,
# rostral middle frontal cortex, pars opercularis, pars orbitalis,
# pars triangularis, lateral occipital cortex, parietal supra-
# marginal gyrus, parietal inferior cortex, superior temporal
# gyrus, parietal superior cortex, precuneus, superior temporal
# sulcus, and transverse temporal gyrus
braak_neo_regions = [
    'left_mtg_middle_temporal_gyrus',
    'left_mcgg_middle_cingulate_gyrus',
    'left_acgg_anterior_cingulate_gyrus',
    'left_pcgg_posterior_cingulate_gyrus',
    'left_ains_anterior_insula',
    'left_pins_posterior_insula',
    'left_tmp_temporal_pole',
    'left_msfg_superior_frontal_gyrus_medial_segment',
    'left_sfg_superior_frontal_gyrus',
    'left_smc_supplementary_motor_cortex',
    'left_porg_posterior_orbital_gyrus',
    'left_mfc_medial_frontal_cortex',
    'left_sca_subcallosal_area',
    'left_gre_gyrus_rectus',
    'left_frp_frontal_pole',
    'left_mfg_middle_frontal_gyrus',
    'left_aorg_anterior_orbital_gyrus',
    'left_opifg_opercular_part_of_the_inferior_frontal_gyrus',
    'left_orifg_orbital_part_of_the_inferior_frontal_gyrus',
    'left_trifg_triangular_part_of_the_inferior_frontal_gyrus',
    'left_iog_inferior_occipital_gyrus',
    'left_ocp_occipital_pole',
    'left_sog_superior_occipital_gyrus',
    'left_po_parietal_operculum',
    'left_smg_supramarginal_gyrus',
    'left_ang_angular_gyrus',
    'left_pp_planum_polare',
    'left_pt_planum_temporale',
    'left_stg_superior_temporal_gyrus',
    'left_spl_superior_parietal_lobule',
    'left_pcu_precuneus',
    'left_ttg_transverse_temporal_gyrus'
]
braak_neo_regions = braak_mtl_regions + [x.replace('left', 'right') for x in braak_neo_regions]
braak_neo_regions = list(set(braak_neo_regions))

def calculate_volume_weighted_suvr(regions, muse):
    suvr_cols = [f'{x}_SUVR' for x in regions]
    vol_cols = [f'{x}_VOLUME' for x in regions]
    regional_suvr = muse[suvr_cols]
    regional_vol = muse[vol_cols]
    regional_weights = regional_vol.div(regional_vol.sum(axis=1), axis=0)
    regional_weights.columns = suvr_cols
    suvr = (regional_suvr * regional_weights).sum(axis=1)
    return suvr

braakdata = df[['Subject', 'Session']].copy()
braakdata['BraakMTLSUVR'] = calculate_volume_weighted_suvr(braak_mtl_regions, taumuse)
braakdata['BraakNeoSUVR'] = calculate_volume_weighted_suvr(braak_neo_regions, taumuse)
braakdata.to_csv(os.path.join(odir, 'braak_mtl_neo.csv'), index=False)