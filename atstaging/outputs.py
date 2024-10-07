
import os

def _dircreate(*args):
    path = os.path.join(*args)
    if not os.path.isdir(path):
        os.mkdir(path)
        

def setup_outputs_folder(directory):
    _dircreate(directory)
    _dircreate(directory, 'download_lists')
    _dircreate(directory, 'preproc_tables')
    _dircreate(directory, 'searches')
