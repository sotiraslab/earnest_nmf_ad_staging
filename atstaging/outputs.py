
import os

import pandas as pd

from atstaging.config import get
from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

def _dircreate(*args):
    path = os.path.join(*args)
    if not os.path.isdir(path):
        os.mkdir(path)
        
def load_master(master_folder=None, filters=True, features=True, verbose=True):

    vprint = print if verbose else lambda *args, **kwargs: None

    if master_folder is None:
        odir = get('output_directory')
        master_folder = os.path.join(odir, 'masterTables')
    
    master_csv_path = os.path.join(master_folder, 'MASTER.csv')
    listdir = [os.path.join(master_folder, f) for f in os.listdir(master_folder) if f.lower().endswith('.csv')]
    features_csvs = sorted([f for f in listdir if os.path.basename(f).startswith('FEATURE')])
    filter_csvs = sorted([f for f in listdir if os.path.basename(f).startswith('FILTER')])

    vprint()
    vprint("* Loading master dataframe")

    vprint(f"    + Loading base from {master_csv_path}")
    master = pd.read_csv(master_csv_path, dtype={'Subject': str, 'Session': str})
    vprint("    + Complete.")

    if filters:
        vprint('* Applying filters.')
        vprint(f'    + Filters found: {[os.path.basename(f) for f in filter_csvs]}')
        for path in filter_csvs:
            vprint(f'    + Applying filter: {os.path.basename(path)}')
            lenbefore = len(master)
            tmpname = '__Keep__'
            filter_df = pd.read_csv(path, dtype={'Subject': str, 'Session': str, 'Keep': bool})
            filter_df = filter_df[['Subject', 'Session', 'Keep']].copy()
            filter_df.columns = ['Subject', 'Session', tmpname]
            master = master.merge(filter_df, on=['Subject', 'Session'], how='left')
            master = master[master[tmpname].astype(bool) & ~(master[tmpname].isna())].copy()
            master = master[[col for col in master.columns if col != tmpname]]
            lenafter = len(master)
            vprint(f'    + # Records before: {lenbefore}; after: {lenafter}')
        vprint('    + Complete')
    
    if features:
        vprint('* Adding features.')
        vprint(f'    + Features found: {[os.path.basename(f) for f in features_csvs]}')
        for path in features_csvs:
            vprint(f'    + Adding features: {os.path.basename(path)}')
            colsbefore = len(master.columns)
            feature_df = pd.read_csv(path , dtype={'Subject': str, 'Session': str})
            master = master.merge(feature_df, on=['Subject', 'Session'], how='left')
            colsafter = len(master.columns)
            vprint(f'    + # Features before: {colsbefore}; after: {colsafter} (nrows: {len(master)})')
        vprint('    + Complete.')

    return master

def load_split(split='training', longitudinal='baseline', validation_sub=None,
               split_column='Split', omit_control=False, verbose=True, master_folder=None):
    
    master = load_master(master_folder=master_folder, filters=True, features=True, verbose=verbose)
    data_split_series = master[split_column]

    # validate
    if split is not None and split.lower() not in ['training', 'validation']:
        raise ValueError('`split` must be "training" or "validation", or None')
    
    if longitudinal is not None and longitudinal.lower() not in ['baseline', 'followup']:
        raise ValueError('`longitudinal` must be "baseline" or "followup", or None')
    
    if (validation_sub is not None) and (validation_sub not in ['A', 'B', 'C']):
        print(type(validation_sub))
        raise ValueError('`validation_sub` must be "A", "B", "C", or None')

    key_training = split.lower().capitalize() if split else ''
    key_longitudinal = longitudinal.lower().capitalize() if longitudinal else ''
    
    mask1 = data_split_series.str.contains(key_training)
    mask2 = data_split_series.str.contains(key_longitudinal)
    final_mask = mask1 & mask2

    if validation_sub is not None:
        mask3 = master['SameTracerValidation' + validation_sub]
        final_mask = final_mask & mask3

    data = master[final_mask]
    if data.empty:
        raise ValueError('Selection returned an empty dataframe!  Check parameters.')
    
    if omit_control:
        print()
        print('Omitting controls using `ControlForStaging` column.')
        data = data[~data['ControlForStaging']].copy()

    return data

def load_subtyped_data(split='training', load_controls=False, include_longitudinal=False, sustain_model='auto'):

    if sustain_model == 'auto':
        sustain_model = split.capitalize()

    df = load_split(split=split, longitudinal='baseline', omit_control=False, verbose=False)
    if load_controls:
        df = df[df['ControlForStaging']].copy()
    else:
        # if not loading controls, assumes the Stage 0 individuals should be omitted
        sustain_stage_col = f'{sustain_model}MLStage'
        df = df[(~df['ControlForStaging']) & df[sustain_stage_col].ge(1)]
    
    if include_longitudinal:
        long = load_split(split=split, longitudinal=None, verbose=False, omit_control=False)
        include_indices = long.index.isin(df.index)
        include_subjects = long['Subject'].isin(df['Subject'].unique())
        output = long[include_indices | include_subjects].copy()
    else:
        output = df

    return output

# def load_subtyped_data(split='training', longitudinal='baseline', omit_control=True, verbose=False,
#                        omit_baseline_stage0=True, sustain_model='Training', **kwargs):
#     data = load_split(split=split, longitudinal=longitudinal, omit_control=omit_control, verbose=verbose, **kwargs)
#     if omit_baseline_stage0:
#         col = f'{sustain_model}MLStage'
#         data = data[~(data['Split'].str.contains('Baseline') & data[col].eq(0))].copy()
    
#     return data

def load_musestats(kind, output_directory=None):

    if kind not in ['amyloid', 'tau']:
        raise ValueError('`kind` must be "amyloid" or "tau"')

    # locate output directory
    if output_directory is None:
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

def load_paths_tables(use_saved=True, output_directory=None):
    if output_directory is None:
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
    _dircreate(directory, 'images')
    _dircreate(directory, 'longitudinalTables')
    _dircreate(directory, 'nmf')
    _dircreate(directory, 'nmf', 'gmmask')
    _dircreate(directory, 'nmf', 'runs')
    _dircreate(directory, 'nmf', 'tables')
    _dircreate(directory, 'plots')
    _dircreate(directory, 'masterTables')
    _dircreate(directory, 'preprocessing')
    _dircreate(directory, 'preprocessing', 'images')
    _dircreate(directory, 'preprocessing', 'paths')
    _dircreate(directory, 'preprocessing', 'preproc_tables')
    _dircreate(directory, 'searches')
    _dircreate(directory, 'sustain')
