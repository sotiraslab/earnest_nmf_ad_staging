# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 13:53:34 2024

@author: earne
"""

import os
import subprocess

def run_dcm2niix(indir, outdir, name):

    call = [
        'dcm2niix', 
        '-a', 'y',
        '-z', 'y',
        '-w', '1',
        '-f', name,
        '-o', outdir,
        indir
        ]

    subprocess.run(call)
