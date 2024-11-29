
import argparse

from atstaging.cli._slurm_pipeline import at_mri_pipeline_SLURM
from atstaging.preprocessing.pipeline import at_mri_pipeline

def parse(arguments=None):

    parser = argparse.ArgumentParser()

    parser.add_argument('--sub', required=True, dest='subject', help='BIDS subject for image.')
    parser.add_argument('--ses', required=True, dest='session', help='BIDS session for image.')
    parser.add_argument('--output', required=True, dest='output_directory', help='BIDS directory to create outputs')
    parser.add_argument('--t1', required=True, dest='t1_img', help='Input T1 image to preprocess.')
    parser.add_argument('--amyloid', required=False, dest='amyloid_img', help='Input aymloid PET image to preprocess.')
    parser.add_argument('--amyloid-tracer', required=False, dest='amyloid_tracer', help='Tracer code for amyloid PET image')
    parser.add_argument('--tau', required=False, dest='tau_img', help='Input tau PET image to preprocess.')
    parser.add_argument('--tau-tracer', required=False, dest='tau_tracer', help='Tracer code for tau PET image')
    parser.add_argument('--slurm', required=False, action='store_true', help='Use SLURM job submission for preprocessing.')

    args = parser.parse_args(args=arguments)

    return args

def main():
    args = parse()
    argsdict = vars(args)
    slurm = argsdict['slurm']
    del argsdict['slurm']
    
    if slurm:
        at_mri_pipeline_SLURM(**argsdict)
    else:
        at_mri_pipeline(**argsdict)