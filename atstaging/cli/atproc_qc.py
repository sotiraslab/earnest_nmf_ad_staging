
import argparse

from atstaging.preprocessing.qc_tools import setup_qc

def parse(arguments=None):

    parser = argparse.ArgumentParser(description='Generate QC information for a preprocessing directory',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('preproc_dir', help='Path to the output directory of preprocessing.')
    parser.add_argument('--rerun', help='Rerun any (costly) operations.', action='store_true')
    args = parser.parse_args(arguments)
    return args

def main():

    args = parse()
    rerun = args.rerun
    setup_qc(
        preproc_dir=args.preproc_dir,
        rerun_imagestats=rerun
        )

if __name__ == '__main__':
    main()