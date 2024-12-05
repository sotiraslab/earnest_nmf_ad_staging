
import functools
import json
from operator import getitem
import os

from colorama import Fore, Style

CONFIG = {}
CONFIG_FILE = ''

def assert_config_is_set():
    if CONFIG:
        return True
    else:
        msg = ('Configuration file is not set; either a specified '
               'config file was unable to be loaded or '
               'no configuration file was able to be selected automatically. '
               'Please add a file to the config directory (atstaging/config), filling in the '
               'entries provided in "example.json", and set the "AUTOUSE" entry to true.'
               'Find the project README for more information about using the configuration file.')
        raise RuntimeError(msg)

def get(*args):
    assert_config_is_set()
    try:
        return functools.reduce(getitem, args, CONFIG)
    except KeyError:
        s = ''.join([f'["{a}"]' for a in args])
        raise KeyError(f'Cannot find configuration value in {CONFIG_FILE} for indexing operation: CONFIG{s}')

def get_config_dir():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(project_dir, 'config')
    return config_dir

def get_slurm_setup_script():
    return os.path.join(get_config_dir(), 'slurm_setup.sh')

def find_config_files():
    config_dir = get_config_dir()
    config_files = os.listdir(config_dir)

    filtered_config_files = filter_config_files(config_files)
    final = [os.path.join(config_dir, f) for f in filtered_config_files]

    return final

def filter_config_files(basenames):
    output = []
    for file in basenames:
        if not file.endswith('.json'):
            continue
        if file == 'example.json':
            continue
        output.append(file)
    return output

def read_config_file(path):
    with open(path, 'r') as f:
        config = json.load(f)
    return config

def read_example_config():
    path = os.path.join(get_config_dir(), 'example.json')
    with open(path, 'r') as f:
        config = json.load(f)
    return config

def report_configuration():
    assert_config_is_set()

    print()
    print(Fore.GREEN + '----- CURRENT CONFIGURATION -----' + Style.RESET_ALL)
    print(f'Name: {os.path.basename(CONFIG_FILE)}')
    print(f'Path: {CONFIG_FILE}')
    print("Configuration:")
    print()
    print(json.dumps(CONFIG, indent=4, sort_keys=True))

    if not CONFIG:
        print(Fore.RED + Style.BRIGHT + 'WARNING!  Configuration appears to not be set.' + Style.RESET_ALL)

    print(Fore.GREEN + '---------------------------------' + Style.RESET_ALL)
    print(Style.RESET_ALL)

def screen_config_against_example(config, config_path):
    example = read_example_config()
    missing = []
    def _check_keys(d1, d2, keystring='', missing=missing):
        for k, v in d1.items():
            new_keystring = keystring + '.' + k
            if k not in d2.keys():
                missing.append(new_keystring)
                continue

            if isinstance(v, dict):
                _check_keys(v, d2[k], keystring=new_keystring)

    _check_keys(example, config)

    if missing:
        raise RuntimeError(f'Missing keys detected for configuration file which is being used ({config_path}): {missing}')

def set_config(src=None):
    if src is None:
        set_config_automatic()
    elif os.path.isfile(src):
        update_config(src)
    else:
        set_config_by_name(src)

def set_config_by_name(name):
    if not name.endswith('.json'):
        name += '.json'
    fullpath = os.path.join(get_config_dir(), name)
    update_config(fullpath)

def set_config_automatic():

    files = find_config_files()
    for file in files:

        config = read_config_file(file)
        if not config['AUTOUSE']:
            continue
        update_config(file)

    assert_config_is_set()

def update_config(file):

    global CONFIG_FILE

    CONFIG.update({})
    CONFIG_FILE = ''
    config = read_config_file(file)
    screen_config_against_example(config, file)
    CONFIG.update(config)
    CONFIG_FILE = file

    cname = os.path.basename(CONFIG_FILE)
    print()
    print('Using configuration: ' + Fore.CYAN + Style.BRIGHT + cname + Style.RESET_ALL)
