import sys
from bcbio.pipeline.config_loader import load_config

if len(sys.argv) < 6:
        print """
Usage:

make_RseqQc_gbc.py  <sample_name> <bed_file> <mail> <config_file> <path> 

        sample_name		This name: /tophat_out_<sample name>
        bed_file      
        mail                  	eg: jun.wang@scilifelab.se
        config_file           	post_process.yaml assumes that you have specified samtools 
                                version under 'custom_algorithms'/'RNA-seq analysis'
        path                  	Path to analysis dir containing the tophat_out_ directories
        """
        sys.exit()

name            = sys.argv[1]
bed_file        = sys.argv[2]
mail            = sys.argv[3]
config_file     = sys.argv[4]
path            = sys.argv[5]

try:
    config  = load_config(config_file)
    extra_arg=config['sbatch']['extra_arg']
    tools   = config['custom_algorithms']['RNA-seq analysis']
    sam     = tools['sam']+'/'+tools['sam_version']
    rseqc_version = tools['rseqc_version']
except:
    print 'ERROR: problem loading samtools version from config file'


f=open("RSeQC_"+name+"_gbc.sh",'w')

print >>f, """#!/bin/bash -l 
#SBATCH -A a2012043
#SBATCH -p core -n 6
#SBATCH -t 50:00:00
#SBATCH -e RSeQC_gbc_{0}.err
#SBATCH -o RSeQC_gbc_{0}.out
#SBATCH -J RSeQC_gbc_{0}
#SBATCH --mail-type=ALL
#SBATCH --mail-user={1}
#SBATCH {5}

module load bioinfo-tools
module unload samtools
module load {3}
module load rseqc/{6}
cd {4}

geneBody_coverage.py -i tophat_out_{0}/accepted_hits_sorted_{0}.bam -r {2} -o {0}
#CMD BATCH {0}.geneBodyCoverage_plot.r
""".format(name, mail, bed_file, sam, path, extra_arg, rseqc_version)
