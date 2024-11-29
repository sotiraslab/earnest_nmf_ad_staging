
import argparse
import sys

import numpy as np
import pandas as pd

from atstaging.config import get, set_config_automatic
from atstaging.cli._slurm_pipeline import at_mri_pipeline_SLURM
from atstaging.preprocessing.pipeline import at_mri_pipeline

def parse(arguments=None):

    usage = """

    Initiate batch processing of subjects from an input table.
    The input table must provide the following information for each subject (i.e., in each row).

        - Subject identifier (Subject)
        - Session identifier (Session)
        - Output directory to direct derivatives to (OutputDirectory)
        - Path to a T1 image (PathT1)

    In addition, you can specify PET images to be processed:

        - Path to an amyloid-PET image (PathAmyloid)
        - Tracer name for the amyloid-PET image (TracerAmyloid) [FBP, FBB, PIB, NAV]
        - Path to an tau-PET image (PathTau)
        - Tracer name for the tau-PET image (TracerTau) [FTP, M62, P26]

    In the lists above, the names in parentheses are the default names expected for each of these
    fields in the column header.  However, these names can be set by altering the "tablecols" entry
    of the configuration JSON file.

    An error will be thrown if at least one of the expected columns is missing."""

    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('-i', '--input', required=True, help='Path to input table (CSV).', dest='table')
    parser.add_argument('-f', '--force', required=False, action='store_true',
                        help='Do not ask for confirmation before proceeding')
    parser.add_argument('--no-slurm', action='store_false', dest='slurm',
                        help="Do not use SLURM and instead run processing jobs serially.")
    parser.add_argument('-n', '--number', dest='slurm', default=None,
                        help="Only submit run the first n jobs (used for debugging).")

    args = parser.parse_args(arguments)
    return args

def _check_input_table_required(df):

    required_keys = ['subject', 'session', 'output_directory', 't1_img']
    config_columns = get('tablecols')
    missing = []

    for key in required_keys:
        column_name = config_columns[key]
        if column_name not in df.columns:
            missing.append(column_name)

    if missing:
        raise ValueError(f'The configuration file expects the following input columns: {required_keys}.'
                         f'The provided input table is missing one or more required columns: {missing}.')

    else:
        config_columns

def _report_processing(df):
    config_columns = get('tablecols')
    columns = df.columns

    t1_proc = False
    amy_proc = False
    tau_proc = False

    if config_columns['t1_img'] in columns:
        t1_proc = True
    if (config_columns['amyloid_img'] in columns) and (config_columns['amyloid_tracer'] in columns):
        amy_proc = True
    if (config_columns['tau_img'] in columns) and (config_columns['tau_tracer'] in columns):
        tau_proc = True

    print(f"Processing T1: {str(t1_proc).upper()}")
    print(f"Processing Amyloid-PET: {str(amy_proc).upper()}")
    print(f"Processing Tau-PET: {str(tau_proc).upper()}")

def run_at_preproc_table(table, slurm=True, force=False, number=None):

    set_config_automatic()

    df = pd.read_csv(table)
    columnmapping = _check_input_table_required(df)
    nrows = len(df)

    print()
    print('BATCH PROCESSING')
    print('- - - - - - - - ')
    print()
    print(f"Input table: {table}")
    print(f"Number of subjects: {nrows}")
    print(f'Using SLURM: {slurm}')
    _report_processing(df)

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

    if number is None:
        number = np.inf

    for i, row in enumerate(df.to_dict(orient="records")):

        if i >= number:
            print()
            print("!!! Reached number limit; stopping.")
            return

        # required arguments
        subject = row[columnmapping['subject']]
        session = row[columnmapping['session']]
        output_directory = row[columnmapping['output_directory']]
        t1_img = row[columnmapping['t1_img']]

        # optional arguments
        amyloid_img = row.get(columnmapping['amyloid_img'], None)
        amyloid_tracer = row.get(columnmapping['amyloid_tracer'], None)
        tau_img = row.get(columnmapping['tau_img'], None)
        tau_tracer = row.get(columnmapping['tau_tracer'], None)

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
                subject=subject,
                session=session,
                output_directory=output_directory,
                t1_img=t1_img,
                amyloid_img=amyloid_img,
                amyloid_tracer=amyloid_tracer,
                tau_img=tau_img,
                tau_tracer=tau_tracer,
                )
        else:
            at_mri_pipeline(
                subject=subject,
                session=session,
                output_directory=output_directory,
                t1_img=t1_img,
                amyloid_img=amyloid_img,
                amyloid_tracer=amyloid_tracer,
                tau_img=tau_img,
                tau_tracer=tau_tracer,
            )

def main():
    args = parse()
    run_at_preproc_table(**vars(args))

if __name__ == '__main__':
    main()
