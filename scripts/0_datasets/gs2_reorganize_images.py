
import os
from os.path import dirname as pdir
from pathlib import Path

import pandas as pd

from atstaging.config import get, set_config
from atstaging.preprocessing.conversion import run_dcm2niix, merge_separated_dicom_frames
from atstaging.dataorg.utils import list_loni_images

# config
set_config('main')
OUTPUT_FOLDER = get('output_directory')

# variables
gs2_image_dir = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS2/images/dicom/GS2'
output_dir = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS2/images/nifti/GS2/'
output_finallist = os.path.join(OUTPUT_FOLDER, 'downloadLists', 'gs2_nifti_images.csv')
overwrite = False
merged_pet_name = 'CONCATENATED_PET_IMAGE'

# get list of images
loni= list_loni_images(gs2_image_dir)

# main script
print('GS2 Image Reorganization')

print(f'> Finding images in {gs2_image_dir}')
# loni = list_loni_images(gs2_image_dir)

print('> Identifying cases which need merging')
# apply some filtering of duplicate reasons
removed = loni[loni['Path'].str.lower().str.contains('non|not|no_loop')]
loni = loni[~loni['Path'].str.lower().str.contains('non|not|no_loop')]
loni = loni.sort_values(['Subject', 'Sequence', 'Date'])

# identify the number of duplicates per case
# we specficically care in the ones with 4 images
# by manual inspection, these appear the only cases that need to be merged
count = loni.groupby(['Subject', 'Date'])['Path'].count().reset_index()
count.columns = ['Subject', 'Date', 'DuplicateCount']
loni = loni.merge(count, on=['Subject', 'Date'], how='left')
n_single = sum(loni['DuplicateCount'].eq(1))
n_quad = sum(loni['DuplicateCount'].eq(4)) // 4
print(f'  + Single images: {n_single}')
print(f'  + Split images: {n_quad}')

# begin image conversion
records = []

print('> Converting single images')
convert_single = loni[loni['DuplicateCount'].eq(1)]
for i, (idx, row) in enumerate(convert_single.iterrows()):

    image = row['Path']
    imageid = os.path.basename(image)
    date = os.path.basename(pdir(image))
    acq = os.path.basename(pdir(pdir(image)))
    sub = os.path.basename(pdir(pdir(pdir(image))))

    image_dest_folder = os.path.join(output_dir, sub, acq, date, imageid)
    image_dest_name = acq
    image_dest_path = os.path.join(image_dest_folder, image_dest_name + '.nii.gz')
    
    print(f'  + [{i+1}/{n_single}]')
    print(f'  + Source: {image}')
    print(f'  + Dest: {image_dest_path}')

    if os.path.isfile(image_dest_path) and not overwrite:
        print('  + Destination image already exists.')
        continue

    Path(image_dest_folder).mkdir(parents=True, exist_ok=True)
    run_dcm2niix(indir=image, outdir=image_dest_folder, name=image_dest_name, silent=True)

    record = {
        'Subject': row['Subject'],
        'Sequence': row['Sequence'],
        'Date': row['Date'],
        'ImageID': row['ImageID'],
        'NIFTIPath': image_dest_path,
        'DICOMPath1': row['Path'],
    }
    records.append(record)

print('> Converting split images')
convert_quad = loni[loni['DuplicateCount'].eq(4)]
for i, (idx, group) in enumerate(convert_quad.groupby(['Subject', 'Date'])):
    
    images = sorted(group['Path'])
    example = images[0]
    imageid = os.path.basename(example)
    date = os.path.basename(pdir(example))
    acq = os.path.basename(pdir(pdir(example)))
    sub = os.path.basename(pdir(pdir(pdir(example))))

    image_dest_folder = os.path.join(output_dir, sub, merged_pet_name, date, imageid)
    image_dest_path = os.path.join(image_dest_folder, merged_pet_name + '.nii.gz')

    print(f'  + [{i+1}/{n_quad}]')
    print(f'  + Source: {example}')
    print(f'  + Dest: {image_dest_path}')

    if os.path.isfile(image_dest_path) and not overwrite:
        print('  + Destination image already exists.')
        continue

    row = group.iloc[0, :]
    record = {
        'Subject': row['Subject'],
        'Sequence': row['Sequence'],
        'Date': row['Date'],
        'ImageID': row['ImageID'],
        'NIFTIPath': image_dest_path,
        'DICOMPath1': images[0],
        'DICOMPath2': images[1],
        'DICOMPath3': images[2],
        'DICOMPath4': images[3],
    }
    records.append(record)

    Path(image_dest_folder).mkdir(parents=True, exist_ok=True)
    print()
    print('++++++++++++++')
    merge_separated_dicom_frames(input_paths=images, output_path=image_dest_path)
    print('++++++++++++++')
    print()

record_df = pd.DataFrame(records)
record_df.to_csv(output_finallist, index=False)
print('> Saving record of new image paths.')
print(f"  + {output_finallist}")