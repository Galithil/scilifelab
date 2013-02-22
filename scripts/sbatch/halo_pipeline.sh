#!/bin/bash

USAGE="Usage: $0 [-n] indir samples"

# Parameters that govern general behaviour
READ1_REGEXP="R1_001"    # Regexp used for 1st reads
READ2_REGEXP="R2_001"    # Regexp used for paired sequences
N_CORES=5
LOGFILE="halo_pipeline.out"
ERRFILE="halo_pipeline.err"

echo $(date) > $LOGFILE
echo $(date) > $ERRFILE

# Software config
# Modify for specific versions
PARALLEL=/usr/bin/parallel
PIGZ=/usr/bin/pigz
FASTQC=fastqc
CUTADAPT=cutadapt
CUTADAPT_OPTS="-m 50"
RESYNCMATES=/home/peru/opt/scilifelab.git/scripts/sbatch/resyncMates.pl
# Picard and GATK
PICARD_HOME=$HOME/local/bioinfo/ngs/picard-tools-1.59
GATK_HOME=$HOME/local/bioinfo/ngs/GenomeAnalysisTK-2.3-9-ge5ebf34
GATK=$GATK_HOME/GenomeAnalysisTK.jar

# Alignment options and database locations
BAIT_INTERVALS_FILE=""
TARGET_INTERVALS_FILE=""
TARGET_BED_FILE=/home/peru/opt/scilifelab.git/scripts/sbatch/test/regions.bed
TARGET_REGION="chr11:1-2000000"
BWA=bwa
BWA_HG19=/datad/biodata/genomes/Hsapiens/hg19/bwa/hg19.fa
BWA_REF=$BWA_HG19
REF=/datad/biodata/genomes/Hsapiens/hg19/seq/hg19.fa

# Samtools
SAMTOOLS=samtools
SAMSTAT=samstat

# Variant databases
VARIANTDBHOME=/datad/biodata/genomes/Hsapiens/hg19/variation
DBSNP=$VARIANTDBHOME/dbsnp_132.vcf
THOUSANDG_OMNI=$VARIANTDBHOME/1000G_omni2.5.vcf
MILLS=$VARIANTDBHOME/Mills_Devine_2hit.indels.vcf
HAPMAP=$VARIANTDBHOME/hapmap_3.3.vcf

# Adapter sequences. These correspond to TruSeq adapter sequence.
# THREEPRIME is found in the three-prime end of read 1, FIVEPRIME
# revcomp in the end of read 2
THREEPRIME="AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC"
FIVEPRIME="AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGATCTCGGTGGTCGCCGTATCATT"

# Setup environment
DRY_RUN=false
FORCE=false

E_PARAM_ERR=250    # If less than 2 params passed to function.
P_RUN=true            # Run command
P_NORUN=false         # Skip command

# Check user input
while getopts n:f flag; do
  case $flag in
    n)
      dry_run=true;
      ;;
    f)
      force=true;
      ;;
    ?)
      echo $usage
      exit;
      ;;
  esac
done
shift $(( OPTIND - 1 ));

# Exit if no input
if [ $# -eq 0 ]; then
    echo $usage
    exit;
fi

# Functions
# run_command: emulate dry run behaviour
# NOTE: currently not used!
run_command () {
    if [ -z "$1" ]
    then
	echo $(date) "No command passed to run_command"
	exit
    fi
    command=$1
    output=$2
    echo $output
    if [ "$dry_run" ]; then
	echo $(date) "Command: " $command
    else
	up_to_date $output
	retval=$?
	if [ ! "$retval" ]; then
	    echo $(date) "command up to date; skipping"
	    echo -e "\t" $command
	else
	    $command
	fi
    fi
}

# up_to_date: check if job is up to date. Very simple rules: if only
# output file given, we assume that job is done if file exists. If
# pre_output file given, compare time stamps and return 0 if output
# older than pre_output (emulates make).
up_to_date () {
    if [ -z "$1" ]
    then
	echo "No parameter passed to up_to_date"
	exit
    fi
    output=$1
    if [ ! -e $output ]; then
	return 0
    fi
    if [ ! -z "$2" ]
    then
	pre_output=$2
	if [ -e "$pre_output" ]; then
	    output_time=`stat -c %Y $output`
	    pre_output_time=`stat -c %Y $pre_output`
	    if [ $output_time -gt $pre_output_time ];
	    then
		return 1
	    else
		return 0
	    fi
	fi
    fi
    return 1
}

##################################################
# Start processing samples
##################################################
indir=$1
samples="${@:2}"
if [ ! -d "$indir" ]; then
    echo  $(date) "$indir not a directory"
    echo $USAGE
    exit
fi
if [ ! "$samples" ]; then
    echo  $(date) "No samples provided; please provide either sample names or a file listing sample names"
    echo $USAGE
    exit
fi
# Make sure indir is absolute path
if [ "`echo $indir | cut -c1`" != "/" ]; then
    echo  $(date) "$indir is not an absolute path; please use absolute path names for input directory"
    exit
fi

# Set input directories
if [ -f "$samples" ]; then
    echo  $(date) "Reading input directories from file $args"
    samples=`cat $samples`
else
    echo $(date) "Assuming input directories passed as argument list"
fi
sample_regexp=`echo $samples | sed -e s"/ /\|/"g`

# Find input files based on regular expressions that include sample names
# Here assuming casava-based file names
echo $(date) Finding files with command "'find $indir -regextype posix-extended -regex \".*(${sample_regexp}).*${READ1_REGEXP}.fastq.gz?\"'"
infiles=`find $indir -regextype posix-extended -regex ".*(${sample_regexp}).*${READ1_REGEXP}.fastq.gz?"`

echo $(date) "Going to run pipeline on " 
for f in $infiles; do 
    echo -e "\t" ${f%.fastq.gz}
done
read1=$infiles
read2=`echo $infiles | sed -e "s/${READ1_REGEXP}/${READ2_REGEXP}/g"`

##################################################
# Pipeline code
# The various steps follow a presentation on HaloPlex
# analysis obtained from Agilent
##################################################

##############################
# Primary analysis
##############################
# 1. QC
command=""
for f in $read1 $read2; do
    outdir=`dirname $f`/fastqc
    up_to_date  $outdir/`basename ${f%.fastq.gz}`_fastqc/summary.txt $f
    if [ $? = 1 ]; then continue; fi
    mkdir -p $outdir
    cmd="$FASTQC $f -o ${outdir}"
    command="$command\n$cmd"
done
echo -e $(date) 1. QC section 
echo -e $(date) $command
echo -e $command | $PARALLEL

# 2a. Trim adapter sequence
command=""
trimfiles=""
for f in $read1; do
    trimfiles="$trimfiles ${f%.fastq.gz}.trimmed.fastq.gz"
    up_to_date ${f%.fastq.gz}.trimmed.fastq.gz $f
    if [ $? = 1 ]; then continue; fi
    cmd="$CUTADAPT $CUTADAPT_OPTS -a $THREEPRIME $f -o ${f%.fastq.gz}.trimmed.fastq.gz > ${f%.fastq.gz}.trimmed.fastq.cutadapt_metrics"
    command="$command\n$cmd"
done
for f in $read2; do
    trimfiles="$trimfiles ${f%.fastq.gz}.trimmed.fastq.gz"
    up_to_date ${f%.fastq.gz}.trimmed.fastq.gz $f
    if [ $? = 1 ]; then continue; fi
    cmd="$CUTADAPT $CUTADAPT_OPTS -a $FIVEPRIME $f -o ${f%.fastq.gz}.trimmed.fastq.gz > ${f%.fastq.gz}.trimmed.fastq.cutadapt_metrics"
    command="$command\n$cmd"
done
echo -e $(date) 2a. Adapter trimming
echo -e $(date) $command
echo -e $command | $PARALLEL

# 2b. Resync mates - sometimes cutadapt cuts reads down to 0, so there
# are some reads without mates
sample_pfx=`for f in $read1; do echo ${f%_${READ1_REGEXP}.fastq.gz}; done`
command=""
syncfiles=""
for f in $sample_pfx; do
    syncfiles="$syncfiles ${f}_${READ1_REGEXP}.trimmed.sync.fastq.gz ${f}_${READ2_REGEXP}.trimmed.sync.fastq.gz"
    up_to_date ${f}_${READ1_REGEXP}.trimmed.sync.fastq.gz ${f}_${READ1_REGEXP}.trimmed.fastq.gz
    if [ $? = 1 ]; then continue; fi
    echo $(date) resyncing reads for ${f}_${READ1_REGEXP}.trimmed.fastq.gz, ${f}_${READ2_REGEXP}.trimmed.fastq.gz
    cmd="$RESYNCMATES -i ${f}_${READ1_REGEXP}.trimmed.fastq.gz -j ${f}_${READ2_REGEXP}.trimmed.fastq.gz -o ${f}_${READ1_REGEXP}.trimmed.sync.fastq.gz -p ${f}_${READ2_REGEXP}.trimmed.sync.fastq.gz"
    command="$command\n$cmd"
done
echo -e $(date) 2b. Resync mates
echo -e $(date) $command
echo -e $command | $PARALLEL

##############################
# Mapping - secondary analysis
##############################

# 3. Align sequences with bwa. Here we run command sequentially since
# bwa takes care of parallelization. From now on we run at sample level.
echo -e $(date) 3. Alignment
for f in $syncfiles; do
    up_to_date ${f%.fastq.gz}.sai $f
    if [ $? = 1 ]; then continue; fi
    echo $(date) aligning reads $f
    $BWA aln -t $N_CORES $BWA_REF $f > ${f%.fastq.gz}.sai 2>> $ERRFILE
done

# 4. Pair reads
command=""
for f in $sample_pfx; do
    label=`basename $f`
    extension="trimmed.sync"
    up_to_date $f.sam ${f}_${READ1_REGEXP}.${extension}.sai
    if [ $? = 1 ]; then continue; fi
    echo $(date) pairing reads for sample $f
    cmd="$BWA sampe -A -P -r \"@RG\tID:${label}\tSM:${label}\tPL:Illumina\tCN:Agilent\" $BWA_REF ${f}_${READ1_REGEXP}.${extension}.sai ${f}_${READ2_REGEXP}.${extension}.sai ${f}_${READ1_REGEXP}.${extension}.fastq.gz ${f}_${READ2_REGEXP}.${extension}.fastq.gz > $f.sam"
    command="$command\n$cmd"
done
echo -e $(date) 4. Pair reads
echo -e $(date) $command
echo -e $command | $PARALLEL

# 5. Generate bam file
command=""
for f in $sample_pfx; do
    up_to_date $f.sort.bam $f.sam
    if [ $? = 1 ]; then continue; fi
    echo $(date) generating bam file for $f
    echo "$SAMTOOLS view -bS $f.sam | $SAMTOOLS sort - $f.sort; $SAMTOOLS index $f.sort.bam "
    cmd="$SAMTOOLS view -bS $f.sam | $SAMTOOLS sort - $f.sort; $SAMTOOLS index $f.sort.bam;"
    command="$command\n$cmd"
done
echo -e $(date) 5. Generate sorted bam file
echo -e $(date) $command
echo -e $command | $PARALLEL

# 6. Generate various metrics for the bamfiles
command=""
for f in $sample_pfx; do
    input=$f.sort.bam
    # Alignment metrics
    up_to_date ${input%.bam}.align_metrics $input
    if [ $? = 0 ]; then 
	echo $(date) generating alignment metrics for $input
	cmd="java -jar $PICARD_HOME/CollectAlignmentSummaryMetrics.jar INPUT=$input OUTPUT=${input%.bam}.align_metrics REFERENCE_SEQUENCE=$REF"
	command="$command\n$cmd"
    fi
    # Insert size metrics
    up_to_date ${input%.bam}.insert_metrics $input
    if [ $? = 0 ]; then 
	echo $(date) generating insert size metrics for $input
	cmd="java -jar $PICARD_HOME/CollectInsertSizeMetrics.jar INPUT=$input OUTPUT=${input%.bam}.insert_metrics HISTOGRAM_FILE=${input%.bam}.insert_metrics REFERENCE_SEQUENCE=$REF"
	command="$command\n$cmd"
    fi
    # Hybrid selectien metrics
    up_to_date ${input%.bam}.hs_metrics
    if [ $? = 0 ]; then 
	if [ ! $BAIT_INTERVALS_FILE ] || [ ! $TARGET_INTERVALS_FILE ]; then
	    echo $(date) "Bait/target file missing; skipping hybrid metrics calculation"
	else 
	    echo $(date) generating hybrid selection metrics for $input
	    cmd="java -jar $PICARD_HOME/CalculateHsMetrics.jar INPUT=$input OUTPUT=${input%.bam}.hs_metrics BAIT_INTERVALS=$BAIT_INTERVALS_FILE TARGET_INTERVALS=$TARGET_INTERVALS_FILE REFERENCE_SEQUENCE=$REF"
	    command="$command\n$cmd"
	fi
    fi
    # Samstat statistics
    up_to_date $input.html $input
    if [ $? = 0 ]; then
	echo $(date) generating samstat metrics for $input
	cmd="$SAMSTAT $input"
	command="$command\n$cmd"
    fi
done
echo -e $(date) 6. Calculate metrics
echo -e $(date) $command
echo -e $command | $PARALLEL

##############################
# Variant calling, tertiary analysis
##############################

# 7. Raw variant calling 
# -L: interval_list(?) type input - bed format doesn't seem to work
UNIFIED_GENOTYPER_OPTS="-T UnifiedGenotyper --dbsnp $DBSNP -stand_call_conf 30.0 -stand_emit_conf 10.0  --downsample_to_coverage 30 --output_mode EMIT_VARIANTS_ONLY -glm BOTH -nt $N_CORES -R $REF -L $TARGET_REGION"
echo -e $(date) 7. Raw variant calling
for f in $sample_pfx; do
    input=$f.sort.bam
    up_to_date ${input%.bam}.BOTH.raw.vcf $input
    if [ $? = 1 ]; then continue; fi
    echo $(date) generating raw variant calls for $f
    java -jar $GATK $UNIFIED_GENOTYPER_OPTS -I $input -o ${input%.bam}.BOTH.raw.vcf
done
    

# 8. Realignment
REALIGNMENT_TARGET_CREATOR_OPTS="-T RealignerTargetCreator -L $TARGET_REGION -known $MILLS -known $THOUSANDG_OMNI -nt $N_CORES -R $REF"
echo -e $(date) 8. Realignment - generate realign target intervals
for f in $sample_pfx; do
    input=$f.sort.bam
    up_to_date ${input%.bam}.intervals $input
    if [ $? = 1 ]; then continue; fi
    echo $(date) generating realignment intervals for $input
    java -jar $GATK $REALIGNMENT_TARGET_CREATOR_OPTS -I $input -known ${input%.bam}.BOTH.raw.vcf -o ${input%.bam}.intervals 
done

# 9. Indel realignment
INDEL_REALIGNER_OPTS="-T IndelRealigner -known $MILLS -known $THOUSANDG_OMNI  -R $REF"
command=""
for f in $sample_pfx; do
    input=$f.sort.bam
    up_to_date ${input%.bam}.realign.bam $input
    if [ $? = 1 ]; then continue; fi
    cmd="java -jar $GATK $INDEL_REALIGNER_OPTS -I $input --targetIntervals ${input%.bam}.intervals -known ${input%.bam}.BOTH.raw.vcf -o ${input%.bam}.realign.bam"
    command="$command\n$cmd"
done
echo -e $(date) 9. Indel realignment
echo -e $(date) $command
echo -e $command | $PARALLEL

# 10. Base recalibration
# NB: currently BaseRecalibrator does *not* support multiple threads
RECALIBRATOR_OPTS="-T BaseRecalibrator -R $REF -L $TARGET_REGION --knownSites $DBSNP --knownSites $MILLS --knownSites $THOUSANDG_OMNI"
echo -e $(date) 10. Base recalibration
command=""
for f in $sample_pfx; do
    input=$f.sort.realign.bam
    up_to_date ${input%.bam}.recal_data.grp $input
    if [ $? = 1 ]; then continue; fi
    echo $(date) realigning $input
    cmd="java -jar $GATK $RECALIBRATOR_OPTS -I $input -o ${input%.bam}.recal_data.grp"
    command="$command\n$cmd"
done
echo -e $(date) $command
echo -e $command | $PARALLEL

# 11. Recalculate base quality score
PRINT_READS_OPTS="-T PrintReads -R $REF"
command=""
for f in $sample_pfx; do
    input=$f.sort.realign.bam
    up_to_date ${input%.bam}.recal.bam $input
    if [ $? = 1 ]; then continue; fi
    cmd="java -jar $GATK $PRINT_READS_OPTS -I $input -BQSR ${input%.bam}.recal_data.grp -o ${input%.bam}.recal.bam"
    #cmd="java -jar $GATK $PRINT_READS_OPTS -I $input -o ${input%.bam}.recal.bam"
    command="$command\n$cmd"
done
echo -e $(date) 11. Recalculate base quality score
echo -e $(date) $command
echo -e $command | $PARALLEL

