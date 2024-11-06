
import glob
import os
import pandas as pd

from atstaging.dataorg.utils import (
    get_bids_entities,
    get_shape
)

def _get_bids_json(oasis_image):
    nifti_dir = os.path.dirname(oasis_image)
    acq_dir = os.path.dirname(nifti_dir)
    bids_dir = os.path.join(acq_dir, 'BIDS')
    jsonfile = os.path.basename(oasis_image).removesuffix('.nii.gz') + '.json'
    fullpath = os.path.join(bids_dir, jsonfile)
    return fullpath

def oasis3_image_list(oasis3_directory):
    c = 0
    images = []

    print('OASIS3 IMAGE SEARCH ')
    print('~~~~~~~~~~~~~~~~~~~~~~~~')

    for subses in os.listdir(oasis3_directory):
        subses_dir = os.path.join(oasis3_directory, subses)
        if not os.path.isdir(subses_dir):
            continue

        if ('AV45' in subses) or ('PIB' in subses):
            kind = 'amyloid'
        elif 'MR' in subses:
            kind = 'mri'
        else:
            continue

        img_files = glob.glob('SCANS/*/NIFTI/*.nii.gz', root_dir=subses_dir)
        for file in img_files:
            fullfile = os.path.join(subses_dir, file)

            if (kind == 'mri') and 'T1w' not in file:
                continue

            data = {
                'path': fullfile,
                'json': _get_bids_json(fullfile)
            }
            data.update(get_bids_entities(fullfile))
            images.append(data)
        
        c += 1
        if (c % 500) == 0:
            print(f'Visited {c} directories...')

    print('Search complete.')
    df = pd.DataFrame(images)

    print()
    print(f'Found {len(df)} scans.')

    print()
    print('Getting image shapes for PET images...')

    global COUNTER
    COUNTER = 0

    def foo(row):
        global COUNTER
        COUNTER += 1

        if COUNTER % 1000 == 0:
            print(f'Row #{COUNTER}...')
        
        if row['modality'] == 'T1w':
            return None

        return get_shape(row['path'])

    df['shape'] = df.apply(foo, axis=1)
    print('Complete.')

    return df

def _tau_image_list_filter(imgpath):

    if not imgpath.endswith('.nii.gz'):
        return False, None

    shape = get_shape(imgpath)
    
    if shape is None:
        return False, shape

    if len(shape) not in [3, 4]:
        return False, shape

    if shape[0] != 256:
        return False, shape

    if (len(shape) == 4) and (shape[3] != 6):
        return False, shape

    return True, shape

def tau_image_list(oasis3tau_directory):
    c = 0
    images = []

    print('OASIS: TAU IMAGE SEARCH ')
    print('~~~~~~~~~~~~~~~~~~~~~~~~')
    for subses in os.listdir(oasis3tau_directory):
        subses_dir = os.path.join(oasis3tau_directory, subses)
        if not os.path.isdir(subses_dir):
            continue
    
        scans_dir = os.path.join(subses_dir, 'SCANS')
        for root, _, files in os.walk(scans_dir):
            for file in files:
                fullfile = os.path.join(root, file)
                
                okay, shape = _tau_image_list_filter(fullfile)
                if not okay:
                    continue
        
                data = {
                    'path': fullfile,
                    'shape': shape,
                    'megabytes': os.path.getsize(fullfile) / 1e6
                }
                data.update(get_bids_entities(fullfile))
                images.append(data)
        c += 1
        if (c % 50) == 0:
            print(f'Visited {c} directories...')
    
    print('Complete.')
    return pd.DataFrame(images)
