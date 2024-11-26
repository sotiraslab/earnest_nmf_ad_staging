#!/bin/bash

CLI_NAME="atproc_subject"

# usage string
usage() {
	echo ""
	echo "Usage:at_preproc_batch.sh -I t1 -A amyloid -a amyloid_tracer -T tau -t tau_tracer -S subject -s session -O output_directory -U slurm_setup.sh"
	}

# read arguments
while getopts hi:o:s:S: arg
do
	case $arg in
	h)	usage
		exit 0;;
	I)	t1=${OPTARG};;
	A)  amyloid=${OPTARG};;
	a)  amyloid_tracer=${OPTARG};;
	T)  tau=${OPTARG};;
	t)  tau_tracer=${OPTARG};;
    S)  subject=${OPTARG};;
    s)  session=${OPTARG};;
	O)	output=${OPTARG};;
	U)  setup_script=${OPTARG};;
	?)	echo ""
		echo "Unknown arguments passed; exiting."
		echo ""
		usage;
		exit 1;;
	esac
done

# main
COMMAND=(
	$CLI_NAME
	--t1 $t1_img
	--amyloid $amyloid
	--amyloid-tracer $amyloid_tracer
	--tau $tau
	--tau-tracer $tau_tracer
	--sub $subject
	--ses $session
	--output $output
	)

echo ""
echo "Running SLURM setup script at ${setup_script}."
echo ""
echo "----BEGIN OUTPUT----"
source ${setup_script}
echo "----END OUTPUT------"

echo ""
echo "PREPROCESSING COMMAND:"
echo "     ${COMMAND[@]}"

echo ""
echo "----BEGIN OUTPUT----"
"${COMMAND[@]}"
echo "----END OUTPUT------"
