
import os

from matplotlib.colors import to_hex
import matplotlib.pyplot as plt
import pandas as pd

def freesurfer_cortical_colors():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freesurfer_cortical_colors.csv')
    colors = pd.read_csv(path)
    colors = colors / 255.
    array = colors.to_numpy()
    return [to_hex(array[i, :]) for i in range(len(array))]

def set_font_properties():
    plt.rcParams.update({
        'font.size': 14,
        'font.family': 'FreeSans'})
