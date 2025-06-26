
import glob
import os
import pickle
import textwrap
import warnings

import h5py
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import nibabel as nib
from nifti_overlay import NiftiOverlay
import numpy as np
import pandas as pd

from atstaging.config import get
from atstaging.plotting import freesurfer_cortical_colors, set_font_properties
from atstaging.preprocessing.execute import execute
from atstaging.nmf.utils import (
    assess_solution_similarity,
    load_image_with_downsample,
    load_results, 
    load_results_with_downsample, 
    plot_component_over_pet_average
)
_this_dir = os.path.abspath(os.path.dirname(__file__))
_NMFVolBin_Directory = os.path.join(_this_dir, 'NMFVolBin')
_NMFVolBinHighMem_Directory = os.path.join(_this_dir, 'NMFVolBinHighMem')
_NMFVolBinMask_Directory = os.path.join(_this_dir, 'NMFVolBinMask')

class NMFRunner:

    def __init__(self,
                 name: str,
                 master_table_path: str,
                 output_root_folder: str,
                 ranks: list = list(range(2, 21)),
                 master_table_path_column: str ='Path',
                 use_mask=False,
                 high_mem=False):

        self.name = name
        self.master_table_path = master_table_path
        self.master_table = pd.read_csv(self.master_table_path, dtype={'Subject': str, 'Session': str})
        self.output_root_folder = output_root_folder
        self.output_directory = os.path.join(self.output_root_folder, name)
        self.ranks = ranks
        self.master_table_path_column = master_table_path_column

        # source code
        self.use_mask = use_mask
        self.high_mem = high_mem
        if high_mem:
            self.use_mask = False
            self.source_dir = _NMFVolBinHighMem_Directory
        elif self.use_mask:
            self.source_dir = _NMFVolBinMask_Directory
        else:
            self.source_dir = _NMFVolBin_Directory
    
        self.main_output_dir = os.path.join(self.output_directory, 'main')
        self.reproducibility_output_dir = os.path.join(self.output_directory, 'reproducibility')
        self.main_submission_script = os.path.join(self.main_output_dir, 'submit_extractBasesMT.sh')
        self.analysis_dir = os.path.join(self.output_directory, 'analysis')

        # reproducibility split objects set later
        self.reproducibility_splits_path = None
        self.reproducibility_splits = None
        self.n_reproducibility_splits = None
        self.split_columns = []

        # cached objects
        self._X = None
        self._reconstruction_errors = None
        self._reproducibility_metrics = None

    def _dircreate(self, *args):
        path = os.path.join(*args)
        if not os.path.isdir(path):
            os.mkdir(path)

    def _updated_version(self):
        new = NMFRunner(
            name=self.name,
            master_table_path=self.master_table_path,
            output_root_folder=self.output_root_folder,
            ranks=self.ranks,
            master_table_path_column=self.master_table_path_column,
            use_mask=self.use_mask
        )

        return new

    def clear_cache(self):
        self._X = None
        self._reconstruction_errors = None
        self._reproducibility_metrics = None

    def create_basis_overlays_over_pet_average(self, path_average_pet, rank=None, vmin_pet=None, vmax_pet=None):
        results = self.get_main_resultsmats()
        figuredirs = self.get_main_figure_directores()

        if isinstance(rank, int):
            rank = [rank]
        elif rank is None:
            rank = list(results.keys())

        print()
        print(f'Path PET image: {path_average_pet}')
        print(f'Rank solutions being plotted: {rank}')

        for k in rank:

            print()
            print(f'> RANK = {k} ')
            print(f'  + MAT path: {results[k]}')
            print(f'  + Figure directory: {figuredirs[k]}')

            mat = results[k]
            figuredir = figuredirs[k]
            
            outdir = os.path.join(figuredir, 'MainOverlaysOnAvergePET')
            os.makedirs(outdir, exist_ok=True)

            for i in range(k):
                print(f'  + Plotting component {i+1} of {k}...')
                overlay = plot_component_over_pet_average(
                    mat=mat,
                    i=i,
                    path_pet=path_average_pet,
                    show_plot=False,
                    vmax_pet=vmax_pet,
                    vmin_pet=vmin_pet
                )
                overlay.generate(os.path.join(outdir, f'Basis{i+1}.jpg'))

    
    def compress_niftis(self, delete=True, verbose=True):
        niis_relative = glob.glob('**/*.nii', root_dir=self.output_directory, recursive=True)
        niis_absolute = [os.path.join(self.output_directory, f) for f in niis_relative]
        for path in niis_absolute:
            nii = nib.load(path)
            nib.save(nii, path + '.gz')
            if verbose:
                print(f'  + Compressed {path}')
            del nii
            if delete:
                os.remove(path)

    def compute_loadings_array(self, rank, images, normalize=True):
        results = self.get_main_resultsmats()
        mat = results[rank]

        W, _ = load_results(mat, transpose=True)

        if normalize:
            W /= W.sum(axis=0)

        n = len(images)
        output = np.zeros((n, rank))

        print()
        print(f'> Beginning main loop to derive loadings for {n} images.')
        print()

        for i, image in enumerate(images):
            print(f'  + [{i+1}/{n}] {image}')
            nii = nib.load(image)
            data3d = nii.get_fdata()
            data1d = data3d.flatten(order='F')
            vsize = len(data1d)
            loadings = np.matmul(data1d.reshape((1, vsize)), W)
            output[i, :] = loadings

        return output
    
    def compute_loadings_dataframe(self, rank, images, keep_indices=None, keep_names=None, normalize=True, prefix='', suffix=''):
        if keep_indices is None:
            keep_indices = list(range(rank))
        if keep_names is None:
            keep_names = [f'Component{i}' for i in range(1, len(keep_indices)+1)]
        if len(keep_indices) != len(keep_names):
            raise ValueError('Length of selected component indices and names must be the same.')
        
        loadings = self.compute_loadings_array(rank=rank, images=images, normalize=normalize)
        selected_loadings = loadings[:, keep_indices]
        df = pd.DataFrame(selected_loadings)
        df.columns = keep_names
        df.columns = prefix + df.columns + suffix
        return df
                
    def construct_X(self, downsample_factor=1, dtype='single', order='F'):
        
        images = self.get_training_images_list()
        n = len(images)
        m = len(load_image_with_downsample(images[0], downsample_factor=downsample_factor, order=order))
        dtype = np.dtype(dtype)
        itemsize_bytes = dtype.itemsize

        estimated_size_bytes = n * m * itemsize_bytes
        estimated_size_gb = round(estimated_size_bytes / 1e9, 2)

        print()
        print('> Beginning construction of X matrix')
        print(f'  ! N: {n}')
        print(f'  ! M (with downsampling={downsample_factor}): {m}')
        print(f'  ! Estimated memory usage of X [NxM]: {estimated_size_gb}GB')
        print(f'  ! Reconstuction error analyses require at least 2x this size ({2*estimated_size_gb}GB)')

        X = np.zeros((m, n), dtype=dtype)

        for i, path in enumerate(images):

            end = '\n' if (i == (n-1)) else '\r'            
            print(f'  + [{i+1}/{n}] {path}', end=end)
            
            data = load_image_with_downsample(path=path, downsample_factor=downsample_factor, order=order)
            X[:, i] = data

        print('Complete.')            
        return X

    def create_input_file_csv(self):
        input_csv_path = os.path.join(self.main_output_dir, 'inputFiles.csv')
        images = self.master_table[[self.master_table_path_column]]
        images.to_csv(input_csv_path, header=False, index=False)
        return input_csv_path
    
    def create_thresholded_components(self, range_threshold=0.2, create_figures=True):
        results = self.get_main_resultsmats()
        figuredirs = self.get_main_figure_directores()
        for rank, mat in results.items():
            
            imat = mat
            omat = os.path.join(os.path.dirname(imat), f'ThresholdedResults{range_threshold}.mat')

            if os.path.isfile(omat):
                print(f'  + Existing output for rank={rank} [{omat}]')
            else:
                print(f'  + Thresholding rank={rank} [{mat}]')
                self.threshold_components_mat(imat=imat, omat=omat, range_threshold=range_threshold)

            # plot
            if create_figures:
                figuredir = figuredirs[rank]
                thisoutdir = os.path.join(figuredir, f'ThresholdedOverlays{range_threshold}')
                self._dircreate(thisoutdir)
                self.plot_results_mat(omat, thisoutdir)


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

    def delete_niftis(self, verbose=True):
        niis_relative = glob.glob('**/*.nii', root_dir=self.output_directory, recursive=True)
        niigzs_relative = glob.glob('**/*.nii.gz', root_dir=self.output_directory, recursive=True)
        niis_absolute = [os.path.join(self.output_directory, f) for f in niis_relative]
        niigzs_absolute = [os.path.join(self.output_directory, f) for f in niigzs_relative]

        all_images_absolute = niis_absolute + niigzs_absolute
        n = len(all_images_absolute)

        if verbose:
            print(f'  + FOUND {n} IMAGES.')

        for i, path in enumerate(all_images_absolute):
            if verbose:
                print(f'  + Deleting [{i+1}/{n}] {path}')
            os.remove(path)

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
    
    def get_reproducibility_completion_status(self, show_only_incomplete=False):
        output = {}

        for repeat, split, rank in self.iterate_reproducibility_indices():
            results_path = os.path.join(
                self.reproducibility_output_dir,
                f'Repeat{repeat}',
                f'Split{split}',
                f'NumBases{rank}',
                'OPNMF',
                'ResultsExtractBases.mat')
            complete = os.path.isfile(results_path)

            if show_only_incomplete and complete:
                continue

            key = f"Repeat{repeat}-Split{split}-NumBases{rank}"
            output[key] = complete

        output = {k:output[k] for k in sorted(output.keys())}

        return output

    def get_training_images_list(self):
        return list(self.master_table[self.master_table_path_column])
    
    def get_voxel_dimensions(self):
        images = self.get_training_images_list()
        example = images[0]
        nii = nib.load(example)
        return nii.shape
    
    def iterate_reproducibility_indices(self):
        n_repeats = len([f for f in os.listdir(self.reproducibility_output_dir) if f.startswith('Repeat')])

        for repeat in range(1, n_repeats + 1):
            for split in [1, 2]:
                for rank in self.ranks:
                    yield repeat, split, rank

    def iterate_reproducibility_paired_split_results(self):
        n_repeats = len([f for f in os.listdir(self.reproducibility_output_dir) if f.startswith('Repeat')])

        for repeat in range(1, n_repeats+1):
            for rank in self.ranks:
                results1 = os.path.join(
                    self.reproducibility_output_dir, f'Repeat{repeat}', 'Split1', f'NumBases{rank}', 'OPNMF', 'ResultsExtractBases.mat'
                )
                results2 = os.path.join(
                    self.reproducibility_output_dir, f'Repeat{repeat}', 'Split2', f'NumBases{rank}', 'OPNMF', 'ResultsExtractBases.mat'
                )

                yield repeat, rank, results1, results2
    
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
                overlay.add_anat(mni_path)
                overlay.add_anat(data_nii, color='magma', alpha=.7)
                overlay.generate(outpath)
                plt.close()

    def post_main(self):

        range_threshold = 0.2
        
        print()
        print('POST-RUN NMF STEPS (Main)')
        print('-------------------------')

        print()
        print('> Deleting basis images (NIFTI)')
        self.delete_niftis()
        print('> Done.')

        print()
        print(f'> Creating thresholded components [threshold={range_threshold}]')
        self.create_thresholded_components(range_threshold=range_threshold, create_figures=False)
        print('> Done.')

        print()
        print('> Creating main component images')
        self.create_main_overlays()
        print('> Done.')
        
    def reconstruction_error_analysis(self, downsample_factor=2, dtype='single', order='F', save_X=False):
        
        results_by_rank = self.get_main_resultsmats()
        
        print()
        print('RECONSTRUCTION ERROR ANALYSIS')
        print('==============')
        
        # 1. Recreate the X input matrix
        # This can take a lot of memory !
        # Downsampling/dtype can be used to ameliorate this
        print()
        print('STEP 1: CONSTRUCT X')

        if self._X is not None:
            print()
            print(f'> Using cached X matrix [{self._X.shape}, {self._X.nbytes / 1e9}GB]')
            X = self._X
        else:
            X = self.construct_X(downsample_factor=downsample_factor,
                                dtype=dtype,
                                order=order)
            self._X = X

        # 2. For each rank, load the results and reconstruction
        print()
        print('STEP 2: COMPUTE RECONSTRUCTION ERRORS')
        
        if self._reconstruction_errors is not None:
            print()
            print('> Using cached reconstruction errors')
            reconstruction_errors = self._reconstruction_errors
        else:
            reconstruction_errors = []
            
            # we need to know the registered image dimensions to help with the resampling
            # This could be gotten from the training images themselves
            # but for my purposes this should always be consistent
            mni_path = get('mni152_brain')
            mni = nib.load(mni_path)
            mni_shape = mni.shape
            
            print()
            print('> Looping over ranks to load components (W) and loadings (H).')
            for k, mat in results_by_rank.items():
                print(f'    + Rank={k} [{mat}]')
                W, H = load_results_with_downsample(
                    path_mat=mat,
                    voxel_dim=mni_shape,
                    downsample_factor=downsample_factor,
                    order=order,
                    dtype=dtype,
                    transpose=True
                    )
                recon = np.matmul(W, H)
                norm = np.linalg.norm(X - recon, ord='fro')
                reconstruction_errors.append(norm)
                print(f'      + Norm={norm}')

            self._reconstruction_errors = np.array(reconstruction_errors)
            
            
        # 2. For each rank, load the results and reconstruction
        print()
        print('STEP 3: SAVE')
        
        OUTDIR = os.path.join(self.analysis_dir, 'reconError')
        self.setup()
        self._dircreate(OUTDIR)
        
        print()
        print(f'Saving results in: {OUTDIR}')
            
        # save as a dataset
        print()
        print('> Creating dataframe with reconstruction errors.')
        df = pd.DataFrame({'k': self.ranks,
                           'reconstruction_error': reconstruction_errors})
        outpath = os.path.join(OUTDIR, 'reconstruction_errors.csv')
        df.to_csv(outpath, index=False)
        print(f'> Done [{outpath}].')

        # Save X
        if save_X:
            print()
            print('> Saving X matrix.')
            outpath = os.path.join(OUTDIR, 'X.npy')
            np.save(outpath, X)
            print(f'> Done [{outpath}].')

        # Plots
        set_font_properties()

        # 1. Recon Error
        plt.figure(figsize=(8, 6))
        x = self.ranks
        y = reconstruction_errors
        plt.plot(x, y, color='red')
        plt.xticks(x)
        plt.xlabel('Rank')
        plt.ylabel('Reconstruction Error')
        plt.title('Reconstruction error for different NMF ranks')
        plt.grid()

        outpath = os.path.join(OUTDIR, 'reconstruction_error.png')
        plt.savefig(outpath, dpi=300)

        # 2. Gradient recon error
        plt.figure(figsize=(8, 6))
        x = self.ranks[:-1]
        y = np.diff(reconstruction_errors)
        plt.plot(x, y, color='red')
        plt.xticks(x)
        plt.xlabel('Rank')
        plt.ylabel('Reconstruction Error')
        plt.title('Gradient of reconstruction error over different NMF ranks')
        plt.grid()

        outpath = os.path.join(OUTDIR, 'gradient_reconstruction_error.png')
        plt.savefig(outpath, dpi=300)

    def reproducibility_analysis(self, verbose=True):
        
        print()
        print('REPRODUCIBILITY ANALYSIS')
        print('==============')
        
        OUTDIR = os.path.join(self.analysis_dir, 'reproducibility')
        self.setup()
        self._dircreate(OUTDIR)

        # Load/compute reproducibility statistics
        path_repro_stats = os.path.join(OUTDIR, 'reproducibility_metircs.csv')

        if os.path.isfile(path_repro_stats):
            print()
            print(f'> Loading existing statistics [{path_repro_stats}].')
            df = pd.read_csv(path_repro_stats)

        else:
            print()
            print('> No existing statistics found, computing...')

            rows = []

            for repeat, rank, results1, results2 in self.iterate_reproducibility_paired_split_results():
                metrics = assess_solution_similarity(
                    mat1=results1,
                    mat2=results2
                )
                row = {
                    'Repeat': repeat,
                    'Rank': rank,
                    'MeanInnerProduct': metrics['mean_inner_product'],
                    'MedianInnerProduct': metrics['median_inner_product'],
                    'ARI': metrics['adjusted_rand_index'],
                    'ARINonZero': metrics['adjusted_rand_index_nonzero'],
                    'MeanPearson': metrics['mean_person_correlation'],
                    'MedianPearson': metrics['median_pearson_correlation']
                }
                rows.append(row)
                if verbose:
                    print(row)

            df = pd.DataFrame(rows)
            df.to_csv(path_repro_stats, index=False)

        self._reproducibility_metrics = df

        # Plots
        set_font_properties()

        # 1. Mean inner product
        col = 'MeanInnerProduct'
        mean = df.groupby('Rank')[col].mean()
        std = df.groupby('Rank')[col].std()
        x = mean.index
        y = mean.values
        e = std.values
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, color='blue')
        plt.fill_between(x, y-e, y+e, alpha=0.1, color='blue', edgecolor='none')
        plt.xticks(x)
        plt.grid()
        plt.xlabel('Rank')
        plt.ylabel('Mean inner product')

        outpath = os.path.join(OUTDIR, 'mean_inner_product.png')
        plt.savefig(outpath, dpi=300)

        # 2. Median inner product
        col = 'MedianInnerProduct'
        mean = df.groupby('Rank')[col].mean()
        std = df.groupby('Rank')[col].std()
        x = mean.index
        y = mean.values
        e = std.values
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, color='blue')
        plt.fill_between(x, y-e, y+e, alpha=0.1, color='blue', edgecolor='none')
        plt.xticks(x)
        plt.grid()
        plt.xlabel('Rank')
        plt.ylabel('Median inner product')

        outpath = os.path.join(OUTDIR, 'median_inner_product.png')
        plt.savefig(outpath, dpi=300)

        # 3. ARI
        col = 'ARI'
        mean = df.groupby('Rank')[col].mean()
        std = df.groupby('Rank')[col].std()
        x = mean.index
        y = mean.values
        e = std.values
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, color='blue')
        plt.fill_between(x, y-e, y+e, alpha=0.1, color='blue', edgecolor='none')
        plt.xticks(x)
        plt.grid()
        plt.xlabel('Rank')
        plt.ylabel('Adjusted Rand Index')

        outpath = os.path.join(OUTDIR, 'ari.png')
        plt.savefig(outpath, dpi=300)
    
        # 4. ARI
        col = 'ARINonZero'
        mean = df.groupby('Rank')[col].mean()
        std = df.groupby('Rank')[col].std()
        x = mean.index
        y = mean.values
        e = std.values
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, color='blue')
        plt.fill_between(x, y-e, y+e, alpha=0.1, color='blue', edgecolor='none')
        plt.xticks(x)
        plt.grid()
        plt.xlabel('Rank')
        plt.ylabel('Adjusted Rand Index (NonZero)')

        outpath = os.path.join(OUTDIR, 'ari_nonzero.png')
        plt.savefig(outpath, dpi=300)

        # 5. Mean Pearson correlation
        col = 'MeanPearson'
        mean = df.groupby('Rank')[col].mean()
        std = df.groupby('Rank')[col].std()
        x = mean.index
        y = mean.values
        e = std.values
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, color='blue')
        plt.fill_between(x, y-e, y+e, alpha=0.1, color='blue', edgecolor='none')
        plt.xticks(x)
        plt.grid()
        plt.xlabel('Rank')
        plt.ylabel('Mean Pearson correlation')

        outpath = os.path.join(OUTDIR, 'mean_pearson.png')
        plt.savefig(outpath, dpi=300)

        # 6. Median Pearson correlation
        col = 'MedianPearson'
        mean = df.groupby('Rank')[col].mean()
        std = df.groupby('Rank')[col].std()
        x = mean.index
        y = mean.values
        e = std.values
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, color='blue')
        plt.fill_between(x, y-e, y+e, alpha=0.1, color='blue', edgecolor='none')
        plt.xticks(x)
        plt.grid()
        plt.xlabel('Rank')
        plt.ylabel('Median Pearson correlation')

        outpath = os.path.join(OUTDIR, 'median_pearson.png')
        plt.savefig(outpath, dpi=300)

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
        print('> Saving pickle of NMF Runner...')
        pickle_path = self.pickle()
        print(f'> Done [{pickle_path}]')

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

    def pickle(self):
        pickle_path = os.path.join(self.output_directory, 'NMFRunner.pickle')
        with open(pickle_path, 'wb') as file:
            pickle.dump(self, file)

        return pickle_path

    def setup(self):
        self._dircreate(self.output_root_folder)
        self._dircreate(self.output_directory)
        self._dircreate(self.main_output_dir)
        self._dircreate(self.reproducibility_output_dir)
        self._dircreate(self.analysis_dir)
    
    def threshold_components_mat(self, imat, omat, range_threshold=0.2):

        W, _ = load_results(imat, transpose=False)

        range_threshold = 0.2

        k, m = W.shape
        extents = W.max(axis=1) - W.min(axis=1)
        cutoffs = (extents * range_threshold) + W.min(axis=1)
        W_thresholded = np.where(W > cutoffs.reshape([k, 1]), W, 0)
        mdict = {'B': W_thresholded}

        with h5py.File(omat, 'w') as f:
            for key, value in mdict.items():
                f.create_dataset(key, data=value)

    def winner_take_all_analysis(self):
        print()
        print('WINNER TAKE ALL ANALYSIS')
        print('==============')

        # 1. Load

        OUTDIR = os.path.join(self.analysis_dir, 'winnerTakeAll')
        self.setup()
        self._dircreate(OUTDIR)

        wta_mat = os.path.join(OUTDIR, 'stacked_WTA_assignments.mat')

        if os.path.isfile(wta_mat):
            print()
            print(f'> Loading existing winner take all assignments... [{wta_mat}]')
            with h5py.File(wta_mat, 'r') as f:
                stacked_wta = np.array(f['WTA'])
        else:
            print()
            print('No existing winner take all assignments found; computing.')

            m = np.prod(self.get_voxel_dimensions())
            n_ranks = len(self.ranks)
            stacked_wta = np.zeros((m, n_ranks))
            
            results_by_rank = self.get_main_resultsmats()
            for i, (rank, results) in enumerate(results_by_rank.items()):
                print(f'  + Processing rank={rank} [{results}]')
                W, _ = load_results(results)
                zeromask = np.all(W == 0, axis=1)
                W_unit = W / np.sqrt(np.sum(W ** 2, axis=0))
                wta = W_unit.argmax(axis=1)
                stacked_wta[:, i] = np.where(zeromask, 0, wta + 1)

            # save the statistics
            print()
            print('> Saving...')
            mdict = {'WTA': stacked_wta,
                    'ranks': np.array(self.ranks, dtype=int)}
            print()
            with h5py.File(wta_mat, 'w') as f:
                for key, value in mdict.items():
                    f.create_dataset(key, data=value)
            print(f'> Done [{wta_mat}].')

        # 2. Plot

        print()
        print('> Creating figures...')

        mni_path = get('mni152_brain')
        mni = nib.load(mni_path)
        mni_shape = mni.shape
        mni_affine = mni.affine

        fs_colors = freesurfer_cortical_colors()

        for i, rank in enumerate(self.ranks):
            outpath = os.path.join(OUTDIR, f'winnerTakeAll_rank{rank}.jpg')
            if os.path.isfile(outpath):
                print(f'  + Exsting figure for RANK={rank} [{outpath}]')
                continue

            print(f'  + Plotting figure for RANK={rank} [{outpath}]')
            data1d = stacked_wta[:, i]
            data3d = np.reshape(data1d, mni_shape, order='F')
            nii = nib.Nifti1Image(data3d, affine=mni_affine)

            colors = fs_colors[:rank]
            cmap = ListedColormap(colors)

            overlay = NiftiOverlay()
            overlay.add_anat(mni)
            overlay.add_anat(nii, color=cmap, alpha=0.8, drop_zero=True, vmin=1, vmax=rank)
            overlay.generate(outpath)
            plt.close()

        print('> Complete')
