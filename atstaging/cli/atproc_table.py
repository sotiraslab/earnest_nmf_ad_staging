
import argparse
import os
import sys

import pandas as pd

from atstaging.config import get, set_config_automatic
from atstaging.cli._slurm_pipeline import at_mri_pipeline_SLURM
from atstaging.preprocessing.pipeline import at_mri_pipeline

def parse(arguments=None):

    usage = """

    Initiate batch processing of subjects from an input table.
    The input table must provide the following information for each subject (i.e., in each row):

        - Path to a T1 image (PathT1)
        - Path to an amyloid-PET image (PathAmyloid)
        - Tracer name for the amyloid-PET image (TracerAmyloid) [FBP, FBB, PIB, NAV]
        - Path to an tau-PET image (PathTau)
        - Tracer name for the tau-PET image (TracerTau) [FTP, M62, P26]
        - Subject identifier (Subject)
        - Session identifier (Session)
        - Output directory to direct derivatives to (OutputDirectory)

    In the list above, the names in parentheses are the default names expected for each of these
    fields in the column header.  However, these names can be set by altering the "tablecols" entry
    of the configuration JSON file.

    An error will be thrown if at least one of the expected columns is missing."""

    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('-i', '--input', required=True, help='Path to input table (CSV).', dest='table')
    parser.add_argument('-f', '--force', required=False, action='store_true',
                        help='Do not ask for confirmation before proceeding')
    parser.add_argument('--no-slurm', action='store_false', dest='slurm',
                        help="Do not use SLURM and instead run processing jobs serially.")

    args = parser.parse_args(arguments)
    return args

def _check_input_table(df):

    required = get('tablecols')
    missing = []
    for key, column_name in required.items():
        if column_name not in df.columns:
            missing.append(column_name)

    if missing:
        raise ValueError(f'The configuration file expects the following input columns: {required}.'
                         f'The provided input table is missing one or more required columns: {missing}.')

    else:
        required

def run_at_preproc_table(table, slurm=True, force=False):

    set_config_automatic()

    df = pd.read_csv(table)
    columns = _check_input_table(df)
    nrows = len(df)

    print()
    print('BATCH PROCESSING')
    print('- - - - - - - - ')
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
        subject = str(row[columns['subject']])
        session = str(row[columns['session']])

        t1_img = str(row[columns['t1_img']])
        amyloid_img = str(row[columns['amyloid_img']])
        amyloid_tracer = str(row[columns['amyloid_tracer']])
        tau_img = str(row[columns['tau_img']])
        tau_tracer = str(row[columns['tau_tracer']])

        output_directory = str(row[columns['output_directory']])

        print()
        print(f'PROCESSING JOB {i+1}/{nrows}')
        print(f'  * subject={subject}')
        print(f'  * session={session}')
        print(f'  * t1_img={t1_img}')
        print(f'  * amyloid_img={amyloid_img}')
        print(f'  * amyloid_tracer={amyloid_tracer}')
        print(f'  * tau_img={tau_img}')
        print(f'  * tau_tracer={tau_tracer}')
        print(f'  * output_directory={output_directory}')
        print()

        if slurm:
            at_mri_pipeline_SLURM(
                t1_img=t1_img,
                amyloid_img=amyloid_img,
                amyloid_tracer=amyloid_tracer,
                tau_img=tau_img,
                tau_tracer=tau_tracer,
                subject=subject,
                session=session,
                output_directory=output_directory
                )
        else:
            at_mri_pipeline(
                t1_img=t1_img,
                amyloid_img=amyloid_img,
                amyloid_tracer=amyloid_tracer,
                tau_img=tau_img,
                tau_tracer=tau_tracer,
                subject=subject,
                session=session,
                output_directory=output_directory
            )

def main():
    args = parse()
    run_at_preproc_table(**vars(args))

if __name__ == '__main__':
    main()
