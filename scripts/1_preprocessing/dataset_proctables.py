
import os

from atstaging.config import get, set_config
from atstaging.outputs import load_master, setup_outputs_folder

# config stuff
set_config('main')
OUTPUTDIRECTORY = get('output_directory')
setup_outputs_folder(OUTPUTDIRECTORY)

# read in master
# We want all subjects to be considered here, so get the master in the rawest format
master = load_master(filters=False, features=False)

# loop over datasets to create preproc tables
datasets = master['DataSet'].unique()
for dataset in datasets:

    print()
    print(dataset)
    print('-------')

    sub = master[master['DataSet'].eq(dataset)].copy()
    print(f'N subjects: {len(sub)}')

    # check for subjects with missing files
    def screen(col):
        output = []
        for x in col:
            if not x:
                output.append(False)
            else:
                output.append(os.path.exists(x))

        return output

    needed = sub[['PathT1', 'PathAmyloid', 'PathTau']].copy()
    filefound = needed.apply(screen)
    allfound = filefound.all(axis=1)
    n_good = allfound.sum().astype(int)
    n_bad = len(sub) - n_good

    if n_bad == 0:
        print('All files found for all subjects')
    else:
        print(f'Omitting {n_bad} subjects with at least one missing input image:')
        subses = 'sub-' + sub['Subject'] + '_' + sub['Session']
        if n_bad < 20:
            for x in subses:
                print(f'  - {subses}')
        else:
            print('  - [MORE THAN 20 CASES]')

    # this column needs to be set here to work
    sub['OutputDirectory'] = os.path.join(OUTPUTDIRECTORY, 'preprocessing', 'images', dataset)

    print()
    print('Saving to preproc tables folder')
    outpath = os.path.join(OUTPUTDIRECTORY, 'preprocessing', 'preproc_tables', f'{dataset}.csv')
    sub.to_csv(outpath, index=False)
    print(f'Done.  [{outpath}]')
