
import os
import pickle
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pySuStaIn import ZscoreSustain, ZScoreSustainData
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from atstaging.config import get
from atstaging.preprocessing.execute import execute

class SustainManager:

    def __init__(self, src=None, setup=False):
        self.sustain = None
        self.sustain_output_folder = None

        if src is not None:
            self.load_sustain(src)

        if (self.sustain is not None) and (self.sustain_output_folder is not None) and setup:
            self.setup()

    def _create_cv_bash_script(self, cv_folds, select_fold):

        code = """
        #!/bin/bash

        source ~/miniconda/bin/activate atsustain
        echo "Python interpreter: $(which python)"
        python -u {PYTHON_CV_SCRIPT}
        """

        python_cv_script = os.path.join(self.path_scripts_subfolder, 'cv', f'cv{cv_folds}', f'run_fold_{select_fold}.py')
        code = textwrap.dedent(code.format(PYTHON_CV_SCRIPT=python_cv_script)).strip() + '\n'

        path_bash_script = os.path.join(self.path_scripts_subfolder, 'cv', f'cv{cv_folds}', f'run_fold_{select_fold}.sh')
        with open(path_bash_script, 'w') as f:
            f.write(code)

    def _create_cv_python_script(self, cv_folds, select_fold):

        code = """
        import os
        import pickle
        
        import numpy as np
        from pySuStaIn import ZscoreSustain

        mdir = os.path.join('{SUSTAIN_OUTPUT_FOLDER}', 'model')

        # Load the sustain model
        data = np.load(os.path.join(mdir, 'data.npy'))
        Z_vals = np.load(os.path.join(mdir, 'Z_vals.npy'))
        Z_max = np.load(os.path.join(mdir, 'Z_max.npy'))

        with open(os.path.join(mdir, 'params.pickle'), 'rb') as f:
            params = pickle.load(f)

        sustain = ZscoreSustain(data=data, Z_vals=Z_vals, Z_max=Z_max, **params)

        # load the CV indices
        cv_indices_dir = os.path.join('{SUSTAIN_OUTPUT_FOLDER}', 'cv', 'cv{CV_FOLDS}')
        test_indices = []
        for i in range({CV_FOLDS}):
            npy = os.path.join(cv_indices_dir, 'fold' + str(i) + '.npy')
            arr = np.load(npy)
            test_indices.append(arr)
        test_indices = np.array(test_indices, dtype='object')

        print()
        print('Test indices being used:')
        print(test_indices[{SELECT_FOLD}])

        CVIC, loglike_matrix = sustain.cross_validate_sustain_model(test_indices, select_fold={SELECT_FOLD})
        """

        code = textwrap.dedent(code.format(SUSTAIN_OUTPUT_FOLDER=self.sustain_output_folder, CV_FOLDS=cv_folds, SELECT_FOLD=select_fold))
        script_dir = os.path.join(self.path_scripts_subfolder, 'cv', f'cv{cv_folds}')
        script_path = os.path.join(script_dir, f'run_fold_{select_fold}.py')

        with open(script_path, 'w') as f:
            f.write(code)
    
    def _create_main_bash_script(self):

        code = """
        #!/bin/bash

        source ~/miniconda/bin/activate atsustain
        echo "Python interpreter: $(which python)"
        python -u {PYTHON_MAIN_SCRIPT}
        """

        code = textwrap.dedent(code.format(PYTHON_MAIN_SCRIPT=self.path_main_python_script)).strip() + '\n'

        with open(self.path_main_bash_script, 'w') as f:
            f.write(code)

    def _create_main_python_script(self):

        code = """
        import os
        import pickle
        
        import numpy as np
        from pySuStaIn import ZscoreSustain

        mdir = os.path.join('{SUSTAIN_OUTPUT_FOLDER}', 'model')
        
        data = np.load(os.path.join(mdir, 'data.npy'))
        Z_vals = np.load(os.path.join(mdir, 'Z_vals.npy'))
        Z_max = np.load(os.path.join(mdir, 'Z_max.npy'))

        with open(os.path.join(mdir, 'params.pickle'), 'rb') as f:
            params = pickle.load(f)

        sustain = ZscoreSustain(data=data, Z_vals=Z_vals, Z_max=Z_max, **params)
        
        samples_sequence, samples_f, ml_subtype, prob_ml_subtype, ml_stage, prob_ml_stage, prob_subtype_stage  = sustain.run_sustain_algorithm()
        """

        code = textwrap.dedent(code.format(SUSTAIN_OUTPUT_FOLDER=self.sustain_output_folder))

        with open(self.path_main_python_script, 'w') as f:
            f.write(code)
    
    def _load_sustain_from_freeze(self, directory):

        mdir = os.path.join(directory, 'model')
        data = np.load(os.path.join(mdir, 'data.npy'))
        Z_vals = np.load(os.path.join(mdir, 'Z_vals.npy'))
        Z_max = np.load(os.path.join(mdir, 'Z_max.npy'))

        with open(os.path.join(mdir, 'params.pickle'), 'rb') as f:
            params = pickle.load(f)

        self.sustain = ZscoreSustain(data=data, Z_vals=Z_vals, Z_max=Z_max, **params)
        self.sustain_output_folder = self.sustain.output_folder
        
    def _load_sustain_from_model(self, sustain):
        self.sustain = sustain
        self.sustain_output_folder = sustain.output_folder

    def create_run_main_scripts(self):
        self._create_main_python_script()
        self._create_main_bash_script()

    def create_run_cv_scripts(self, test_indices):

        # some helpful variables
        cv_folds = len(test_indices)

        # saves the test indices as npy files (in the cv directory)
        self.save_cv_indices(test_indices)

        # creates the scripts for each CV run
        script_dir = os.path.join(self.path_scripts_subfolder, 'cv', f'cv{cv_folds}')
        os.makedirs(script_dir, exist_ok=True)

        for i in range(cv_folds):
            self._create_cv_python_script(cv_folds=cv_folds, select_fold=i)
            self._create_cv_bash_script(cv_folds=cv_folds, select_fold=i)

    def freeze(self):

        odir = self.path_model_freeze_subfolder

        # numpy arrays
        np.save(os.path.join(odir, 'data.npy'), self.sustain._AbstractSustain__sustainData.data)
        np.save(os.path.join(odir, 'Z_vals.npy'), self.sustain.Z_vals)
        np.save(os.path.join(odir, 'Z_max.npy'), self.sustain.max_biomarker_zscore)

        # base python arguments
        args = {
            'biomarker_labels': self.sustain.biomarker_labels,
            'N_startpoints': self.sustain.N_startpoints,
            'N_S_max': self.sustain.N_S_max,
            'N_iterations_MCMC': self.sustain.N_iterations_MCMC,
            'output_folder': self.sustain.output_folder,
            'dataset_name': self.sustain.dataset_name,
            'use_parallel_startpoints': self.sustain.use_parallel_startpoints,
            'seed': self.sustain.seed
        }
        with open(os.path.join(self.path_model_freeze_subfolder, 'params.pickle'), 'wb') as f:
            pickle.dump(args, f)

    def frequency_based_biomarker_ordering(self, n_subtypes):
        ml_subtype = self.load_pickled_results(n_subtypes=n_subtypes)['ml_subtype']
        order = np.zeros((n_subtypes, self.n_biomarkers))
        for i in range(n_subtypes):
            w = self.input_data[ml_subtype.flatten() == i, :]
            order[i, :] = (w > 2.5).sum(axis=0).argsort()[::-1]
        return order

    @property
    def input_data(self):
        return self.sustain._AbstractSustain__sustainData.data

    def load_pickled_results(self, n_subtypes, fold=None, key=None):
        subtype_index = n_subtypes - 1
        fold_str = f'_fold{fold}' if fold is not None else ''
        picklepath = os.path.join(self.sustain_output_folder, 'pickle_files', 
                                  f'{self.sustain.dataset_name}{fold_str}_subtype{subtype_index}.pickle')
        with open(picklepath, 'rb') as f:
            data = pickle.load(f)
            if key is None:
                output = data
            elif isinstance(key,str):
                output = data[key]
            else:
                output = {k: data[k] for k in key}
        return output

    def load_test_indices(self, cv_folds):

        cv_dir = os.path.join(self.path_cv_subfolder, f'cv{cv_folds}')
        test_indices = []
        for i in range(cv_folds):
            path = os.path.join(cv_dir, f'fold{i}.npy')
            idx = np.load(path)
            test_indices.append(idx)
        test_indices = np.array(test_indices, dtype='object')
        return test_indices
    
    def load_sustain(self, src):

        if isinstance(src, str):
            self._load_sustain_from_freeze(src)
        else:
            self._load_sustain_from_model(src)

    def map_subtype_indexing(self, n_subtypes=3, verbose=True):
        ml_subtype_order = self.frequency_based_biomarker_ordering(n_subtypes=n_subtypes)
        sampled_order = self.load_pickled_results(n_subtypes=n_subtypes, key='ml_sequence_EM')
        dist = cdist(ml_subtype_order, sampled_order)
        index_a, index_b = linear_sum_assignment(dist)

        if verbose:
            print()
            print('Approximate regional ordering of subtypes as labeled in `ml_subtype`:')
            print(ml_subtype_order)
            print()
            print('Maximum likelihood ordering of subtypes as labeled in `samples_sequence`:')
            print(sampled_order)
            print()
            print('Linear sum assignment:')
            print(index_a, index_b)

        return index_a, index_b

    @property
    def n_biomarkers(self):
        return self.sustain._AbstractSustain__sustainData.data.shape[1]

    @property
    def n_samples(self):
        return self.sustain._AbstractSustain__sustainData.data.shape[0]

    @property
    def n_stages(self):
        return self.sustain._AbstractSustain__sustainData.getNumStages()

    @property
    def path_cv_subfolder(self):
        return os.path.join(self.sustain_output_folder, 'cv')
    
    @property
    def path_log_subfolder(self):
        return os.path.join(self.sustain_output_folder, 'logs')

    @property
    def path_model_freeze_subfolder(self):
        return os.path.join(self.sustain_output_folder, 'model')

    @property
    def path_scripts_subfolder(self):
        return os.path.join(self.sustain_output_folder, 'scripts')

    @property
    def path_main_python_script(self):
        return os.path.join(self.path_scripts_subfolder, 'run_main.py')

    @property
    def path_main_bash_script(self):
        return os.path.join(self.path_scripts_subfolder, 'run_main.sh')

    @property
    def path_main_log(self):
        return os.path.join(self.path_log_subfolder, 'run_main.log')
    
    def plot_cv_loglikelihood(self, loglike_matrix):
        
        fig, ax = plt.subplots()
        df_loglike = pd.DataFrame(data = loglike_matrix, columns = ["s_" + str(i+1) for i in range(self.sustain.N_S_max)])
        df_loglike.boxplot(grid=False, ax=ax)
        
        for i in range(self.sustain.N_S_max):
            y = df_loglike[["s_" + str(i+1)]]
            x = np.random.normal(1+i, 0.04, size=len(y)) # Add some random "jitter" to the x-axis
            plt.plot(x, y, 'r.', alpha=0.2)
        plt.ylabel('Log likelihood')  
        plt.xlabel('N subtypes') 
        plt.title('Figure 8: Test set log-likelihood across folds')

        return fig
                     
    def plot_cvic(self, CVIC):

        fig = plt.figure()
        x = np.arange(self.sustain.N_S_max, dtype=int)
        plt.plot(x, CVIC)
        plt.xticks(x, x+1)
        plt.ylabel('CVIC')
        plt.xlabel('N subtypes') 

        return fig
    
    def plot_likelihood_histogram(self, N_S_max=None):

        N_S_max = self.sustain.N_S_max if N_S_max is None else N_S_max
        
        fig = plt.figure()
        
        for i in range(N_S_max):
            samples_likelihood = self.load_pickled_results(key='samples_likelihood', n_subtypes=i+1, fold=None)
            txt = 'subtype' if i == 0 else 'subtypes'
            plt.hist(samples_likelihood, label=f'{i+1} {txt}')

        plt.legend(loc='upper left', bbox_to_anchor=(1,1))
        plt.xlabel('Log likelihood')
        plt.ylabel('Number of samples')
        plt.title('Histograms of model likelihood')

        return fig
    
    def plot_mcmc_trace(self, N_S_max=None):

        N_S_max = self.sustain.N_S_max if N_S_max is None else N_S_max

        fig = plt.figure()

        iterations = self.sustain.N_iterations_MCMC
        
        for i in range(N_S_max):
            samples_likelihood = self.load_pickled_results(key='samples_likelihood', n_subtypes=i+1, fold=None)
            txt = 'subtype' if i == 0 else 'subtypes'
            plt.plot(range(iterations), samples_likelihood, label=f'{i+1} {txt}')

        plt.legend(loc='upper left', bbox_to_anchor=(1,1))
        plt.xlabel('MCMC samples')
        plt.ylabel('Number of samples')
        plt.title('MCMC trace')

        return fig
    
    def plot_pvd(self, n_subtypes, **kwargs):
        loaded_variables = self.load_pickled_results(n_subtypes=n_subtypes)
        samples_sequence = loaded_variables['samples_sequence']
        samples_f = loaded_variables['samples_f']
        n_samples = self.n_samples


        return self.sustain._plot_sustain_model(
            samples_sequence,
            samples_f,
            n_samples,
            biomarker_labels=self.sustain.biomarker_labels,
            **kwargs)
    
    def predict(self, data, n_subtypes, n_samples=1000, prefix=''):

        # load samples for predicitng new data
        loaded_variables = self.load_pickled_results(n_subtypes=n_subtypes)
        samples_sequence = loaded_variables['samples_sequence']
        samples_f = loaded_variables['samples_f']

        # load new data
        sustain_data = ZScoreSustainData(data, numStages=self.n_stages)
        ml_subtype, \
        prob_ml_subtype, \
        ml_stage, \
        prob_ml_stage, \
        prob_subtype, \
        prob_stage, \
        prob_subtype_stage = self.sustain.subtype_and_stage_individuals(
            sustainData=sustain_data,
            samples_sequence=samples_sequence,
            samples_f=samples_f,
            N_samples=n_samples
        )

        df = pd.DataFrame(
            {
                'MLSubtype': ml_subtype.flatten(),
                'MLStage': ml_stage.flatten(),
                'ProbMLSubtype': prob_ml_subtype.flatten(),
                'ProMLStage': prob_ml_stage.flatten()
            }
        )
        df['MLSubtype'] = 'S' + (df['MLSubtype'].astype(int) + 1).astype(str)
        df['MLSubtypeRAW'] = ml_subtype.flatten()

        n_subtypes = prob_subtype.shape[1]
        probs = pd.DataFrame(prob_subtype, columns=[f'ProbSubtypeS{i+1}' for i in range(n_subtypes)])

        result = pd.concat([df, probs], axis=1)
        result.columns = [prefix + c for c in result.columns]

        return result

    def run_cv(self, test_indices, dry=False):

        # ensure setup
        self.setup()

        # Create CV Scripts
        self.create_run_cv_scripts(test_indices=test_indices)

        # Submit
        account = get('slurm', 'account')
        partition = get('slurm', 'partition')

        cv_folds = len(test_indices)
        bname = os.path.basename(os.path.normpath(self.sustain_output_folder))
        
        for i in range(cv_folds):
            script = os.path.join(self.path_scripts_subfolder, 'cv', f'cv{cv_folds}', f'run_fold_{i}.sh')
            logpath = os.path.join(self.path_log_subfolder, f'cv_{cv_folds}_fold_{i}.log')
            command = [
                'sbatch','-n', '1', '-N', '1', '-J', f'{bname}_cv{i}', '-t', '24:00:00', '--mem=4G',
                '--account', account, '--partition', partition, '-o', logpath, script
            ]

            print()
            print('SLURM Command:')
            print(' '.join(command))
    
            if not dry:
                execute(command)

    def run_main(self, dry=False):

        # ensure setup
        self.setup()

        account = get('slurm', 'account')
        partition = get('slurm', 'partition')

        command = [
            'sbatch','-n', '1', '-N', '1', '-J', os.path.basename(os.path.normpath(self.sustain_output_folder)), '-t', '24:00:00', '--mem=4G',
            '--account', account, '--partition', partition, '-o', self.path_main_log, self.path_main_bash_script
        ]

        print()
        print('SLURM Command:')
        print()
        print(' '.join(command))
        print()

        if not dry:
            execute(command)

    def save_cv_indices(self, test_indices):
        cv_folds = len(test_indices)
        subfolder = os.path.join(self.path_cv_subfolder, f"cv{cv_folds}")
        os.makedirs(subfolder, exist_ok=True)
        for i in range(cv_folds):
            path = os.path.join(subfolder, f'fold{i}.npy')
            np.save(path, test_indices[i])
        
    def setup(self):
        print()
        print('SustainManager Setup')
        print('=====')

        print()
        print('> Creating directories...')
        os.makedirs(self.path_cv_subfolder, exist_ok=True)
        os.makedirs(self.path_model_freeze_subfolder, exist_ok=True)
        os.makedirs(self.path_scripts_subfolder, exist_ok=True)
        os.makedirs(self.path_log_subfolder, exist_ok=True)

        print('> Freezing model')
        self.freeze()

        print('> Creating run scripts for main run...')
        self.create_run_main_scripts()
