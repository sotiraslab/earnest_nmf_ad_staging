
import argparse
from collections import Counter
import os
from os.path import join as pjoin
import re

import pandas as pd

from atstaging.preprocessing.bids import ATPreprocMRINamer, ATPreprocPETNamer
from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

TAU_TRACERS = ['FTP', 'M62', 'P26']
AMY_TRACERS = ['FBP', 'PIB', 'FBB', 'NAV']

def bids_files_value_count(files):
    names = [os.path.basename(f) for f in files]
    names = [re.sub('(?<=sub-)[a-zA-Z0-9]+(?=_)', '[SUB]', name) for name in names]
    names = [re.sub('(?<=ses-)[a-zA-Z0-9]+(?=_)', '[SES]', name) for name in names]

    counter = Counter(names)
    longest_name = max([len(name) for name in counter.keys()])
    print('----------')
    for k, v in counter.items():
        print(k + (' ' * (longest_name - len(k))) + ' : ' + str(v))
    print('----------')
    
def delete_files_with_report(files, dry_run=False):
    
    ...


def delete_preproc_by_keys(preproc_dir, keys, modality=None, refresh=False):

    print()
    print("Deleting files by keys")
    print('----------------------')

    if not refresh:
        print()
        print('>>> Loading paths JSON information from paths folder.')
        paths_folder= pjoin(preproc_dir, 'paths')
        pathtable = paths_folder_to_dataframe(paths_folder=paths_folder)
    else:
        print()
        print('>>> Manually creating path table by directory search.')
        pathtable = recreate_paths_table(preproc_dir)

    if modality is not None:
        keys = [modality + '_' + key for key in keys]

    print('>>> Beginning deletion of files by key.')

    for key in keys:
        print()
        print(f'. . . . KEY={key} . . . .')
        if key in pathtable.columns:
            files = pathtable[key]
            delete_files_with_report(files)
        else:
            print(f'Pathtable has no entry for key "{key}" - skipping.')
            continue
        print(f'. . . . . . . . . . . . .')

def recreate_paths_table(processing_dir):

    rows = []

    for sub in os.listdir(processing_dir):
        sub_dir = pjoin(processing_dir, sub)
        if not os.path.isdir(sub_dir):
            continue
        if not sub.startswith('sub'):
            continue

        for ses in os.listdir(sub_dir):
            ses_dir = pjoin(sub_dir, ses)
            if not os.path.isdir(ses_dir):
                continue
            if not ses.startswith('ses'):
                continue

            subname = sub.removeprefix('sub-')
            sesname = ses.removeprefix('ses-')

            row = {}
            row['Subject'] = subname
            row['Session'] = sesname

            # add MRI names
            t1namer = ATPreprocMRINamer(subject=subname, session=sesname,
                                        directory=processing_dir)
            for name in t1namer.namestore.keys():
                row['t1_' + name] = t1namer.get_path(name)

            # find PET tracers
            pet_dir = pjoin(ses_dir, 'pet')
            if not os.path.isdir(pet_dir):
                rows.append(row)
                continue

            pet_files = pd.Series(os.listdir(pet_dir))
            trc_values = pet_files.str.extract('(trc-[A-Z0-0]{3})', expand=False).dropna()
            trc_values = trc_values.str.removeprefix('trc-')
            trc_unique = trc_values.unique()

            for trc in trc_unique:
                if trc in TAU_TRACERS:
                    pettype = 'tau'
                elif trc in AMY_TRACERS:
                    pettype = 'amyloid'
                else:
                    raise ValueError(f'Found images with tracer "{trc}", which is unrecognized. '
                                     f'Subject={subname}, Session={sesname}')
                petnamer = ATPreprocPETNamer(subject=subname,
                                             session=sesname,
                                             tracer=trc,
                                             modality='pet',
                                             directory=processing_dir)
                for name in petnamer.namestore.keys():
                    row[pettype + '_' + name] = petnamer.get_path(name)

            rows.append(row)

    pathtable = pd.DataFrame(rows)
    return pathtable
                
def parse():
    
    parser = argparse.ArgumentParser()

    # major arguments / affects everything
    parser.add_argument('folder', help='Directory with preprocessing outputs.')
    
    # mode == key
    parser.add_argument('-k', '--keys', help='For key deletion mode, key names of file to delete. One or more can be supplied.',
                        nargs='+', action='extend', dest='keys')
    h = ('For key deletion mode, specify that all deletion keys are indicating T1 images [t1], '
         'amyloid-PET images [amyloid], or tau-PET images [tau].  If not provided, '
         'user muse specify the modality key prior to each deletion key.')
    parser.add_argument('--keys-modality', help=h, required=False, default=None)
    parser.add_argument('--keys-refresh', help='Manually find the images matching keys, rather than using the paths folder JSON files',
                        required=False, action='store_true')
    
    # mode == bids
    parser.add_argument('-x', '--bids-name', help='For bids deletion mode, name of the BIDS field [NAME-VALUE].')
    parser.add_argument('-y', '--bids-value', help='For bids deletion mode, name of the BIDS value [NAME-VALUE].')
    parser.add_argument('--bids-regex', help='For bids deletion mode, interpret key as a regex expression.')
    
    # mode == routine
    parser.add_argument('-r', '--routine', help='Use a specified routine for deleting images.')

    args = parser.parse_args()
    return args

def main():

    args = parse()


    

