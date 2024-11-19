
"""This code will load search the OASIS3 download directory, isolate the frames of interest
from amyloid/tau PET images, and copy all filtered images to a new directory.  T1 images are
also copied.

The primary need for this code is to do frame selection for PET images.  The PET processing pipeline
(`atstaging.preprocessing.pet`) is not prepared to select frames from dynamic scans.
Many of the scans avaialable (particularly for amyloid) are dynamic, and need the stable window
frames pulled out.  Frame selection is as follows:

    - PIB: 30-60 minutes (typically 6 frames)
    - AV45: 50-70 minutes (typically 4 frames)
    - FTP: 80-110 minutes (typically 6 frames)

After frame selection, images are copied to a user-specified output directory.  This 
was somewhat required on the CHPC (WashU computing cluster where I am accessing these images)
because there were issues with accessing the shared dataset from compute nodes.  
        
Most of the relevant code for this is in the `atstaging.dataorg.oasis` module.  Some other key
metholodological points are:

    - Not all people were in the scanner for the same amount of time (see OASIS3 documentation PDF).
    The code has some branches to detect that and determine which are the active frames.
    - The code expects OASIS3 data in the format provided by the RCIF shared datasets on the CHPC
    at WashU (https://docs.chpc.wustl.edu/datasets/).  As such, tweaking might be required for
    OASIS3 data downloaded from elsewhere.

After running this script, proceed to the "oasis.py" script (in this same directory).
"""

import os

import nibabel as nib
import pandas as pd

from atstaging.config import get
from atstaging.dataorg.oasis import oasis3_image_list, oasis_table_pull_PET_frames

OASIS3_FOLDER = '/ceph/chpc/rcif_datasets/oasis/OASIS3'
OASIS3AV1451_FOLDER = '/ceph/chpc/rcif_datasets/oasis/OASIS3AV1451'
OASIS_COPY_DIRECTORY = '/scratch/tom.earnest/OASIS'
OVERWRITE_COPY = False
OUTPUT_FOLDER = get('output_directory')
USE_CACHE = True
DRY_RUN = False

# setup caching
CACHEDIR = os.path.join(OUTPUT_FOLDER, 'downloadLists')

# PART 1: LOAD THE LIST OF DOWNLOADED OASIS3 & OASIS3AV1451 DATA
# # # # # # # # # #
oasis3_downloads = oasis3_image_list(OASIS3_FOLDER, cache_dir=CACHEDIR, use_cache=USE_CACHE, cache_tag='oasis3')
oasis3av1451_downloads = oasis3_image_list(OASIS3AV1451_FOLDER, cache_dir=CACHEDIR, use_cache=USE_CACHE, cache_tag='oasis3av1451')

# PART 2: PULL THE FRAMES OF INTEREST FOR TAU
# # # # # # # # # #

# NOTE: "DRY_RUN" will not do the copying, so needs to be set to False in order to actually prepare images
#       but can be useful for developing/debugging

# start with tau - this is a smaller number of images, and can be used to limit the amyloid search to only
# people with tau
tau_conversion = oasis_table_pull_PET_frames(
    table=oasis3av1451_downloads,
    output_directory=os.path.join(OASIS_COPY_DIRECTORY, 'tau'),
    dry_run=DRY_RUN,
    overwrite=OVERWRITE_COPY
)

# handle duplicate images in tau
# there are a few people who have a full dynamic image and one with 6 frames, which both appear usable
# we take the dynamic one
tau_conversion = tau_conversion.sort_values(['sub', 'ses', 'src_shape']).groupby('sub').head(1)

# save the record
tau_conversion.to_csv(os.path.join(OUTPUT_FOLDER, 'downloadLists', 'oasis3_tau_conversion.csv'), index=False)

# PART 3: PULL THE FRAMES OF INTEREST FOR AMYLOID
# # # # # # # # # #

# first, separate out the MRI and AV45 from the OASIS3 search
oasis3_downloads.loc[oasis3_downloads['ses'].isna(), 'ses'] = oasis3_downloads['sess']

mri_downloads = oasis3_downloads[
    oasis3_downloads['modality'].eq('T1w') &
    oasis3_downloads['acq'].ne('hippocampus') &
    oasis3_downloads['echo'].isna()
        ].copy()

amy_downloads = oasis3_downloads[
    oasis3_downloads['modality'].eq('pet') &
    oasis3_downloads['acq'].isin(['PIB', 'AV45'])
].copy()

# next, do a merge operation to find amyloid scans within 365D of tau scans
tau_joiner = tau_conversion[['sub', 'ses']].copy()
tau_joiner['ses'] = tau_joiner['ses'].str.lstrip('d').astype(float)
amy_joiner = amy_downloads[['sub', 'ses']].copy()
amy_joiner['ses'] = amy_joiner['ses'].str.lstrip('d').astype(float)

merge = tau_joiner.merge(amy_joiner, how='left', on='sub', suffixes=['_tau', '_amyloid'])
merge = merge[~merge['ses_amyloid'].isna()]
merge['delta'] = (merge['ses_tau'] - merge['ses_amyloid']).abs()

group = merge.loc[merge.groupby('sub')['delta'].idxmin().values, :]
group = group.loc[group['delta'].le(365), :]

amy_downloads['id'] = amy_downloads['sub'] + amy_downloads['ses'].str.lstrip('d').astype(int).astype(str)
group['id'] = group['sub'] + group['ses_amyloid'].astype(int).astype(str)
amy_downloads_filtered = amy_downloads[amy_downloads['id'].isin(group['id'])].copy()

# now, convert the amyloid scans
amy_conversion = oasis_table_pull_PET_frames(
    table=amy_downloads_filtered,
    output_directory=os.path.join(OASIS_COPY_DIRECTORY, 'amyloid'),
    dry_run=DRY_RUN,
    overwrite=OVERWRITE_COPY
)

# save the record
amy_conversion.to_csv(os.path.join(OUTPUT_FOLDER, 'downloadLists', 'oasis3_amyloid_conversion.csv'), index=False)

# PART 4: COPY OVER T1 IMAGES
# # # # # # # # # #

# do a similar merging operation as above to link T1 scans to PET
pet_joiner = group[['sub']].copy()
pet_joiner['ses'] = (group['ses_tau'] + group['ses_amyloid']) / 2
mri_joiner = mri_downloads[['sub', 'ses']].copy()
mri_joiner['ses'] = mri_joiner['ses'].str.lstrip('d').astype(float)

merge_mri = pet_joiner.merge(mri_joiner, how='left', on='sub', suffixes=['_pet', '_mri'])
merge_mri = merge_mri[~merge_mri['ses_mri'].isna()]
merge_mri['delta'] = (merge_mri['ses_pet'] - merge_mri['ses_mri']).abs()

group_mri = merge_mri.loc[merge_mri.groupby('sub')['delta'].idxmin().values, :]
group_mri = group_mri.loc[group_mri['delta'].le(365), :]

mri_downloads['id'] = mri_downloads['sub'] + mri_downloads['ses'].str.lstrip('d').astype(int).astype(str)
group_mri['id'] = group_mri['sub'] + group_mri['ses_mri'].astype(int).astype(str)
mri_downloads_filtered = mri_downloads[mri_downloads['id'].isin(group['id'])].copy()

# Convert (copy) the images to the destination folder
print()
print('T1 Image Conversion')
print('~~~~~~~~~~~~~~~~~~~')

t1_outfolder = os.path.join(OASIS_COPY_DIRECTORY, 't1')

if not os.path.isdir(t1_outfolder):
    os.mkdir(t1_outfolder)

images = []
for i, (_, row) in enumerate(mri_downloads_filtered.iterrows()):
    imgpath = row['path']
    base = os.path.basename(imgpath)
    newpath = os.path.join(t1_outfolder, base)

    d = row.to_dict()
    d['res_img'] = newpath
    images.append(d)

    print(f'> MRI Image: {i+1}: {imgpath}')
    if os.path.exists(newpath) and not OVERWRITE_COPY:
        print(f'    * Not overwriting existing image at {newpath}')
        continue
    
    print(f'    * Writing image to destination: {newpath}')
    nii = nib.load(imgpath)
    nib.save(nii, newpath)


mri_conversion = pd.DataFrame(images)
mri_conversion.to_csv(os.path.join(OUTPUT_FOLDER, 'downloadLists', 'oasis3_mri_conversion.csv'), index=False)
