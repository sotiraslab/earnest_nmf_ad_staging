import os

from colorama import Fore, Style
import matplotlib.pyplot as plt
import pandas as pd

from atstaging.config import get, set_config
from atstaging.outputs import setup_outputs_folder

# config stuff
set_config('main')

# variables
OUTPUTDIRECTORY = get('output_directory')
setup_outputs_folder(OUTPUTDIRECTORY)
MASTER_COLUMNS = [
    'DataSet', 'Subject', 'Session',
    'ScanDateTau', 'TracerTau', 'PathTau',
    'ScanDateAmyloid', 'TracerAmyloid', 'PathAmyloid',
    'ScanDateT1', 'PathT1',
    'TauAmyloidMeanDate',
    'Age', 'SexMale', 'HasE4', 'AmyloidPositive', 'CDR', 'CDRSumBoxes', 'CDRBinned',
    'Division'
]
    

# read in the datasets
datatable_dir = os.path.join(OUTPUTDIRECTORY, 'datasetTables')
dataset_paths = [os.path.join(datatable_dir, path) for path in os.listdir(datatable_dir) if path.lower().endswith('csv')]
datasets = {os.path.basename(path).removesuffix('.csv'): pd.read_csv(path, dtype={'CDRBinned': str, 'Subject': str}) for path in dataset_paths}

# validation function
def validate(df, name='< name not provided >'):

    LJUST = 40

    # individual test cases
    def _validate_columns():
        if not all([col in df.columns for col in MASTER_COLUMNS]):
            return False

        return True
        
    def _validate_dataset():
        if "DataSet" not in df.columns:
            return False
        dataset = df["DataSet"]

        if not dataset.str.isalnum().all():
            return False

        if not len(dataset.unique()) == 1:
            return False

        return True

    def _validate_subject():
        if not df['Subject'].str.isalnum().all():
            return False
        return True

    def _validate_session():
        if not df['Session'].str.isalnum().all():
            return False
        return True

    def _validate_unique():
        bidskey = 'sub-' + df['Subject'] + '_' + 'ses-' + df['Session']
        if len(bidskey.unique()) != len(df):
            return False
        return True
    
    results = []

    print()
    print(f'Validating datset: {Fore.YELLOW}{name}{Style.RESET_ALL}')
    print('========')

    res = _validate_columns()
    results.append(res)
    txt = (Fore.GREEN + Style.BRIGHT + 'PASS' + Style.RESET_ALL) if res else (Fore.RED + Style.BRIGHT + 'FAIL' + Style.RESET_ALL)
    print('  - All master columns found:'.ljust(LJUST), txt)

    res = _validate_dataset()
    results.append(res)
    txt = (Fore.GREEN + Style.BRIGHT + 'PASS' + Style.RESET_ALL) if res else (Fore.RED + Style.BRIGHT + 'FAIL' + Style.RESET_ALL)
    print('  - Dataset column formatted correctly:'.ljust(LJUST), txt)

    res = _validate_subject()
    results.append(res)
    txt = (Fore.GREEN + Style.BRIGHT + 'PASS' + Style.RESET_ALL) if res else (Fore.RED + Style.BRIGHT + 'FAIL' + Style.RESET_ALL)
    print('  - Subject is BIDS-compliant:'.ljust(LJUST), txt)

    res = _validate_session()
    results.append(res)
    txt = (Fore.GREEN + Style.BRIGHT + 'PASS' + Style.RESET_ALL) if res else (Fore.RED + Style.BRIGHT + 'FAIL' + Style.RESET_ALL)
    print('  - Session is BIDS-compliant:'.ljust(LJUST), txt)

    res = _validate_unique()
    results.append(res)
    txt = (Fore.GREEN + Style.BRIGHT + 'PASS' + Style.RESET_ALL) if res else (Fore.RED + Style.BRIGHT + 'FAIL' + Style.RESET_ALL)
    print('  - All subject/sessions are unique:'.ljust(LJUST), txt)

    if any(not res for x in results):
        raise ValueError('Validation failed for at least one requirement.')

# loop over datasets and validate
master = []
for name, dataset in datasets.items():

    # remove underscores in names
    dataset['Subject'] = dataset['Subject'].str.replace('_', '')

    # create a session field
    dataset['Session'] = pd.to_datetime(dataset['TauAmyloidMeanDate']).dt.strftime('%Y%m%d')

    # validate
    validate(dataset, name=name)

    print(Fore.YELLOW + str(len(dataset)) + Style.RESET_ALL + ' subjects')

    # proceed
    master.append(dataset[MASTER_COLUMNS].copy())

print()
print(Fore.GREEN + Style.BRIGHT + 'All datasets are passing.' + Style.RESET_ALL)

# create concatenated dataset
master = pd.concat(master, ignore_index=True)
print()
print('Created MASTER dataset with ' + Fore.BLUE + str(len(master)) + Style.RESET_ALL + ' scan sets.')

# save master
outpath = os.path.join(OUTPUTDIRECTORY, 'masterTables', 'MASTER.csv')
print()
print(f'Saving master dataset at "{outpath}".')
master.to_csv(outpath, index=False)

# master plot
def age_visit_plot(df):

    # configuration
    COLORS = {
        'ADNI': 'yellowgreen',
        'A4': 'steelblue',
        'OASIS': 'burlywood',
        'HABSHD': 'slategray',
        'HABS': 'firebrick',
        'GS1': 'plum',
        'GS2': 'darkviolet',
        'SCAN': 'darkblue'
    }
    AGEMIN = 40
    AGEMAX = 100

    fig = plt.figure(figsize=(8, 8))
    
    # assign group number
    df['GroupNo'] = df.groupby('Subject', sort=False).ngroup()
    df['Color'] = df['DataSet'].map(COLORS)
    
    # dots
    for index, frame in df.groupby('DataSet', sort=False):
        x = frame['Age']
        y = frame['GroupNo']
        color = frame['Color'].values[0]
        dataset = frame['DataSet'].values[0]
    
        plt.scatter(x, y, color=color, alpha=0.7, zorder=2, edgecolor='none', label=dataset)
    
    # lines
    for index, frame in df.groupby('Subject', sort=False):
        x = frame['Age']
        y = frame['GroupNo']
        color = frame['Color'].values[0]
        
        plt.plot(x, y, color=color, alpha=0.5, zorder=1)
    
    plt.legend()
    plt.xlim(AGEMIN, AGEMAX)
    plt.grid()
    plt.xlabel('Age')
    plt.ylabel('Subject Index')

    return fig

print()
print('Creating spaghetti plots...')
plotdata = master.copy().sort_values('Age')

# output directory
odir = os.path.join(OUTPUTDIRECTORY, 'plots', 'master_spaghetti')
if not os.path.isdir(odir):
    os.mkdir(odir)

# overall figure
fig = age_visit_plot(plotdata)
opath = os.path.join(odir, 'alldatasets.png')
fig.savefig(opath, dpi=300)

# by dataset
for dataset in plotdata['DataSet'].unique():
    df = plotdata[plotdata['DataSet'].eq(dataset)].copy()
    fig = age_visit_plot(df)
    opath = os.path.join(odir, f'{dataset}.png')
    fig.savefig(opath, dpi=300)
print(f'Done [{odir}]')