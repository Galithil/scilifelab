#!/usr/bin/env python
import os
import sys
import glob
import operator
import csv
import re
from optparse import OptionParser
from Bio.SeqIO.QualityIO import FastqGeneralIterator
from Bio import SeqIO

from bcbio.solexa.run_configuration import IlluminaConfiguration

def main(run_dir):
    runobj = MiSeqRun(run_dir)
    runobj._split_fastq()
    
def group_fastq_files(fastq_files):
    """Divide the input fastq files into batches based on lane and read, ignoring set"""
        
    regexp = r'_(L\d+)_([RI]\d+)_'
    batches = {}
    for fastq_file in fastq_files:
        m = re.search(regexp, fastq_file)
        if not m or len(m.groups()) < 2:
            print "WARNING: Could not determine lane and read from input file %s" % fastq_file
            continue
        
        batch = "%s%s" % (m.group(1).strip(),m.group(2).strip())
        if batch not in batches:
            batches[batch] = []
        batches[batch].append(fastq_file)

    return batches.values()

    
class MiSeqRun:
    
    def __init__(self, run_dir):
        self._run_dir = os.path.normpath(run_dir)
        assert os.path.exists(self._run_dir), "The path %s is invalid" % self._run_dir
        ss_file = self._find_samplesheet()
        if ss_file is not None:
            samplesheet = MiSeqSampleSheet(ss_file)
            self.samplesheet = samplesheet
        
        self._run_config = IlluminaConfiguration(run_dir)
        self._fastq = self._fastq_files()
        
    def _data_dir(self):
        return os.path.join(self._run_dir,"Data")
    def _intensities_dir(self):
        return os.path.join(self._data_dir(),"Intensities")
    def _basecalls_dir(self):
        return os.path.join(self._intensities_dir(),"BaseCalls")
    def _multiplex_dir(self):
        return os.path.join(self._basecalls_dir(),"Multiplex")
    def _alignment_dir(self):
        return os.path.join(self._basecalls_dir(),"Alignment")
    
    def _fastq_files(self, fastq_dir=None):
        if fastq_dir is None:
            fastq_dir = self._basecalls_dir()
        
        fastq_files = group_fastq_files(glob.glob(os.path.join(fastq_dir,"*.fastq*")))
        
#        indexreads = len(self._run_config.indexread())
#        nonindexreads = self._run_config.readcount() - indexreads
#        
#        fastq_files = []
#        for read in range(nonindexreads):
#            fastq_files.append(glob.glob(os.path.join(fastq_dir,"*_R%s_*.fastq*" % (read+1))))
#        for read in range(indexreads):
#            fastq_files.append(glob.glob(os.path.join(fastq_dir,"*_I%s_*.fastq*" % (read+1))))
#        
        return fastq_files
    
    def _find_samplesheet(self):
        dirs = [self._run_dir,
                self._basecalls_dir()]
        for dir in dirs:
            ss = os.path.join(dir,"SampleSheet.csv")
            if os.path.exists(ss):
                return ss
        return None
    
    def _split_fastq(self):
        
        samples = self.samplesheet.sample_names()
        samples.insert(0,"unmatched")
        sample_names = {}
        for i,name in enumerate(samples):
            sample_names[str(i)] = name
        
        out_dir = self._multiplex_dir()
        
        import split_demultiplexed 
        split_demultiplexed._split_fastq_batches(self._fastq,out_dir,sample_names)

class MiSeqSampleSheet:
    
    def __init__(self, ss_file):
        assert os.path.exists(ss_file), "Samplesheet %s does not exist" % ss_file
        setattr(self,"samplesheet",ss_file)
        self._parse_sample_sheet()
        
    def _parse_sample_sheet(self):
        
        # Parse the samplesheet file into a data structure
        data = {}
        with open(self.samplesheet,"r") as fh:
            current = None
            for line in fh:
                line = line.strip()
                if line.startswith("["):
                    current = line.strip("[], ")
                    data[current] = {}
                else:
                    [opt,val] = line.split(",",1)
                    data[current][opt] = val
    
        # Assign the parsed attributes to class attributes
        for option, value in data.get("Header",{}).items():
            setattr(self, option, value)
        for option, value in data.get("Settings",{}).items():
            setattr(self, option, value)
        
        # Parse sample data
        first_data_col = "Sample_ID"
        if "Data" in data and first_data_col in data["Data"]:
            data_header = data["Data"][first_data_col].split(",")
            samples = {}
            for sample_id, sample_data in data["Data"].items():
                if sample_id == first_data_col: continue
                samples[sample_id] = dict(zip(data_header,sample_data.split(",")))
                samples[sample_id][first_data_col] = sample_id
            setattr(self, "samples", samples)

    def sample_names(self):
        """Return the name of the samples in the same order as they are listed in
        the samplesheet.
        """
        samples = getattr(self,"samples",{})
        
        if getattr(self, "_sample_names", None) is None:
            sample_names = []
            with open(self.samplesheet,"r") as fh:
                for line in fh:
                    if line.startswith("[Data]"):
                        for line in fh:
                            data = line.split(",")
                            if len(data) == 0 or data[0].startswith("["):
                                break
                            if data[0] in samples:
                                sample_names.append(data[0])
            self._sample_names = sample_names
        
        return self._sample_names
        
        
    def sample_field(self, sample_id, sample_field=None):
        samples = getattr(self,"samples",{})
        assert sample_id in samples, "The sample '%s' was not found in samplesheet %s" % (sample_id,self.samplesheet)
        if sample_field is None:
            return samples[sample_id]
        assert sample_field in samples[sample_id], "The sample field '%s' was not found in samplesheet %s" % (sample_field,self.samplesheet)
        return samples[sample_id][sample_field] 

    
if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--samplesheet", dest="samplesheet", default=None)
    #parser.add_option("-n", "--dry-run", dest="dryrun", action="store_true", default=False)
    options, args = parser.parse_args()
    
    
    main(args[0])
