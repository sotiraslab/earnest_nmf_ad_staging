### Contents

- **0_datasets**: data wrangling to identify subjects/sessions and paths to their imaging data for each source dataset
- **1_preprocessing**: generate inputs to initiate image preprocessing
- **2_qc**: Quality control for preprocessing outputs.
- **3_datasplitting**: Determine training/validation splitting.
- **4_nmf**: Apply non-negative matrix factorization to generate amyloid & tau factors.
- **5_frequencystaging**: Fit and evaluate a single staging model capturing the dominant trajectory of amyloid and tau pathology in AD.
- **6_sustain**: Fit a Subtype and Stage Inference model capturing subtypes of amyloid and tau progression.
- **misc**: Miscellaneous scripts
- **rsource**: R source files