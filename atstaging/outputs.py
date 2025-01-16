
import os

import pandas as pd

from atstaging.config import get

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
    features_csvs = [f for f in listdir if os.path.basename(f).startswith('FEATURE')]
    filter_csvs = [f for f in listdir if os.path.basename(f).startswith('FILTER')]

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
            filter_df.columns = ['Subject', 'Session', tmpname]
            master = master.merge(filter_df, on=['Subject', 'Session'])
            master = master[master[tmpname]].copy()
            master = master[[col for col in master.cols if col != tmpname]]
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

def setup_outputs_folder(directory):
    _dircreate(directory)
    _dircreate(directory, 'amyloidpetnet')
    _dircreate(directory, 'amyloidpetnet', 'modeltmp')
    _dircreate(directory, 'datasetTables')
    _dircreate(directory, 'downloadLists')
    _dircreate(directory, 'plots')
    _dircreate(directory, 'masterTables')
    _dircreate(directory, 'preprocessing')
    _dircreate(directory, 'preprocessing', 'images')
    _dircreate(directory, 'preprocessing', 'preproc_tables')
    _dircreate(directory, 'searches')
