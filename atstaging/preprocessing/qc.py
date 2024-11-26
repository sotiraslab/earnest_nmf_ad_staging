#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 10:48:35 2024

@author: earnestt1234
"""

import matplotlib.pyplot as plt
from nifti_overlay import NiftiOverlay

def pet_mni_registration_qc_image(registeredpet, mni, output):
    overlay = NiftiOverlay(dpi=300)
    overlay.add_anat(mni)
    overlay.add_anat(registeredpet, color='jet', alpha=.5)
    overlay.generate(output)
    plt.close()

def pet_t1_registration_qc_image(registeredpet, t1, output):
    overlay = NiftiOverlay(dpi=300)
    overlay.add_anat(t1)
    overlay.add_anat(registeredpet, color='jet', alpha=.5)
    overlay.generate(output)
    plt.close()

def registration_checkerboard_qc_image(registered, template, output):
    overlay = NiftiOverlay(dpi=300)
    overlay.add_checkerboard([registered, template])
    overlay.generate(output)
    plt.close()

def skullstripping_qc_image(t1, brainmask, output):
    overlay = NiftiOverlay(dpi=300)
    overlay.add_anat(t1)
    overlay.add_mask(brainmask, color='red', alpha=0.5)
    overlay.generate(output)
    plt.close()

def suvr_qc_image(suvr, output):
    overlay = NiftiOverlay(dpi=300)
    overlay.add_anat(suvr, color='nipy_spectral', vmin=1.0, vmax=2.5)
    overlay.generate(output)
    plt.close()
