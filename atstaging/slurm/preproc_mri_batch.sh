#!/bin/bash

# usage string
usage() {
	echo ""
	echo "Usage:	preproc_mri_batch.sh -i <t1> -o <output> -s <subject> -S <session>"
	}

# read arguments
while getopts hi:o:s:S: arg
do
	case $arg in
	h)	usage
		exit 0;;
	i)	t1=${OPTARG};;
	o)	output=${OPTARG};;
    s)  subject=${OPTARG};;
    S)  session=${OPTARGE} 
	?)	echo ""
		echo "Unknown arguments passed; exiting."
		echo ""
		usage;
		exit 1;;
	esac
done

# check arguments
if [[ -z $t1 ]] || [[ -z $output ]] || [[ -z $subject ]] || [[ -z $session ]]
then
	echo ""
	echo "Some input arguments missing (-i -o -s -S); exiting."
	echo ""
	usage;
	exit 1
fi

# run!
preproc_mri -i $t1 -o $output --sub $subject --ses $session