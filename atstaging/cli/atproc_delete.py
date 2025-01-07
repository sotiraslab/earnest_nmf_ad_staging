
import argparse
from collections import Counter
import glob
import os
from os.path import join as pjoin
import pprint
import re
import shutil

import pandas as pd

from atstaging.preprocessing.bids import ATPreprocMRINamer, ATPreprocPETNamer
from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

TAU_TRACERS = ['FTP', 'M62', 'P26']
AMY_TRACERS = ['FBP', 'PIB', 'FBB', 'NAV']
DELETION_ROUTINES = ['anat', 'pet', 'extra']

def bids_files_value_count(files):
    names = [os.path.basename(f) for f in files]
    names = [re.sub('(?<=sub-)[a-zA-Z0-9]+(?=_)', '[SUB]', name) for name in names]
    names = [re.sub('(?<=ses-)[a-zA-Z0-9]+(?=_)', '[SES]', name) for name in names]

    counter = Counter(names)
    longest_name = max([len(name) for name in counter.keys()])
    for k, v in counter.items():
        print('  ' + k + (' ' * (longest_name - len(k))) + ' : ' + str(v))

def _delete_empty_directories(directory):

    if not os.path.isdir(directory):
        return

    children = os.listdir(directory)
    if children:
        return
    
    os.rmdir(directory)
    parent = os.path.dirname(directory)
    _delete_empty_directories(parent)
    
def delete_files_with_report(to_delete, dry_run=False, remove_empty_dirs=True, mode='os.remove'):

    if not len(to_delete):
        print()
        print('No files provided, exiting.')
    
    print()
    print('DATA DELETION')
    print('~~~~~~~~~~~~~')
    print(f'Number of items to delete: {len(to_delete)}')
    print('Unique item descriptors:')
    bids_files_value_count(to_delete)
    print()

    if dry_run:
        ans = input('This is a dry run; no files will actually be deleted.  Proceed? [y/n]')
    else:
        ans = input('This is NOT a dry run.  Files will be deleted if proceeding! Proceed? [y/n]')

    while True:
        if ans == 'y':
            break
        elif ans == 'n':
            return
        else:
            ans = input('Answer not recognized; please enter "y" or "n".')

    deletion_func = None
    if mode == 'os.remove':
        deletion_func = os.remove
    elif mode == 'shutil.rmtree':
        deletion_func = shutil.rmtree
    else:
        raise ValueError('`mode` must be "os.remove" or "shutil.rmtree".')

    print()
    for i, path in enumerate(to_delete):
        # printing helper
        pct = round(((i+1) / len(to_delete)) * 100, 2)
        header = '<DRYRUN> ' if dry_run else ''
        pct_str = f'({i+1}/{len(to_delete)}) [{pct}%]'

        # file not found - skip
        if not os.path.exists(path):
            print(f'Path {path} not found; skipping. {pct_str}')
            continue
        
        # file found
        print(f'{header}Removing {path}... {pct_str}')
        if not dry_run:
            deletion_func(path)
            parent_directory = os.path.dirname(path)
            if remove_empty_dirs:
                _delete_empty_directories(parent_directory)

def delete_preproc_by_bids(preproc_dir, names, values, same_file=False, dry_run=False, remove_empty_dirs=True):

    print()
    print("DELETING FILES BY BIDS")
    print('----------------------')

    if isinstance(names, str):
        names = [names]
    if isinstance(values, str):
        values = [values]

    if len(names) != len(values):
        raise ValueError('Must provide the same number of BIDS names and values.  User provided lengths are '
                         f'{len(names)} and {len(values)}, repsectively.')
    
    targets = []
    for name, value in zip(names, values):
        print(f'>>> Finding files matching {name}-{value}.')
        files = glob.glob(f'*/*/*/*{name}-{value}*', root_dir=preproc_dir)
        files = [os.path.join(preproc_dir, file) for file in files]
        targets.append(files)

    if same_file:
        print('>>> Filtering files to only include ones matching all provided patterns.')
        as_sets = [set(target) for target in targets]
        intersect = list(set.intersection(*as_sets))
        
        if not intersect:
            print('!!! No files found matching all patterns; exiting.')
            return
        
        delete_files_with_report(to_delete=intersect,
                                 dry_run=dry_run,
                                 remove_empty_dirs=remove_empty_dirs,
                                 mode='os.remove')
        
    else:
        for name, value, files in zip(names, values, targets):
            title = f'============= NAME: {name}, VALUE: {value} ============='
            end = '=' * len(title)
            print()
            print(title)
            if files:
                delete_files_with_report(files, dry_run=dry_run, remove_empty_dirs=remove_empty_dirs, mode='os.remove')
            else:
                print('No files matching the provided name-value pair; skipping.')
                continue
            print(end)

def delete_preproc_by_keys(preproc_dir, keys, modality=None, refresh=False,
                           dry_run=False, remove_empty_dirs=True):

    print()
    print("DELETING FILES BY KEYS")
    print('----------------------')

    if not refresh:
        print('>>> Loading paths JSON information from paths folder.')
        paths_folder= pjoin(preproc_dir, 'paths')
        pathtable = paths_folder_to_dataframe(paths_folder=paths_folder)
    else:
        print('>>> Manually creating path table by directory search.')
        pathtable = recreate_paths_table(preproc_dir)

    if modality is not None:
        keys = [modality + '_' + key for key in keys]

    print('>>> Beginning deletion of files by key.')

    for key in keys:
        title = f'================= KEY: {key} ================='
        end = '=' * len(title)
        print()
        print(title)
        if key in pathtable.columns:
            files = pathtable[key]
            delete_files_with_report(files, dry_run=dry_run, remove_empty_dirs=remove_empty_dirs)
        else:
            print(f'Pathtable has no entry for key "{key}" - skipping.')
            continue
        print(end)

def delete_preproc_by_routine(preproc_dir, routine, dry_run=False, remove_empty_dirs=True):

    print()
    print("DELETING FILES BY ROUTINE")
    print('-------------------------')

    files = []

    if routine == 'pet':
        print('>>> Deleting all PET outputs for all subjects.')
        files = glob.glob('*/*/pet', root_dir=preproc_dir)
        files = [os.path.join(preproc_dir, file) for file in files]
    elif routine == 'anat':
        print('>>> Deleting all anatomical outputs for all subjects.')
        files = glob.glob('*/*/anat', root_dir=preproc_dir)
        files = [os.path.join(preproc_dir, file) for file in files]
    elif routine == 'extra':
        print('>>> Deleting non-pipeline files.')
        # get a list of all images to keep
        paths_folder= pjoin(preproc_dir, 'paths')
        pathtable = paths_folder_to_dataframe(paths_folder=paths_folder)
        melted = pathtable.melt(id_vars=['Subject', 'Session'], var_name='Image', value_name='Path')
        keepimages = list(melted['Path'])

        # list of images to delete
        files = glob.glob('*/*/*/*', root_dir=preproc_dir)
        files = [os.path.join(preproc_dir, file) for file in files]

        # filter out
        files = [file for file in files if file not in keepimages]
    else:
        raise ValueError(f'Routine "{routine}" unrecognized; must be one of "{DELETION_ROUTINES}"')
    
    delete_files_with_report(to_delete=files, dry_run=dry_run, remove_empty_dirs=remove_empty_dirs, mode='shutil.rmtree')

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
    parser.add_argument('-D', '--dryrun', help='Dry run: nothing is actually deleted.', action='store_true')
    parser.add_argument('-E', '--empty', help='Remove empty directories created during deletion.', action='store_true')
    
    # mode == key
    parser.add_argument('-k', '--keys', help='For key deletion mode, key names of file to delete. One or more can be supplied.',
                        nargs='+', action='extend', dest='keys')
    h = ('For key deletion mode, specify that all deletion keys are indicating T1 images [t1], '
         'amyloid-PET images [amyloid], or tau-PET images [tau].  If not provided, '
         'user muse specify the modality key prior to each deletion key.')
    parser.add_argument('--keys-modality', help=h, required=False, default=None)
    parser.add_argument('--keys-refresh', help='Manually find the images matching keys, rather than using the paths folder JSON files',
                        required=False, action='store_true')
    parser.add_argument('--keys-list', help='List the acceptable keys and the images they target', action='store_true')
    
    # mode == bids
    parser.add_argument('-x', '--bids-name', help='For bids deletion mode, name of the BIDS field [NAME-VALUE].',
                        action='append')
    parser.add_argument('-y', '--bids-value', help='For bids deletion mode, name of the BIDS value [NAME-VALUE].',
                        action='append')
    parser.add_argument('--bids-samefile', help='Look for all the patterns to be matched in the same file.  Otherwise, patterns are interpreted separately.', action='store_true')
    
    # mode == routine
    parser.add_argument('-r', '--routine', help='Use a specified routine for deleting images.')

    args = parser.parse_args()
    return args

def _screen_args(args):

    meets_keyslist_mode = args.keys_list
    if meets_keyslist_mode:
        return "keys-list"

    meets_keysmode = args.keys is not None

    meets_bidsmode = False
    if args.bids_name is not None and args.bids_value is not None:
        meets_bidsmode = True
    elif args.bids_name is None and args.bids_value is None:
        meets_bidsmode = False
    else:
        raise ValueError('Must provide both BIDS name (-x, --bids-name) and value (-y, --bids-value), '
                         'not one or the other.')

    meets_routinemode = args.routine is not None

    allmodes = [meets_keysmode, meets_bidsmode, meets_routinemode]
    if sum(allmodes) == 0:
        raise ValueError('Must supply arguments for file deletion method; see usage for more details.')
    elif sum(allmodes) > 1:
        raise ValueError('Arguments supplied for more than one deletion mode; only one can be provided per call.')
    
    mode = ['keys', 'bids', 'routine'][allmodes.index(True)]
    return mode

def main():
    args = parse()
    mode = _screen_args(args)

    if mode == 'keys-list':
        print()
        print('T1 Keys')
        print('-------------------------------')
        namer = ATPreprocMRINamer(subject='SUB', session='SES', modality='anat')
        pprint.pprint(namer.namestore, sort_dicts=False)

        print()
        print('PET Keys')
        print('-------------------------------')
        namer = ATPreprocPETNamer(subject='SUB', session='SES', tracer='TRC', modality='pet')
        pprint.pprint(namer.namestore, sort_dicts=False)

        print()
        print('NOTE: For T1 keys, prepend "t1_"; for amyloid, prepend "amyloid_"; '
              'for tau, prepend "tau_".  Or instead, use the `--keys-modality` argument.')

        return
    
    folder = os.path.abspath(args.folder)

    if mode == 'keys':
        delete_preproc_by_keys(
            preproc_dir=folder,
            keys=args.keys,
            modality=args.keys_modality,
            refresh=args.keys_refresh,
            dry_run=args.dryrun,
            remove_empty_dirs=args.empty,
        )
    elif mode == 'bids':
        delete_preproc_by_bids(
            preproc_dir=folder,
            names=args.bids_name,
            values=args.bids_value,
            same_file=args.bids_samefile,
            dry_run=args.dryrun,
            remove_empty_dirs=args.empty,
        )
    elif mode == 'routine':
        delete_preproc_by_routine(
            preproc_dir=folder,
            routine=args.routine,
            dry_run=args.dryrun,
            remove_empty_dirs=args.empty
        )


    

