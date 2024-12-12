
import argparse
import os

from atstaging.preprocessing.pipeline import paths_folder_to_dataframe

def deletion_table_from_pathtable(folder):

    paths_folder = os.path.join(folder_paths)
    pathtable = paths_folder_to_dataframe(paths_folder=paths_folder)

    

def delete_preproc_outputs_by_key(folder, keys, modality=None, manual_search=False):

    ...

def parse():
    
    parser = argparse.ArgumentParser()

    # major arguments / affects everything
    parser.add_argument('folder', help='Directory with preprocessing outputs.')
    parser.add_argument('-m', '--mode', help='Deletion mode [key, bids]')
    h = ('When specified, do not use the JSON files '
         'in the "paths" folder of the preprocessing outputs. '
         'Instead, use trawl the directory to find files to delete.')
    parser.add_argument('--manual-search', help=h, required=False,
                        dest='manual_search', action='store_true')
    
    # mode == key
    parser.add_argument('-k', '--keys', help='For key deletion mode, key names of file to delete. One or more can be supplied.',
                        nargs='+', action='extend', dest='keys')
    h = ('For key deletion mode, specify that all deletion keys are indicating T1 images [t1], '
         'amyloid-PET images [amyloid], or tau-PET images [tau].  If not provided, '
         'user muse specify the modality key prior to each deletion key.')
    parser.add_argument('--modality', help=h)
    
    # mode == bids
    parser.add_argument('-n', '--name', help='For bids deletion mode, name of the BIDS field [NAME-VALUE].')
    parser.add_argument('-v', '--value', help='For bids deletion mode, name of the BIDS value [NAME-VALUE].')
    parser.add_argument('--regex', help='For bids deletion mode, interpret key as a regex expression.')
    
    args = parser.parse_args()
    return args

def main():

    args = parse()


    

