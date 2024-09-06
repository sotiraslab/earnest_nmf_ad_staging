
import functools
import json
from operator import getitem
import os
import warnings

CONFIG = {}
CONFIG_FILE = ''

def get(*args):
    try:
        return functools.reduce(getitem, args, CONFIG)
    except KeyError:
        s = ''.join([f'["{a}"]' for a in args])
        raise KeyError(f'Cannot find configuration value for indexing operation: CONFIG{s}')

def get_config_dir():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(project_dir, 'config')
    return config_dir

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

def report_configuration():

    print()
    print('----- CURRENT CONFIGURATION -----')
    print(f'Name: {os.path.basename(CONFIG_FILE)}')
    print(f'Path: {CONFIG_FILE}')
    print("Configuration:")
    print()
    print(json.dumps(CONFIG, indent=4, sort_keys=True))
    print('---------------------------------')


def set_config_by_name(name):
    if not name.endswith('.json'):
        name += '.json'
    fullpath = os.path.join(get_config_dir(), name)
    update_config(fullpath)


def set_config_on_init():

    files = find_config_files()
    for file in files:

        config = read_config_file(file)
        if not config['use']:
            continue
        update_config(file)

    if not CONFIG:
        m = ('No configuration file found; please add '
             'a file to atstaging/config, filling in the '
             'entries provided in "example.json". '
             'Find the project README for more information '
             'about using the configuration file.')
        warnings.warn(RuntimeWarning(m))

def update_config(file):

    global CONFIG_FILE

    CONFIG.update({})
    CONFIG_FILE = ''
    config = read_config_file(file)
    CONFIG.update(config)
    CONFIG_FILE = file
