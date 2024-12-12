
import argparse

from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

def parse():
    
    parser = argparse.ArgumentParser()

    parser.add_argument('folder', help='Directory with preprocessing outputs.')
    parser.add_argument('--delete', help='Key names of file to delete. One or more can be supplied.',
                        nargs='+', action='extend')
    
    args = parser.parse_args()
    return args

def main():

    args = parse()

    

