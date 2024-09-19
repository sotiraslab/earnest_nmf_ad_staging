
import argparse
import os
import sys

import pandas as pd

from atstaging.config import get, set_config_automatic
from atstaging.preprocessing.mripreproc_bids import mripreproc_bids
from atstaging.preprocessing.execute import execute
from atstaging.printing import begin_command, end_command

BATCH_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preproc_mri_batch.sh')

def parse(arguments=None):

    usage = """
    
    Initiate batch processing of MRIs from an input table.
    The input table has a *specific* structure which cannot be changed.
    The following columns are required:
    
      - subject: subject identifier (used for BIDS outputs)
      - session: session identifier (user for BIDS outputs)
      - t1: path to the input T1 image for the given subject/session
      - output: output directory for each subject.  This can be the same for all rows
                but need not be.
                
    An error will be thrown if at least one of these columns is missing"""

    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('-i', '--input', required=True, help='Path to input table (CSV).', dest='table')
    parser.add_argument('-f', '--force', required=False, action='store_true',
                        help='Do not ask for confirmation before proceeding')
    parser.add_argument('--no-slurm', action='store_false', dest='slurm',
                        help="Do not use SLURM and instead run processing jobs serially.")
    
    args = parser.parse_args(arguments)
    return args

def _check_input_table(df):

    required = ['subject', 'session', 't1', 'output']
    missing = []
    for col in required:
        if col not in df.columns:
            missing.append(col)

    if missing:
        raise ValueError(f'Input table is missing one or more required columns: {missing}')
    
    else:
        return True

def run_mri_preproc_table(table, slurm=True, force=False):

    set_config_automatic()

    df = pd.read_csv(table)
    _check_input_table(df)
    nrows = len(df)

    print()
    print('BATCH MRI PROCESSING')
    print('- - - - - - - - - - ')
    print()
    print(f"Input table: {table}")
    print(f"Number of subjects: {nrows}")
    print(f'Using SLURM: {slurm}')

    ans = 'n'

    if not force:
        print()
        ans = input('Begin preprocessing? [y/n]')
        ans = ans.lower()
    else:
        ans = 'y'

    if ans == 'n':
        sys.exit()
    elif ans != 'y':
        print(f'Cannot understand answer "{ans}"; exiting.')
        sys.exit()

    for i, row in df.iterrows():
        subject = str(row['subject'])
        session = str(row['session'])
        t1 = str(row['t1'])
        output = str(row['output'])
            
        print()
        print(f'PROCESSING JOB {i+1}/{nrows}')
        print(f'  * subject={subject}')
        print(f'  * session={session}')
        print(f'  * t1={t1}')
        print(f'  * output={output}')
        print()
        tag = f"sub-{subject}_ses-{session}"
        begin_command(f'preproc: {tag}')
        if slurm:

            nodes = get('slurm', 'nodes')
            ntasks = get('slurm', 'ntasks')
            mem = get('slurm', 'mem')
            time = get('slurm', 'time')

            log_dir = os.path.join(output, 'logs')
            if not os.path.exists(log_dir):
                os.mkdir(log_dir)
            log_file = os.path.join(log_dir, f"{tag}.slurmlog")
            command = [
                "sbatch",
                "-J", tag,
                f"--output={log_file}",
                "--parsable",
                '-n', ntasks,
                '-N', nodes,
                f'--mem={mem}',
                '-t', time,
                BATCH_SCRIPT,
                '-i', t1,
                '-o', output,
                '-s', subject,
                '-S', session
            ]
            print()
            print('SBATCH call:')
            print(command)
        else:
            mripreproc_bids(input_img=t1, subject=subject, session=session, output_directory=output)
        end_command(f'preproc: {tag}')

def main():
    args = parse()
    run_mri_preproc_table(**vars(args))

if __name__ == '__main__':
    main()