
import argparse

from atstaging.dataorg.utils import list_loni_images

def parse():

    parser = argparse.ArgumentParser()

    parser.add_argument('downloadFolder', help='Input folder of LONI downloads to search for images.')
    parser.add_argument('outputCSV', help='Output path to write CSV record')

    args = parser.parse_args()

    return args

def main():
    args = parse()
    df = list_loni_images(args.downloadFolder)
    df.to_csv(args.outputCSV, index=False)