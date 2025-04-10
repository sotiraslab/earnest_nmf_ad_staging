
import glob
import os
import pickle
import textwrap
import warnings

import h5py
import matplotlib.pyplot as plt
import nibabel as nib
from nifti_overlay import NiftiOverlay
import numpy as np
import pandas as pd

from atstaging.config import get
from atstaging.preprocessing.execute import execute

_this_dir = os.path.abspath(os.path.dirname(__file__))
_NMFVolBin_Directory = os.path.join(_this_dir, 'NMFVolBin')
_NMFVolBinMask_Directory = os.path.join(_this_dir, 'NMFVolBinMask')

def load_nmf_runner(path):

    # if a folder is passed, assume it is the run output directory
    if os.path.isdir(path):
        path = os.path.join(path, 'NMFRunner.pickle')

    with open(path, 'rb') as file:
        runner = pickle.load(file)

    return runner

class NMFRunner:

    def __init__(self,
                 name: str,
                 master_table_path: str,
                 output_root_folder: str,
                 ranks: list = list(range(2, 21)),
                 master_table_path_column: str ='Path',
                 use_mask=False):

        self.name = name
        self.master_table_path = master_table_path
        self.master_table = pd.read_csv(self.master_table_path, dtype={'Subject': str, 'Session': str})
        self.output_root_folder = output_root_folder
        self.output_directory = os.path.join(self.output_root_folder, name)
        self.ranks = ranks
        self.use_mask = use_mask
        self.source_dir = _NMFVolBinMask_Directory if use_mask else _NMFVolBin_Directory
        self.master_table_path_column = master_table_path_column
    
        self.main_output_dir = os.path.join(self.output_directory, 'main')
        self.reproducibility_output_dir = os.path.join(self.output_directory, 'reproducibility')
        self.main_submission_script = os.path.join(self.main_output_dir, 'submit_extractBasesMT.sh')

        # reproducibility split objects set later
        self.reproducibility_splits_path = None
        self.reproducibility_splits = None
        self.n_reproducibility_splits = None
        self.split_columns = []

        # save
        self.pickle_path = os.path.join(self.output_directory, 'NMFRunner.pickle')
        with open(self.pickle_path, 'wb') as file:
            pickle.dump(self, file)

    def _dircreate(self, *args):
        path = os.path.join(*args)
        if not os.path.isdir(path):
            os.mkdir(path)

    def compress_niftis(self, delete=True, verbose=True):
        niis_relative = glob.glob('**/*.nii', root_dir=self.output_root_folder, recursive=True)
        niis_absolute = [os.path.join(self.output_root_folder, f) for f in niis_relative]
        for path in niis_absolute:
            nii = nib.load(path)
            nib.save(nii, path + '.gz')
            if verbose:
                print(f'  + Compressed {path}')
            del nii
            if delete:
                os.remove(path)

    def create_input_file_csv(self):
        input_csv_path = os.path.join(self.main_output_dir, 'inputFiles.csv')
        images = self.master_table[[self.master_table_path_column]]
        images.to_csv(input_csv_path, header=False, index=False)
        return input_csv_path
    
    def create_thresholded_components(self, range_threshold=0.2):
        results = self.get_main_resultsmats()
        for rank, mat in results.items():
            
            imat = mat
            omat = os.path.join(os.path.dirname(imat), f'ThresholdedResults{range_threshold}.mat')

            if os.path.isfile(omat):
                print(f'  + Existing output for rank={rank} [{omat}]')
            else:
                print(f'  + Thresholding rank={rank} [{mat}]')
                self.threshold_components_mat(imat=imat, omat=omat, range_threshold=range_threshold)

    def create_main_overlays(self):
        resultsmats = self.get_main_resultsmats()
        figuredirs = self.get_main_figure_directores()

        for k, mat in resultsmats.items():
            figuredir = figuredirs[k]
            outdir = os.path.join(figuredir, 'MainOverlays')
            self._dircreate(outdir)
            self.plot_results_mat(mat, odir=outdir)

    def create_submission_script(self, files_csv_path, nmf_output_dir, outpath):
        
        SCRIPT = """\
        #!/bin/bash
        
        # Use absolute paths!
        inFiles="{INFILES}"
        outputDir="{OUTPUTDIR}"
        scriptDir="{SCRIPTDIR}"
        ranks="{RANKS}"

        # submit master script
        for b in $ranks
        do
            mkdir -p ${{outputDir}}/NumBases${{b}}
            ${{scriptDir}}/create_submit_extractBasesMT.sh ${{inFiles}} ${{b}} ${{outputDir}} ${{scriptDir}}> ${{outputDir}}/NumBases${{b}}/submit_extractBasesMT.sh
            cd ${{outputDir}}/NumBases${{b}}
            sbatch ./submit_extractBasesMT.sh
        done	
        """

        SCRIPT = SCRIPT.format(
            INFILES=files_csv_path,
            OUTPUTDIR=nmf_output_dir,
            SCRIPTDIR=self.source_dir,
            RANKS=' '.join([str(k) for k in self.ranks])
        )
        SCRIPT = textwrap.dedent(SCRIPT)

        with open(outpath, 'w') as f:
            f.write(SCRIPT)

    def get_main_completion_by_rank(self):
        directories = self.get_main_num_bases_directories()
        result = {k: os.path.isfile(os.path.join(v, 'OPNMF', 'ResultsExtractBases.mat'))
                  for k, v in directories.items()}
        return result
    
    def get_main_figure_directores(self):
        numbases = self.get_main_num_bases_directories()
        return {k: os.path.join(v, 'OPNMF', 'Figures') for k, v in numbases.items()}

    def get_main_nii_directories(self):
        numbases = self.get_main_num_bases_directories()
        return {k: os.path.join(v, 'OPNMF', 'niiImg') for k, v in numbases.items()}
    
    def get_main_num_bases_directories(self):
        return {k : os.path.join(self.main_output_dir, f'NumBases{k}') for k in self.ranks}

    def get_main_resultsmats(self):
        numbases = self.get_main_num_bases_directories()
        return {k: os.path.join(v, 'OPNMF', 'ResultsExtractBases.mat') for k, v in numbases.items()}
    
    def plot_results_mat(self, mat, odir):

        mni_path = get('mni152_brain')
        mni = nib.load(mni_path)
        mni_affine = mni.affine
        mni_shape = mni.shape

        print(f'  + MAT file = {mat}')
        with h5py.File(mat) as file:
            W = np.array(file['B'])

        k, _ = W.shape
        for i in range(k):

            outpath = os.path.join(odir, f'Basis{i+1}.jpg')
            if os.path.isfile(outpath):
                print(f'    + Existing image for basis {i+1} [{outpath}]')

            else:
                print(f'    + Creating overlay for basis {i+1} [{outpath}]')
                data1d = W[i, :]
                data3d = np.reshape(data1d, shape=mni_shape, order='F')
                data_nii = nib.Nifti1Image(dataobj=data3d, affine=mni_affine)

                overlay = NiftiOverlay()
                overlay.add_anat('/home/tom.earnest/mni/MNI152_T1_1mm_brain.nii.gz')
                overlay.add_anat(data_nii, color='magma', alpha=.7)
                overlay.generate(outpath)
                plt.close()

    def post_main(self):

        range_threshold = 0.2
        
        print()
        print('POST-RUN NMF STEPS (Main)')
        print('-------------------------')

        print()
        print('> Compressing NIFTI images')
        self.compress_niftis(delete=True)
        print('> Done.')

        print()
        print(f'> Creating thresholded components [threshold={range_threshold}]')
        self.create_thresholded_components(range_threshold=range_threshold)
        print('> Done.')

        print()
        print(f'> Creating main component images')
        self.create_main_overlays()
        print('> Done.')
    
    def run_main(self, dry=False):

        print()
        print('+-----------+')
        print('|  NMF RUN  |')
        print('+-----------+')

        print()
        print('> Setting up necessary directories...')
        self.setup()
        print('Done.')

        print()
        print('> Creating input file CSV with image paths...')
        files_csv_path = self.create_input_file_csv()
        print(f'Done [{files_csv_path}].')

        print()
        print('> Creating submission script for main run...')
        self.create_submission_script(
            files_csv_path=files_csv_path,
            nmf_output_dir=self.main_output_dir,
            outpath=self.main_submission_script
            )
        print(f'Done [{self.main_submission_script}].')

        print()
        print('> Saving a copy of the input master CSV...')
        copy_master_path = os.path.join(self.output_directory, 'master_table.csv')
        self.master_table.to_csv(copy_master_path, index=False)
        print(f'Done [{copy_master_path}].')

        if dry:
            print()
            print('> DRYRUN: Reporting contents of submission script.')
            command = ['cat', self.main_submission_script]
        else:
            print()
            print('> Submitting run jobs.')
            command = ['/usr/bin/bash', self.main_submission_script]

        print()
        print('+------------ COMMAND RESULT ------------+')
        execute(command)
        print('+------------ COMMAND RESULT ------------+')

    def run_reproducibility(self, reproducibility_splits_path: str, dry: bool=False):

        print()
        print('+-------------------+')
        print('|  REPRODUCIBILITY  |')
        print('+-------------------+')

        print()
        print('> Setting up necessary directories...')
        self.setup()
        print('Done.')

        print()
        print('> Loading reproducibility splits CSV...')
        self.load_reproducibility_splits(reproducibility_splits_path=reproducibility_splits_path)
        print('Done.')

        print()
        print('> RESULT:')
        print(f'    + Path: {reproducibility_splits_path}')
        print(f'    + N subjects: {len(self.reproducibility_splits)}')
        print(f'    + N splits: {self.n_splits}')

        print()
        print('> Copying splits to reproducibility folder...')
        self.reproducibility_splits.to_csv(os.path.join(self.reproducibility_output_dir, 'splits.csv'), index=False)
        print('Done.')
        
        for i, col in enumerate(self.split_columns):

            name = f'Repeat{i+1}'
            repeat_directory = os.path.join(self.reproducibility_output_dir, name)
            split1_directory = os.path.join(repeat_directory, 'Split1')
            split2_directory = os.path.join(repeat_directory, 'Split2')
            self._dircreate(repeat_directory)
            self._dircreate(split1_directory)
            self._dircreate(split2_directory)

            print()
            print(f'=== REPEAT {i+1} ===')
            print(f' - {repeat_directory}')

            print()
            print('> Preparing split 1')
            mask1 = self.reproducibility_splits[col].eq(1).values
            input_images_1 = self.master_table.loc[mask1, self.master_table_path_column]
            input_path_1 = os.path.join(repeat_directory, 'split1_images.csv')
            input_images_1.to_csv(input_path_1, header=False, index=False)
            submit_script_1 = os.path.join(repeat_directory, 'submitSplit1.sh')
            print(f'> Done [{input_path_1}, {submit_script_1}]')
            self.create_submission_script(
                files_csv_path=input_path_1,
                nmf_output_dir=split1_directory,
                outpath=submit_script_1
                )
            
            if dry:
                print()
                print('!!! DRYRUN !!! Not submitting jobs.')
            else:
                print()
                print('> Submitting run jobs.')
                command = ['/usr/bin/bash', submit_script_1]

                print()
                print('+------------ COMMAND RESULT ------------+')
                execute(command)
                print('+------------ COMMAND RESULT ------------+')

            print()
            print('> Preparing split 2')
            mask2 = self.reproducibility_splits[col].eq(2).values
            input_images_2 = self.master_table.loc[mask2, self.master_table_path_column]
            input_path_2 = os.path.join(repeat_directory, 'split2_images.csv') 
            input_images_2.to_csv(input_path_2, header=False, index=False)
            submit_script_2 = os.path.join(repeat_directory, 'submitSplit2.sh')
            self.create_submission_script(
                files_csv_path=input_path_2,
                nmf_output_dir=split2_directory,
                outpath=submit_script_2
                )
            print(f'> Done [{input_path_2}, {submit_script_2}]')

            if dry:
                print()
                print('!!! DRYRUN !!! Not submitting jobs.')
            else:
                print()
                print('> Submitting run jobs.')
                command = ['/usr/bin/bash', submit_script_2]

                print()
                print('+------------ COMMAND RESULT ------------+')
                execute(command)
                print('+------------ COMMAND RESULT ------------+')

    def load_reproducibility_splits(self, reproducibility_splits_path):

        try:
            df = pd.read_csv(reproducibility_splits_path, dtype={'Subject': str, 'Session': str})
        except Exception:
            df = pd.read_csv(reproducibility_splits_path)
        
        # same length
        n_master = len(self.master_table)
        n_reproducibility = len(df)
        if n_master != n_reproducibility:
            raise ValueError(f'Length of reproducibility split table [{n_reproducibility}] does not match length of master [{n_master}]')
        
        # number of splits
        split_columns = [col for col in df.columns if col.startswith('Split')]
        n_splits = len(split_columns)
        if n_splits < 1:
            raise ValueError(f'Must provide at least 1 "Split" column for reproducibility splitting; found {n_splits}.')
        

        # assert 1/2
        just_splits = df[split_columns].copy()
        test = just_splits.eq(1) | just_splits.eq(2)
        if not test.all(axis=None):
            raise ValueError('Detected values other than `1` or `2` in splitting columns.')
        
        # order
        a = 'Subject' in self.master_table.columns
        b = 'Session' in self.master_table.columns
        c = 'Subject' in df.columns
        d = 'Session' in df.columns

        if not (a and b and c and d):
            warnings.warn(RuntimeWarning('Cannot find "Subject" and "Session" columns to check order of master & reproduciblity splits.'))

        test1 = np.all(self.master_table['Subject'].values == df['Subject'].values)
        test2 = np.all(self.master_table['Session'].values == df['Session'].values)

        if not test1:
            raise ValueError('Order of subjects does not match for master & reproduciblity splits.')
        
        if not test2:
            raise ValueError('Order of sessions does not match for master & reproduciblity splits.')
        
        # assign attributes
        self.reproducibility_splits_path = reproducibility_splits_path
        self.reproducibility_splits = df
        self.n_splits = n_splits
        self.split_columns = split_columns

    def setup(self):
        self._dircreate(self.output_root_folder)
        self._dircreate(self.output_directory)
        self._dircreate(self.main_output_dir)
        self._dircreate(self.reproducibility_output_dir)

    
    def threshold_components_mat(self, imat, omat, range_threshold=0.2):

        with h5py.File(imat) as f:
            W = np.array(f['B'])

        range_threshold = 0.2

        k, m = W.shape
        extents = W.max(axis=1) - W.min(axis=1)
        cutoffs = (extents * range_threshold) + W.min(axis=1)
        W_thresholded = np.where(W > cutoffs.reshape([k, 1]), W, 0)
        mdict = {'B': W_thresholded}

        with h5py.File(omat, 'w') as f:
            for key, value in mdict.items():
                f.create_dataset(key, data=value)


