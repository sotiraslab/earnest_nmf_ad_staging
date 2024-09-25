# Image Search Protocols

## SCAN

Image searches for SCAN are run through LONI.  Note that some of the PET images have multiple imaging windows available (e.g. 45-75 mins vs 30-60 minutes for PI-2620).  We specifically include the ones recommended in documentation or otherwise the most abundant.

### Amyloid

Make sure "Pre-processed" and "PET" are ticked.  In the Image Description, run 4 searches:

- florbetapir: `AV Coreg, Avg, Rigid Reg to Std Img/Vox Size, 50-70, 6mm Res`
- florbetaben:  `FBB Coreg, Avg, Rigid Reg to Std Img/Vox Size, 90-110, 6mm Res`
- PIB: `PIB Coreg, Avg, Rigid Reg to Std Img/Vox Size, 40-60, 6mm Res`
- NAV: `NAV Coreg, Avg, Rigid Reg to Std Img/Vox Size, 50-70, 6mm Res`

Add all results to an image collection.

### Tau

Make sure "Pre-processed" and "PET" are ticked.  In the Image Description, run 3 searches:

- flortaucipir: `T80 Coreg, Avg, Rigid Reg to Std Img/Vox Size, 80-100, 6mm Res`
- MK6240: `M62 Coreg, Avg, Rigid Reg to Std Img/Vox Size, 90-110, 6mm Res`
- PI2620: `P26 Coreg, Avg, Rigid Reg to Std Img/Vox Size, 45-75, 6mm Res`

Add all results to an image collection.

### T1

Check "Original", "MRI", and "T1".  Search, and add all results to an image collection.