import os

from atstaging.config import get, set_config
from atstaging.outputs import load_paths_tables

set_config('main')

output_directory = get('output_directory')
save_path = os.path.join(output_directory, 'preprocessing', 'paths', 'paths.csv')
paths = load_paths_tables(use_saved=False)
paths.to_csv(save_path, index=False)