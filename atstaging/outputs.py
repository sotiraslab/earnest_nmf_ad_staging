
import os

import pandas as pd

from atstaging.config import get
from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

def _dircreate(*args):
    path = os.path.join(*args)
    if not os.path.isdir(path):
        os.mkdir(path)
        
def load_master(master_folder=None, filters=True, features=True):

    if master_folder is None:
        odir = get('output_directory')
        master_folder = os.path.join(odir, 'masterTables')
    
    master_csv_path = os.path.join(master_folder, 'MASTER.csv')
    listdir = [os.path.join(master_folder, f) for f in os.listdir(master_folder) if f.lower().endswith('.csv')]
    features_csvs = sorted([f for f in listdir if os.path.basename(f).startswith('FEATURE')])
    filter_csvs = sorted([f for f in listdir if os.path.basename(f).startswith('FILTER')])

    print()
    print("* Loading master dataframe")

    print(f"    + Loading base from {master_csv_path}")
    master = pd.read_csv(master_csv_path, dtype={'Subject': str, 'Session': str})
    print("    + Complete.")

    if filters:
        print('* Applying filters.')
        print(f'    + Filters found: {[os.path.basename(f) for f in filter_csvs]}')
        for path in filter_csvs:
            print(f'    + Applying filter: {os.path.basename(path)}')
            lenbefore = len(master)
            tmpname = '__Keep__'
            filter_df = pd.read_csv(path, dtype={'Subject': str, 'Session': str, 'Keep': bool})
            filter_df = filter_df[['Subject', 'Session', 'Keep']].copy()
            filter_df.columns = ['Subject', 'Session', tmpname]
            master = master.merge(filter_df, on=['Subject', 'Session'], how='left')
            master = master[master[tmpname].astype(bool) & ~(master[tmpname].isna())].copy()
            master = master[[col for col in master.columns if col != tmpname]]
            lenafter = len(master)
            print(f'    + # Records before: {lenbefore}; after: {lenafter}')
        print('    + Complete')
    
    if features:
        print('* Adding features.')
        print(f'    + Features found: {[os.path.basename(f) for f in features_csvs]}')
        for path in features_csvs:
            print(f'    + Adding features: {os.path.basename(path)}')
            colsbefore = len(master.columns)
            feature_df = pd.read_csv(path , dtype={'Subject': str, 'Session': str})
            master = master.merge(feature_df, on=['Subject', 'Session'], how='left')
            colsafter = len(master.columns)
            print(f'    + # Features before: {colsbefore}; after: {colsafter}')
        print('    + Complete.')

    return master

def load_split(split='training', longitudinal='baseline', longitudinal_sub=None, split_column='Split'):
    
    master = load_master(filters=True, features=True)
    data_split_series = master[split_column]

    # validate
    if split is not None and split.lower() not in ['training', 'validation']:
        raise ValueError('`split` must be "training" or "validation", or None')
    
    if longitudinal is not None and longitudinal.lower() not in ['baseline', 'followup']:
        raise ValueError('`longitudinal` must be "baseline" or "followup", or None')
    
    if (longitudinal_sub is not None) and (longitudinal_sub not in ['A', 'B']):
        print(type(longitudinal_sub))
        raise ValueError('`longitudinal_sub` must be "A" or "B" or None')

    key_training = split.lower().capitalize() if split else ''
    key_longitudinal = longitudinal.lower().capitalize() if longitudinal else ''
    
    mask1 = data_split_series.str.contains(key_training)
    mask2 = data_split_series.str.contains(key_longitudinal)
    final_mask = mask1 & mask2

    if longitudinal_sub is not None:
        mask3 = master['SameTracerValidation' + longitudinal_sub]
        final_mask = final_mask & mask3

    data = master[final_mask]
    if data.empty:
        raise ValueError('Selection returned an empty dataframe!  Check parameters.')

    return data

def load_musestats(kind):

    if kind not in ['amyloid', 'tau']:
        raise ValueError('`kind` must be "amyloid" or "tau"')

    # locate output directory
    output_directory = get('output_directory')
    preproc_folder = os.path.join(output_directory, 'preprocessing', 'images')

    # load all the amyloid stats into one master table
    museall = []
    for dataset in os.listdir(preproc_folder):
        muse_path = os.path.join(output_directory, 'preprocessing', 'images', dataset, 'qc', f'musestats_{kind}.csv')
        if not os.path.isfile(muse_path):
            print(f'Cannot find amyloid MUSE stats for DataSet={dataset}; skipping.')
            continue

        muse_single_dataset = pd.read_csv(muse_path, dtype={'Subject':str, 'Session':str})
        museall.append(muse_single_dataset)

    muse = pd.concat(museall, ignore_index=True)
    return muse

def load_paths_tables(use_saved=True):
    output_directory = get('output_directory')
    preproc_dir = os.path.join(output_directory, 'preprocessing', 'images')

    # try loading the saved path if requested
    if use_saved:
        saved_path = os.path.join(output_directory, 'preprocessing', 'paths', 'paths.csv')
        if os.path.isfile(saved_path):
            print()
            print(f'Using paths table at "{saved_path}".')
            df = pd.read_csv(saved_path, dtype={'Subject': str, 'Session': str})
            return df
        else:
            print(f'No paths table found at "{saved_path}"; loading manually.')

    datasets = sorted(os.listdir(preproc_dir))
    output = []
    print()
    print('Manually reading paths folders:')
    for dataset in datasets:
        print(f'  > {dataset}...')
        path = os.path.join(preproc_dir, dataset, 'paths')
        if not os.path.isdir(path):
            continue
        df = paths_folder_to_dataframe(path)
        output.append(df)
    output = pd.concat(output)
    print('Done!')
    return output

def setup_outputs_folder(directory):
    _dircreate(directory)
    _dircreate(directory, 'amyloidpetnet')
    _dircreate(directory, 'amyloidpetnet', 'modeltmp')
    _dircreate(directory, 'datasetTables')
    _dircreate(directory, 'downloadLists')
    _dircreate(directory, 'nmf')
    _dircreate(directory, 'nmf', 'gmmask')
    _dircreate(directory, 'nmf', 'runs')
    _dircreate(directory, 'plots')
    _dircreate(directory, 'masterTables')
    _dircreate(directory, 'preprocessing')
    _dircreate(directory, 'preprocessing', 'images')
    _dircreate(directory, 'preprocessing', 'paths')
    _dircreate(directory, 'preprocessing', 'preproc_tables')
    _dircreate(directory, 'searches')
