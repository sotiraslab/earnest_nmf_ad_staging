
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
gs2_allpet_search = '/scratch/tom.earnest/atstaging/searches/gs2_allpet_search.csv'
output_dir = '/ceph/chpc/shared/aristeidis_sotiras_group/aris_data/GS2/images/nifti/GS2/'
output_finallist = os.path.join(OUTPUT_FOLDER, 'downloadLists', 'gs2_nifti_images.csv')
overwrite = False
merged_pet_name = 'CONCATENATED_PET_IMAGE'

# main script
print('GS2 Image Reorganization')
pet = pd.read_csv(gs2_allpet_search, dtype={'Subject ID': str})

print('> Identifying amyloid scans which need merging')
pet['Subject'] = 'S' + pet['Subject ID']
pet['ScanDate'] = pd.to_datetime(pet['Study Date'])
pet['ImageID'] = 'I' + pet['Image ID'].astype(str)
prot = pet['Imaging Protocol'].str.removeprefix('Radiopharmaceutical=')
pet['Tracer'] = prot.map(
    {
        '18F-Flutemetamol': 'FMT',
        '18F-Florbetaben': 'FBB',
        '18F-Florbetapir': 'FBP',
        '18F-FDG': 'FDG',
        '18F-AV-1451': 'FTP'
    }
)
amy = pet[pet['Tracer'].isin(['FMT', 'FBB', 'FBP'])].copy()
amycount = amy.sort_values(['Subject', 'Description']).groupby(['Subject', 'ScanDate'])['Description'].count().reset_index()
amycount.columns = ['Subject', 'ScanDate', 'DuplicateCount']
amy = amy.merge(amycount, on=['Subject', 'ScanDate'], how='left')
n_single = sum(amy['DuplicateCount'].eq(1))
n_quad = sum(amy['DuplicateCount'].eq(4)) // 4
print(f'  + Single amyloid images: {n_single}')
print(f'  + Split amyloid images: {n_quad}')

# get list of downloaded images
print(f'> Finding images in {gs2_image_dir}')
loni = list_loni_images(gs2_image_dir)
print(f'  + Images found: {len(loni)}')

# separate loni into single conversions and quad conversions
print('> Splitting conversion jobs')
quads = amy[amy['DuplicateCount'].eq(4)].copy().sort_values(['Subject', 'Description'])
quads['QuadGroup'] = quads.groupby(['Subject', 'ScanDate']).ngroup()
merger = quads[['ImageID', 'QuadGroup']]
loni = loni.merge(merger, how='left', on='ImageID')
convert_single = loni[loni['QuadGroup'].isna()]
convert_quad = loni[~loni['QuadGroup'].isna()]
print(f'  + Single images: {len(convert_single)}')
print(f'  + Merge images: {len(convert_quad)/4} (4x images each)')

# begin image conversion
records = []

print('> Converting single images')
for i, (idx, row) in enumerate(convert_single.iterrows()):
    image = row['Path']
    imageid = os.path.basename(image)
    date = os.path.basename(pdir(image))
    acq = os.path.basename(pdir(pdir(image)))
    sub = os.path.basename(pdir(pdir(pdir(image))))

    image_dest_folder = os.path.join(output_dir, sub, acq, date, imageid)
    image_dest_name = acq
    image_dest_path = os.path.join(image_dest_folder, image_dest_name + '.nii.gz')
    
    print(f'  + [{i+1}/{len(convert_single)}]')
    print(f'  + Source: {image}')
    print(f'  + Dest: {image_dest_path}')

    record = {
        'Subject': row['Subject'],
        'Sequence': row['Sequence'],
        'Date': row['Date'],
        'ImageID': row['ImageID'],
        'NIFTIPath': image_dest_path,
        'DICOMPath1': row['Path'],
    }
    records.append(record)

    if os.path.isfile(image_dest_path) and not overwrite:
        print('  + Destination image already exists.')
        continue

    Path(image_dest_folder).mkdir(parents=True, exist_ok=True)
    run_dcm2niix(indir=image, outdir=image_dest_folder, name=image_dest_name, silent=True)

print('> Converting split images')
for i, (idx, group) in enumerate(convert_quad.groupby(['QuadGroup'])):
    
    images = sorted(group['Path'])
    example = images[0]
    imageid = os.path.basename(example)
    date = os.path.basename(pdir(example))
    acq = os.path.basename(pdir(pdir(example)))
    sub = os.path.basename(pdir(pdir(pdir(example))))

    image_dest_folder = os.path.join(output_dir, sub, merged_pet_name, date, imageid)
    image_dest_path = os.path.join(image_dest_folder, merged_pet_name + '.nii.gz')

    print(f'  + [{i+1}/{len(convert_quad)//4}]')
    print(f'  + Source: {example}')
    print(f'  + Dest: {image_dest_path}')

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

    if os.path.isfile(image_dest_path) and not overwrite:
        print('  + Destination image already exists.')
        continue

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