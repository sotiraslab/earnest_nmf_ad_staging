#!/bin/bash

CHPCPATH='/scratch/tom.earnest/atstaging'
DESTINATION="${HOME}/Desktop"

# CHPC is an environment variable containing the user@hostname
rsync $CHPC:$CHPCPATH $DESTINATION -av --exclude nmf --exclude images