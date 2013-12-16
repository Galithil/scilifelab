"""
Demultiplex a CASAVA 1.8+ FastQ file based on the information in the middle read (r2 of 3)
Should be run in the Undetermined_indices folder
"""
import argparse
import collections
import os
#import sys
import time

from scilifelab.illumina.hiseq import HiSeqSampleSheet
from scilifelab.utils.fastq_utils import FastQParser, is_read_pair, FastQWriter, parse_header, gtQ30count, avgQ


def demultiplex(CSV, keepIndexes, indexesToExtract):
    sdata =  HiSeqSampleSheet(CSV)
    folderStruct = collections.defaultdict(lambda : collections.defaultdict(dict))
    outfiles = {}
    DemultiplexStats = {}
    counts = {}

    # Initialization of destination folder structure based on samplesheet info
    for sd in sdata:
        sampleProject = sd['SampleProject']
        sampleID = sd['SampleID']
        lane = sd["Lane"]
        index = sd["Index"]
        # this is kind of a weird conditional
        if indexesToExtract is None or index in indexesToExtract:
            if lane not in outfiles:
                outfiles[lane] = {}
                DemultiplexStats[lane] = {}
                counts[lane] = {}
            outfiles[lane][index] = []
            counts[lane][index] = 0
            read = 1
            read1 = "tmp_{}_{}_L00{}_R{}_001.fastq.gz".format(sampleID,
                                                              index,
                                                              lane,
                                                              read)
            read = 2
            read2 = "tmp_{}_{}_L00{}_R{}_001.fastq.gz".format(sampleID,
                                                              index,
                                                              lane,
                                                              read)
            # Index-specific fastq files
            folderStruct[sampleProject][sampleID][lane] = [read1, read2]
            projectDirName = "Project_{}".format(sampleProject)
            sampleDirName  = "Sample_{}".format(sampleID)
            outfiles[lane][index].append(os.path.join(projectDirName, sampleDirName, read1))
            outfiles[lane][index].append(os.path.join(projectDirName, sampleDirName, read2))
            ## now prepare Demultiplex stats
            DemultiplexStats[lane][index] = {'SampleID' : sampleDirName,
                                         'SampleRef': sd['SampleRef'],
                                         'Index'    : index,
                                         'Description': sd['Description'],
                                         'Control'    : sd['Control'],
                                         'Project'    : sampleProject,
                                         'numReads'   : 0,
                                         'Yeld'       : 0,
                                         'PF'         : 100, # not lcear how to set this one
                                         'lanePerc'   : 0,
                                         'Q30'        : 0,
                                         '0error'     : 0,
                                         '1error'     : 0,
                                         'meanQuality': 0,
                                         'Recipe'     : sd['Recipe'] ,
                                         'Operator'   : sd['Operator'],
                                         'Directory'  : os.path.join(os.getcwd(), projectDirName, sampleDirName)
                                         }
    for lane in outfiles:
        #create undetermined group
        outfiles[lane]["Undetermined"] = []
        read1 = "tmp_lane{}_Undetermined_L00{}_R{}_001.fastq.gz".format(lane, lane, 1)
        read2 = "tmp_lane{}_Undetermined_L00{}_R{}_001.fastq.gz".format(lane, lane, 2)
        projectDirName = "Undetermined_indices"
        sampleDirName = "Sample_lane{}".format(lane)
        outfiles[lane]["Undetermined"].append(os.path.join(projectDirName, sampleDirName, read1))
        outfiles[lane]["Undetermined"].append(os.path.join(projectDirName, sampleDirName, read2))
        folderStruct["Undetermined_indices"][sampleDirName][lane] = [read1, read2]
        DemultiplexStats[lane]['Undetermined'] = {'SampleID' : sampleDirName,
                                         'SampleRef'  : 'unknown',
                                         'Index'      : 'Undetermined',
                                         'Description': 'unmatched barcodes for lane {}'.format(lane),
                                         'Control'    : 'N',
                                         'Project'    : projectDirName,
                                         'numReads'   : 0,
                                         'Yeld'       : 0,
                                         'PF'         : 100, # not lcear how to set this one
                                         'lanePerc'   : 0,
                                         'Q30'        : 0,
                                         '0error'     : 0,
                                         '1error'     : 0,
                                         'meanQuality': 0,
                                         'Recipe'     : 'R1' ,
                                         'Operator'   : 'NN',
                                         'Directory'  : os.path.join(os.getcwd(), projectDirName, sampleDirName)
                                         }
        #create ambiguous group
        outfiles[lane]["Ambiguous"] = []
        read1 = "tmp_lane{}_Ambiguous_L00{}_R{}_001.fastq.gz".format(lane, lane, 1)
        read2 = "tmp_lane{}_Ambiguous_L00{}_R{}_001.fastq.gz".format(lane, lane, 2)
        projectDirName = "Ambiguous_indices"
        sampleDirName = "Sample_lane{}".format(lane)
        outfiles[lane]["Ambiguous"].append(os.path.join(projectDirName, sampleDirName, read1))
        outfiles[lane]["Ambiguous"].append(os.path.join(projectDirName, sampleDirName, read2))
        folderStruct["Ambiguous_indices"][sampleDirName][lane] = [read1, read2]
    ##Use folderStruct to build the folder structure of the experiment
    prepareDirectories(folderStruct, indexesToExtract)

    # Go through all the lanes extracted from the SampleSheet above (sd['lane'])
    for lane in outfiles:
        for index in outfiles[lane]:
            # the tmp files created above for each sample.lane.index
            files = outfiles[lane][index]
            # wtf
            outfiles[lane][index] = []
            for f in files:
                # nothing to write yet, just a Writer
                outfiles[lane][index].append(FastQWriter(f))
    demultiplex_lanes(outfiles, keepIndexes, DemultiplexStats)
    return


def prepareDirectories(folderStruct, indexesToExtract):
    """
    Create the directories according to the folder structure determined in the demultiplex() method
    using the information from the sample sheet.
    """
    for project in folderStruct:
        projectDirName = "Project_"+project
        if project is "Undetermined_indices":
            projectDirName = "Undetermined_indices"
        elif project is "Ambiguous_indices":
            projectDirName = "Ambiguous_indices"
        if indexesToExtract is None:
            assert not os.path.exists(projectDirName), \
                    "Directory {} already exist, I am not going to overwrite previous results".format(projectDirName)
        if not os.path.exists(projectDirName):
            os.mkdir(projectDirName)
        for sample in folderStruct[project]:
            sampleDirName = "Sample_" + sample
            if project is "Undetermined_indices" or project is "Ambiguous_indices":
                sampleDirName = sample
                if not os.path.exists(os.path.join(projectDirName, sampleDirName)):
                    os.mkdir(os.path.join(projectDirName, sampleDirName))
            else:
                assert not os.path.exists(os.path.join(projectDirName, sampleDirName)), \
                        "Directory {} already exists, I am not going to overwrite previous results".format(sampleDirName)
                os.mkdir(os.path.join(projectDirName, sampleDirName))



def change_index(header, new_index):
    """
    Changes the index field in the header with the one specified in a FASTQ header as specified by CASAVA 1.8.2
    and returns the new header
    @<instrument>:<run number>:<flowcell ID>:<lane>:<tile>:<x-pos>:<y-pos> <read>:<is filtered>:<control number>:<index sequence>
    """
    if header[0] != '@':
        return None

    instrument, run_number, flowcell_id, lane, tile, x_pos, y_pos_read, is_filtered, control_number, _ = header[:].split(":")
    new_header = ":".join([instrument, run_number, flowcell_id, lane, tile, x_pos, y_pos_read, is_filtered, control_number, new_index])
    return new_header

def demultiplex_lanes(outfiles, keepIndexes, DemultiplexStats):
    """
    Demultiplex multiple lanes
    """
    for lane in outfiles:
        unmultiplexedDirForLane = "Sample_lane"+lane
        if os.path.exists(unmultiplexedDirForLane):
            unmultiplexedFileRead1      = "lane{}_Undetermined_L00{}_R{}_001.fastq".format(lane, lane, 1)
            unmultiplexedFileReadInd    = "lane{}_Undetermined_L00{}_R{}_001.fastq".format(lane, lane, 2)
            unmultiplexedFileRead2      = "lane{}_Undetermined_L00{}_R{}_001.fastq".format(lane, lane, 3)
            if not( os.path.exists(os.path.join(unmultiplexedDirForLane, unmultiplexedFileRead1)) and \
                    os.path.exists(os.path.join(unmultiplexedDirForLane, unmultiplexedFileRead2))):
                unmultiplexedFileRead1      = "lane{}_Undetermined_L00{}_R{}_001.fastq.gz".format(lane, lane, 1)
                unmultiplexedFileReadInd    = "lane{}_Undetermined_L00{}_R{}_001.fastq.gz".format(lane, lane, 2)
                unmultiplexedFileRead2      = "lane{}_Undetermined_L00{}_R{}_001.fastq.gz".format(lane, lane, 3)
            assert  os.path.exists(os.path.join(unmultiplexedDirForLane, unmultiplexedFileRead1)) and \
                    os.path.exists(os.path.join(unmultiplexedDirForLane, unmultiplexedFileRead2)), \
                    "Error in lane {} folder {}: folder exists but" \
                    "no read file present: this is unexpected".format(lane, unmultiplexedDirForLane)
            DemultiplexStats = demultiplex_lane(unmultiplexedDirForLane, unmultiplexedFileRead1,
                                                unmultiplexedFileRead2, unmultiplexedFileReadInd,
                                                outfiles, keepIndexes, DemultiplexStats)
        else:
            print 'Lane {0} with folder {1} not found'.format(lane, unmultiplexedDirForLane)

    print   "Lane SampleID SampleRef Index Description Control Project" \
            "Yield(Mbases) %PF #Reads %ofRawClustersPerLane %PerfectIndexReads" \
            "%OneMismatchReads(Index) %of>=Q30Bases(PF) MeanQualityScore(PF)"
    for lane in DemultiplexStats:
        for index in DemultiplexStats[lane]:
            print "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {}".format(lane,
                                                                        DemultiplexStats[lane][index]['SampleID'],
                                                                        DemultiplexStats[lane][index]['SampleRef'],
                                                                        DemultiplexStats[lane][index]['Index'],
                                                                        DemultiplexStats[lane][index]['Description'],
                                                                        DemultiplexStats[lane][index]['Control'],
                                                                        DemultiplexStats[lane][index]['Project'],
                                                                        DemultiplexStats[lane][index]['Yeld'],
                                                                        DemultiplexStats[lane][index]['PF'],
                                                                        DemultiplexStats[lane][index]['numReads'],
                                                                        DemultiplexStats[lane][index]['lanePerc'],
                                                                        DemultiplexStats[lane][index]['0error'],
                                                                        DemultiplexStats[lane][index]['1error'],
                                                                        DemultiplexStats[lane][index]['Q30'],
                                                                        DemultiplexStats[lane][index]['meanQuality']
                                                                        )

    print "here it goes information about the samples --> to be build"
#DemultiplexStats[lane][index]['Recipe']
#DemultiplexStats[lane][index]['Operator']
#DemultiplexStats[lane][index]['Directory']


def demultiplex_lane(unmultiplexedFolder, unmultiplexedFastq1, unmultiplexedFastq2, unmultiplexedFastqInd, outfiles, keepIndexes, DemultiplexStats):
    """
    Demultiplex just the one lane
    """
    fp1     = FastQParser(os.path.join(unmultiplexedFolder, unmultiplexedFastq1))
    fp2     = FastQParser(os.path.join(unmultiplexedFolder, unmultiplexedFastq2))
    fpind   = FastQParser(os.path.join(unmultiplexedFolder, unmultiplexedFastqInd))
    numReadInLane = 0
    lane_r1 = 0
    oldTime = time.clock()
    for r1, r2, rind in fp1, fp2, fpind:
        assert is_read_pair(r1, r2), "Mismatching headers for expected read pair"
        header_r1 = parse_header(r1[0])
        lane_r1 = str(header_r1['lane'])
        #index_r1 = header_r1['index']
        # TODO make the lengths configurable
        # first 8 are sequence
        index       = rind['seq'][:8]
        # final 10 are molecular barcode
        #mol_index   = rind['seq'][8:]

        # NOTE  This outfiles[lane_r1] is a dict for which the keys are all the
        #       indexes gleaned from the SampleSheet
        real_index, num_mismatches = check_index(index, outfiles[lane_r1])
        numReadInLane += 2
        currentTime  = time.clock()
        if numReadInLane % 1000000 == 0:
            print "processing reads 1000000 reads in {}".format(currentTime - oldTime)
            oldTime = currentTime
        if not keepIndexes and real_index is not 'Undetermined' and real_index is not 'Ambiguous':
            r1[0] = change_index(r1[0], real_index)
            r2[0] = change_index(r2[0], real_index)
        # WRITE THE DATA
        # TODO where to add the molecular barcode?
        outfiles[lane_r1][real_index][0].write(r1)
        outfiles[lane_r1][real_index][1].write(r2)
        if real_index is not 'Ambiguous':
            DemultiplexStats[lane_r1][real_index]['Yeld']       += len(r1[1]) + len(r2[1])
            #DemultiplexStats[lane_r1][real_index]['PF']         = 1
            DemultiplexStats[lane_r1][real_index]['numReads']   += 2
            DemultiplexStats[lane_r1][real_index]['lanePerc']   += 2
            if num_mismatches == 0:
                DemultiplexStats[lane_r1][real_index]['0error'] += 2
            elif num_mismatches == 1:
                DemultiplexStats[lane_r1][real_index]['1error'] += 2
            DemultiplexStats[lane_r1][real_index]['Q30']        += (gtQ30count(r1) + gtQ30count(r2))
            DemultiplexStats[lane_r1][real_index]['meanQuality'] += (avgQ(r1) + avgQ(r2))
    for index in DemultiplexStats[lane_r1]:
        if index is not "Ambiguous":
            if DemultiplexStats[lane_r1][index]['Yeld'] > 0:
                DemultiplexStats[lane_r1][index]['Q30']     = round(100*float(  DemultiplexStats[lane_r1][index]['Q30']) / \
                                                                                DemultiplexStats[lane_r1][index]['Yeld'],2)
                DemultiplexStats[lane_r1][index]['Yeld']    = round(    float(  DemultiplexStats[lane_r1][index]['Yeld'])/1000, 2)
                DemultiplexStats[lane_r1][index]['lanePerc']= round(100*float(  DemultiplexStats[lane_r1][index]['lanePerc'])/numReadInLane, 2)
                DemultiplexStats[lane_r1][index]['0error']  = round(100*float(  DemultiplexStats[lane_r1][index]['0error']) / \
                                                                                DemultiplexStats[lane_r1][index]['numReads'],2)
                DemultiplexStats[lane_r1][index]['1error']  = round(100*float(  DemultiplexStats[lane_r1][index]['1error'])/ \
                                                                                DemultiplexStats[lane_r1][index]['numReads'],2)
                DemultiplexStats[lane_r1][index]['meanQuality'] = round(float(  DemultiplexStats[lane_r1][index]['meanQuality']) / \
                                                                                DemultiplexStats[lane_r1][index]['numReads'],2)
    return DemultiplexStats


def check_index(index_r1 , indexes_present_in_lane):
    """
    Check the index against the filter list passed.
    """
    # indexes_present_in_lane is a list of the indices for a specific lane pulled from the SampleSheet
    num_matches = 0
    best_match  = 0
    index_matched = ""
    for index in indexes_present_in_lane:
        indexLength = len(index)
        index_to_compare = index_r1[0:indexLength]
        num_mismatches = hamdist(index_to_compare, index, 2)
        if num_mismatches <= 1:
            index_matched = index
            best_match    = num_mismatches
            num_matches += 1
    if num_matches == 1:
        return index_matched, best_match
    elif num_matches == 0:
        return "Undetermined", best_match
    else:
        return "Ambiguous", best_match


def hamdist(str1, str2, max_dist):
    """
    Count the # of differences between equal length strings str1 and str2
    """
    diffs = 0
    for ch1, ch2 in zip(str1, str2):
        if ch1 != ch2:
            diffs += 1
        if diffs >= max_dist:
            break
    return diffs

def check_input(indexes, CSV):
    """
    Francesco doesn't write docstrings
    """
    sdata =  HiSeqSampleSheet(CSV)
    indexes_in_CSV = {}
    for sd in sdata:
        indexes_in_CSV[sd["Index"]] = 0
    for index in indexes:
        assert index in indexes_in_CSV, "index {} is not present in {}: please specify" \
                "only indexes that are present in the sample sheet file".format(index, CSV)

def main():
    """
    An oddly superfluous function
    """

    parser = argparse.ArgumentParser(description="Demultiplex a CASAVA 1.8+ FastQ file based on the information in the fastq header")


    parser.add_argument('CSV', action='store', help="CSV file describing the experiment")
    parser.add_argument('--indexes',  nargs='+', help='sprcify which index(es) you want to demultiplex')
    parser.add_argument('--keepIndexes', action='store_true', help="if specified does not trim the index (keeps the one used to demultiplex)")

    args = parser.parse_args()

    if args.indexes is not None:
        check_input(args.indexes, args.CSV)

    demultiplex(args.CSV , args.keepIndexes, args.indexes )



if __name__ == "__main__":
    main()

