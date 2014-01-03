"""
Demultiplex haloplex data including molecular tags.
"""
# TODO add pairwise alignment of indexes to correct for sequencing error (biopython's Bio.pairwise2)
# TODO add directory parsing
# TODO support single-read runs (i.e. not paired-end)

from __future__ import print_function

import argparse
import Bio
import re
import sys

from itertools import izip
from scilifelab.utils.fastq_utils import FastQParser


def main(read_one, read_two, read_index, sample_sheet, halo_index_file, halo_index_length, molecular_tag_length=None):

    halo_index_dict, halo_index_revcom_dict = load_indexes(halo_index_file)
    parse_readset(read_one, read_two, read_index, halo_index_dict, halo_index_revcom_dict, halo_index_length, molecular_tag_length)


def parse_readset(read_1_fq, read_2_fq, read_index_fq, halo_index_dict, halo_index_revcom_dict, halo_index_length, molecular_tag_length=None):
    """
    Parse input fastq files by index reads.
    """
    fqp_1, fqp_2, fqp_ind = map(FastQParser, (read_1_fq, read_2_fq, read_index_fq))
    for read_1, read_2, read_ind in izip(fqp_1, fqp_2, fqp_ind):
        # Get the haloplex index and the molecular tag from the index read's sequence data
        halo_index, molecular_tag, index_name = parse_index(read_ind[1], halo_index_dict, halo_index_revcom_dict,
                                                            halo_index_length, molecular_tag_length)
        # TODO modify headers of the reads and split by index either in dict, yield, or write to file
        if halo_index and molecular_tag:
            print(halo_index, molecular_tag, index_name)


def parse_index(index_seq, halo_index_dict=None, halo_index_revcom_dict=None, halo_index_length=None, molecular_tag_length=None):
    """
    Split an index up into its haloplex index and the random molecular tag.
    Returns the halo index and the molecular tag as a tuple.
    """
    # TODO add check against known indexes (Bio.pairwise2) -- this will also determine default molecular tag length
    # TODO add pairwise alignment to known indexes to correct for sequencing errors
    halo_index, molecular_tag = index_seq[:halo_index_length], index_seq[halo_index_length:molecular_tag_length]
    if not halo_index in halo_index_dict.keys():
        if halo_index in halo_index_revcom_dict.keys():
            print("WARNING: No match to supplied indexes but match to reverse complement of supplied indexes. Double-check read direction.",
                  file=sys.stderr)
        return None, None, None
    index_name = halo_index_dict[halo_index]
    return halo_index, molecular_tag, index_name


def load_indexes(csv_file):
    """
    Load known indexes from a csv file.
    csv file should be in format:
        sequence[,index_name]
    where index_name is optional.
    Returns a dict of sequence->name pairs.
    """
    index_dict          = {}
    index_dict_revcom   = {}
    with open(csv_file, 'r') as f:
        for line in f:
            # could also use csv.sniffer to dynamically determine delimiter
            index = re.split(r'[\t,;]', line.strip())
            # include reverse complement
            rev_com_index = Bio.Seq.Seq(index[0]).reverse_complement().tostring()
            try:
                index_dict[index[0]]                = index[1]
                index_dict_revcom[rev_com_index]    = index[1]
            except IndexError:
                index_dict[index[0]]                = None
                index_dict_revcom[rev_com_index]    = None
    return index_dict, index_dict_revcom

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sample-sheet", help="Sample sheet describing the indexes used during library preparation.")
    parser.add_argument("-i", "--halo-index-file", required=True, help="File containing haloplex indexes (one per line, optional name in second column separated by tab, comma, or semicolon).")
    # TODO make this not required by dynamically matching to indexes
    parser.add_argument("-l", "--halo-index-length", type=int, required=True, help="The length of the haloplex index. Required if indexes are not supplied (option -i).")
    parser.add_argument("-m", "--molecular-tag-length", type=int, help="The length of the (random) molecular tag. If not specified, the remainder of the read after the halo index is used.")
    #parser.add_argument("-r", "--read-index", dest="read_index", type=int, help="Which read is the index.")
    #parser.add_argument("-s", "--single-read", dest="single_read", action="store_true", help="Specify that the data is single-read (not paired-end); default false.")
    #parser.add_argument("-d", "--directory", help="Directory containing demultiplexed data.")
    parser.add_argument("-1", "--read-one", required=True, help="Read 1 fastq file.")
    parser.add_argument("-2", "--read-two", required=True, help="Read 2 fastq file.")
    parser.add_argument("-r", "--read-index", required=True, help="Index read fastq file.")

    arg_vars = vars(parser.parse_args())

    main(**arg_vars)
