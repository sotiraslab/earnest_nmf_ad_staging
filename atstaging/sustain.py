
import os
import pickle
import textwrap

import numpy as np
from pySuStaIn import ZscoreSustain

from atstaging.config import get
from atstaging.preprocessing.execute import execute

class SustainManager:

    def __init__(self, src=None, setup=True):
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
    
    def load_sustain(self, src):

        if isinstance(src, str):
            self._load_sustain_from_freeze(src)
        else:
            self._load_sustain_from_model(src)

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

    def run_cv(self, test_indices, dry=False):

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
