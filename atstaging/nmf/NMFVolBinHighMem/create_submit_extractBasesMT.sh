#!/bin/bash

# set parameters for NMF here!
PARAMETERS=(saveInterm 1 negPos 0 initMeth 4 downSample 2)

# parsing input / setting up variables
mkdir -p ${3}/NumBases${2}/slurm_job_output
inFiles=$1
numBases=$2
outputDir=$3
BinDir=$4

MCRROOT="/export/matlab/R2021a/"
extractBases="${BinDir}/run_extractBasesMT.sh"

# script creation
echo '#!/bin/bash  '

# basic slurm setup
echo '### Job Name  '
echo '#SBATCH -J extractBasesMT  '
echo '### Save output and error files in the following folder  '
echo "#SBATCH -o ${3}/NumBases${2}/slurm_job_output/output.log  "
echo "#SBATCH -e ${3}/NumBases${2}/slurm_job_output/error.log  "

# emailing
# echo '### Send email to user about the job from the execution server  '
# echo '#SBATCH --mail-user=wustlid@wustl.edu  '
# echo '### Sends email only in certain cases; see sbatch docs  '
# echo '#SBATCH --mail-type=END,FAIL,TIME_LIMIT'

# resources
echo '### Start job with priority - default is zero  '
echo '#SBATCH --priority=0  '
echo '### Select 1 nodes with 4 CPU  '
echo '#SBATCH --nodes=1  '
echo '#SBATCH --cpus-per-task=4  '
echo '### Select 16Gb RAM  '
echo '#SBATCH --mem=48G  '
echo '### Select wall time  '
echo '#SBATCH -t 48:00:00  '
echo '### Account  '
echo '#SBATCH --account=aristeidis_sotiras  '
echo '### Partition  '
echo '#SBATCH --partition=tier2_cpu  '
echo '  '

# variables
echo '# set up useful variables  '
echo '  '
echo "MCRROOT=${MCRROOT}  "
echo "BinDir=${BinDir} "
echo "extractBases=${extractBases}"
echo '  '
echo '# parse input variables  '
echo "inFiles=$inFiles	  "
echo "numBases=$numBases  "
echo "outputDir=$outputDir  "
echo '  '

echo '##########################################  '
echo '#                                        #  '
echo '#   Output some useful job information.  #  '
echo '#                                        #  '
echo '##########################################  '
echo '  '

# see: https://wiki.gacrc.uga.edu/wiki/Migrating_from_Torque_to_Slurm
# SLURM status printed in std output
echo '# stdout  '
echo 'echo "------------------------------------------------------"   '
echo 'echo "SLURM: sbatch is running on ${SLURM_SUBMIT_HOST}"   '
echo 'echo "SLURM: executing queue is ${SLURM_JOB_PARTITION}"   '
echo 'echo "SLURM: working directory is ${SLURM_SUBMIT_DIR}"   '
echo 'echo "SLURM: job identifier is ${SLURM_JOB_ID}"   '
echo 'echo "SLURM: job name is ${SLURM_JOB_NAME}"   '
echo 'echo "SLURM: cores per node ${SLURM_CPUS_ON_NODE}"   '
echo 'echo "SLURM: cores per task ${SLURM_CPUS_PER_TASK}"   '
echo 'echo "SLURM: node list ${SLURM_JOB_NODELIST}"   '
echo 'echo "SLURM: number of nodes for job ${SLURM_JOB_NUM_NODES}"   '
echo 'echo "------------------------------------------------------"  '
echo 'echo "Command: ${BinDir}/run_extractBasesMT.sh"   '
echo 'echo "Arguments: Input files: ${inFiles} NumBases: ${numBases} Output directory: ${outputDir}"  '
echo '  '
echo '( echo -e "Executing in: \c"; pwd )   '
echo '( echo -e "Executing at: \c"; date )   '
echo '  '

# SLURM status printed in std error
echo '# stderr  '
echo 'echo "------------------------------------------------------" 1>&2  '
echo 'echo "SLURM: sbatch is running on ${SLURM_SUBMIT_HOST}" 1>&2  '
echo 'echo "SLURM: executing queue is ${SLURM_JOB_PARTITION}" 1>&2  '
echo 'echo "SLURM: working directory is ${SLURM_SUBMIT_DIR}" 1>&2  '
echo 'echo "SLURM: job identifier is ${SLURM_JOB_ID}" 1>&2  '
echo 'echo "SLURM: job name is ${SLURM_JOB_NAME}" 1>&2  '
echo 'echo "SLURM: cores per node ${SLURM_CPUS_ON_NODE}" 1>&2   '
echo 'echo "SLURM: cores per task ${SLURM_CPUS_PER_TASK}" 1>&2  '
echo 'echo "SLURM: node list ${SLURM_JOB_NODELIST}" 1>&2  '
echo 'echo "SLURM: number of nodes for job ${SLURM_JOB_NUM_NODES}" 1>&2  '
echo 'echo "------------------------------------------------------" 1>&2 '
echo 'echo "Command: ${BinDir}/run_extractBasesMT.sh" 1>&2  '
echo 'echo "Arguments: Input files: ${inFiles} NumBases: ${numBases} Output directory: ${outputDir}" 1>&2 '
echo '  '
echo '( echo -e "Executing in: \c"; pwd ) 1>&2  '
echo '( echo -e "Executing at: \c"; date ) 1>&2  '
echo '  '

# prep for run
echo '  '
echo '# keep some extra information in the output directory  '
echo 'mkdir -p ${outputDir}/NumBases${numBases}  '
echo '  '
echo '# date  '
echo 'date2save=$(date +"%m-%d-%y")  '
echo '  '

# main command; printed to file
echo '# output command  '

echo -n "command=\"\${BinDir}/run_extractBasesMT.sh \${MCRROOT} OPNMF \${inFiles} 1 \${numBases} outputDir \${outputDir} ${PARAMETERS[@]}\""
echo -e "\n"
echo 'echo ${command} > ${outputDir}/NumBases${numBases}/command_${date2save}.txt  '

# running main command
echo "\${extractBases} \${MCRROOT} OPNMF \${inFiles} 1 \${numBases} outputDir \${outputDir} ${PARAMETERS[@]}"
echo '  '

# check failures
echo 'if [ $? != 0 ] ;   '
echo 'then  '
echo '	date_info=$(date)  '
echo '	echo "${date_info} : Failure to execute extractBasesMT"  '
echo -n '	echo "${date_info} : Failure to execute extractBasesMT, JobID: ${SLURM_JOB_ID}, method: OPNMF, number of bases:  ${numBases}" >> ${outputDir}/FailedExtractBasesExperimentsMT.txt  '
echo -e "\n"
echo '	exit 1  '
echo 'fi  '
