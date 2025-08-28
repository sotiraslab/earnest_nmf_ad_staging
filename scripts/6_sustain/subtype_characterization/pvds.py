import os

from atstaging import component_order
from atstaging.config import get, set_config
from atstaging.plotting import set_font_properties, staging_colors
from atstaging.sustain import SustainManager

# setup
set_config('main')
set_font_properties()
scolors = staging_colors()
comp_order = component_order(dash=True)

root_output = get('output_directory')
odir = os.path.join(root_output, 'plots', 'sustain', 'pvd')
os.makedirs(odir, exist_ok=True)

# Load data
training = SustainManager(os.path.join(root_output, 'sustain', 'training'))
training.sustain.biomarker_labels = [
    x.replace('WScore', '').replace('PAC', 'PAC-').replace('PTC','PTC-')
    for x in training.sustain.biomarker_labels
]

validation = SustainManager(os.path.join(root_output, 'sustain', 'validation'))
validation.sustain.biomarker_labels = [
    x.replace('WScore', '').replace('PAC', 'PAC-').replace('PTC','PTC-')
    for x in validation.sustain.biomarker_labels
]

biomarker_order = [training.sustain.biomarker_labels.index(s) for s in comp_order]

# helper func
def plot_pvd(sustain, n_subtypes, keyword):

    figs = sustain.combine_cross_validated_sequences(
        N_subtypes=n_subtypes,
        N_folds=10,
        separate_subtypes=True,
        biomarker_order=biomarker_order,
        figsize=(6,6),
        biomarker_colours=[scolors['A2T0']]*4 + [scolors['A2T4']]*7
    )

    for i, fig in enumerate(figs[0]):
        ax = fig.get_axes()[0]
        ax.set_title('')
    
        fig.savefig(os.path.join(odir, f'{keyword}_n{n_subtypes}_subtype{i+1}.svg'))

# run
plot_pvd(training.sustain, 3, 'training')
plot_pvd(training.sustain, 7, 'training')

plot_pvd(validation.sustain, 3, 'validation')
plot_pvd(validation.sustain, 7, 'validation')