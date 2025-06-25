
# IMPORTS
import os

from atstaging.config import get, set_config
from atstaging.nmf.utils import load_nmf_runner

# CONFIG
set_config('main')
output_directory = get('output_directory')

# MAIN
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationA_tau')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationA_amyloid')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationB_tau')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationB_amyloid')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationC_tau')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationC_amyloid')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationAll_tau')).post_main()
load_nmf_runner(os.path.join(output_directory, 'nmf', 'runs', 'validationAll_amyloid')).post_main()

