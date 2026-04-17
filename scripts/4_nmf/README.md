# Non-negative matrix factorization (NMF)

This repository runs the non-negative matrix factorization (NMF) to generate the amyloid factors (Patterns of Amyloid Covariance, PACs) and tau factors (Patterns of Tau Covariance, PTCs).

This code was run on a SLURM computing cluster at Washington University in St Louis.  The Python code here calls a wrapper (`atstaging.nmf.run.NMFRunner`) which in turn calls a compile MATLAB program for running NMF (on GitHub, see *atstaging > nmf > NMFVolBin*).

NMF outputs are stored at `OUTPUTDIRECTORY/nmf`.

The script `run_nmf.py` first fits the main NMF models for amyloid and tau with the number of factors (*k*) set from 2-20, as well as the split half reproducibility experiments.  The latter are the most time consuming part, taking a day or more to complete on the cluster.

`post_nmf.py` is then run to evaluate the reconstruction error and reproducibility of different ranks.  This script needs high memory to run, as it loads the entire imaging dataset into memory.   I was able to run with 64GB.

`component_overlays.py` can additionally be used to create visualizations of each component overlaed on the MNI template.

After analyzing the post-NMF outputs, the optimal model is selected.  In `calculate_loadings.py`, the model selection result is saved under the `#PARAMETERS` comment, namely the rank of the optimal solution for amyloid and tau, the indices of the cortical gray matter factors, and the assigned names for each.  This script then runs over the entire dataset (training and validation)  and calculates loadings (SUVR uptake within each factor) for each subject.

Other bits in this repository:

- `create_gm_maskpy` creates a gray matter overlap mask in MNI space based on the aggregation of training set segmentations.  This can be used to constrain NMF, but it is not used for the manuscripts generated from this repo.
- `surfice_scripts.py` contains Python code to generate 3D surface images of brains using [Surf Ice](https://www.nitrc.org/projects/surfice/).  It is meant to be run in to program's Python interpreter.
- `validation` contains code for refitting the NMF models using validation data, and generating figures to compare the factors.
