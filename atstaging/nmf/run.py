
import os
import textwrap

import pandas as pd

from atstaging.preprocessing.execute import execute

_this_dir = os.path.abspath(os.path.dirname(__file__))
_NMFVolBin_Directory = os.path.join(_this_dir, 'NMFVolBin')

class NMFRunner:

    def __init__(self,
                 master_table: pd.DataFrame,
                 output_dir_path: str,
                 ranks: list = list(range(2, 21)),
                 master_table_path_column: str ='Path',
                 n_reproducibility_splits: int =15,
                 reproduciblity_match_continuous: list =['Age'],
                 reproducbility_match_categorical: list=['CDRBinned','SexMale'],
                 source_dir=None):

        self.master_table = master_table
        self.output_dir_path = output_dir_path
        self.ranks = ranks
        self.source_dir = source_dir if source_dir is not None else _NMFVolBin_Directory

        self.master_table_path_column = master_table_path_column
        self.n_reproducibility_splits = n_reproducibility_splits
        self.reproducibility_match_continuous = reproduciblity_match_continuous
        self.reproducbility_match_categorical = reproducbility_match_categorical

        self.main_output_dir = os.path.join(self.output_dir_path, 'main')
        self.reproducibility_output_dir = os.path.join(self.output_dir_path, 'reproducibility')

    def _dircreate(self, *args):
        path = os.path.join(*args)
        if not os.path.isdir(path):
            os.mkdir(path)

    def create_input_file_csv(self):
        input_csv_path = os.path.join(self.main_output_dir, 'inputFiles.csv')
        images = self.master_table[[self.master_table_path_column]]
        images.to_csv(input_csv_path, header=False, index=False)
        return input_csv_path

    def create_main_submission_script(self, files_csv_path):
        
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
            OUTPUTDIR=self.main_output_dir,
            SCRIPTDIR=self.source_dir,
            RANKS=' '.join([str(k) for k in self.ranks])
        )
        SCRIPT = textwrap.dedent(SCRIPT)

        out_script_path = os.path.join(self.main_output_dir, 'submit_extractBasesMT.sh')
        with open(out_script_path, 'w') as f:
            f.write(SCRIPT)

        return out_script_path
    
    # def describe(self):

        # print()
        # print('+-----------+')
        # print('|  NMF RUN  |')
        # print('+-----------+')
    
    def run_main(self, dry=False):

        # self.describe()

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
        submit_script_path = self.create_main_submission_script(files_csv_path)
        print(f'Done [{submit_script_path}].')

        if dry:
            print()
            print('> DRYRUN: Reporting contents of submission script.')
            command = ['cat', submit_script_path]
        else:
            print()
            print('> Submitting run jobs.')
            command = ['source', submit_script_path]

        execute(command)

    def setup(self):
        self._dircreate(self.output_dir_path)
        self._dircreate(self.main_output_dir)
        self._dircreate(self.reproducibility_output_dir)

