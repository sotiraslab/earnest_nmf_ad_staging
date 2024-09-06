#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  6 15:48:46 2024

@author: earnestt1234
"""

import os
import subprocess

from colorama import Fore, Back, Style

from atstaging.config import get

def _run(command):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)

def _check_which_command(command):
    process = _run(['which', command])
    return process.returncode == 0, process

def check_ants():
    ants = get('ants')
    command = os.path.join(ants, 'antsRegistration')
    return _check_which_command(command)

def check_conda():
    return _check_which_command('conda')

def check_deepmrseg():
    env = get('deepmrseg_env')
    process = _run(
        ['conda',
         'run',
         '--name', env,
         'which',
         'deepmrseg_apply'])
    return process.returncode == 0, process

def check_packages():

    success = True
    message = None
    try:
        import colorama
        import nibabel
    except ModuleNotFoundError as error:
        message = error
        success = False

    return success, message

def run_dependency_check():

    print()
    print(Fore.CYAN + Style.BRIGHT + 'RUNNING DEPENDENCY CHECK' + Style.RESET_ALL)

    checks = {
        'Conda': check_conda,
        'Python packages': check_packages,
        'ANTS Registration': check_ants,
        'DeepMRSeg': check_deepmrseg,
        }

    count = 0
    total = len(checks)
    print()
    print('-----')
    for name, func in checks.items():
        success, metadata = func()
        response = (Fore.GREEN + 'success' + Style.RESET_ALL if success else
                    Fore.RED + 'failed' + Style.RESET_ALL)
        print(f'* {name}: ({response})')
        if not success:
            print(f'    > {metadata}')

        count += success

    print()
    print('-----')
    color = Fore.GREEN if count == total else Fore.RED
    print(color + str(count) + Style.RESET_ALL + ' / ' + str(total) + ' passed')



run_dependency_check()



