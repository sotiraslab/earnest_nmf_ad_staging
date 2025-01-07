
import argparse

from atstaging.preprocessing.qc_tools import setup_qc

def parse(arguments=None):

    parser = argparse.ArgumentParser(description='Generate QC information for a preprocessing directory',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('preproc_dir', help='Path to the output directory of preprocessing.')
    args = parser.parse_args(arguments)
    return args

def main():

    args = parse()
    setup_qc(args.preproc_dir)

if __name__ == '__main__':
    main()