#!/usr/bin/env python
import os
import sys
import yaml
from optparse import OptionParser

def _printer(verbose):
    if verbose:
        def vprint(S):
            print(S)
    else:
        def vprint(S):
            pass
    return vprint

def main(run_info_yaml, lane, out_file, genome_build, barcode_type, trim, ascii, analysis, description, clear_description, verbose):
    
    vprint = _printer(verbose)
    vprint("Verifying that {} exists".format(run_info_yaml))
    assert os.path.exists(run_info_yaml)
    vprint("Parsing {}".format(run_info_yaml))
    with open(run_info_yaml) as fh:
        run_info = yaml.load(fh)

    vprint("Extracting lane info")
    if lane == 0:
        lane_info = run_info
    else:
        for info in run_info:
            if (int(info.get("lane",0)) == lane):
                lane_info = [info]
                break
    for info in lane_info:
        vprint("Processing lane {}".format(info["lane"]))
        _process_info(info,genome_build,barcode_type,trim,ascii,analysis,description,clear_description,vprint)
    
    if out_file is not None:
        with open(out_file,'w') as fh:
            yaml.dump(run_info, fh, allow_unicode=True, default_flow_style=False)
    else:
        print yaml.dump(run_info, allow_unicode=True, default_flow_style=False)
        
        
def _process_info(info,genome_build,barcode_type,trim,ascii,analysis,description,clear_description,vprint):
    
    if genome_build is not None:
        vprint("\tSetting genome build: {}".format(genome_build))
        info['genome_build'] = genome_build
    if analysis is not None:
        vprint("\tSetting analysis: {}".format(analysis))
        info['analysis'] = analysis
    if description is not None:
        vprint("\tSetting description: {}".format(description))
        info['description'] = description
    if ascii and 'description' in info:
        vprint("\tEnsuring ascii")
        info['description'] = _replace_ascii(info['description'])
        
    for multiplex in info.get('multiplex',[]):
        vprint("\tProcessing multiplexed barcode id {}".format(multiplex['barcode_id']))
        if barcode_type is not None:
            vprint("\t\tSetting barcode_type: {}".format(barcode_type))
            multiplex['barcode_type'] = barcode_type
        if trim > 0:
            vprint("\t\tTrimming {} nucleotides from end of barcode".format(trim))
            multiplex['sequence'] = multiplex['sequence'][0:(-1*trim)]
        if clear_description and 'description' in multiplex:
            del multiplex['description']
        if ascii:
            vprint("\t\tEnsuring ascii")
            if 'sample_prj' in multiplex:
                multiplex['sample_prj'] = _replace_ascii(multiplex['sample_prj'])
            if 'description' in multiplex:
                multiplex['description'] = _replace_ascii(multiplex['description'])
    
def _replace_ascii(str):
    # Substitute swedish characters for sensible counterparts
    str = str.replace(u'\xc5','A')
    str = str.replace(u'\xe5','a')
    str = str.replace(u'\xc4','A')
    str = str.replace(u'\xe4','a')
    str = str.replace(u'\xd6','O')
    str = str.replace(u'\xf6','o') 
    return str.encode('ascii','replace')
 
if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-l", "--lane", dest="lane", default=0)
    parser.add_option("-o", "--out_file", dest="out_file", default=None)
    parser.add_option("-g", "--genome_build", dest="genome_build", default=None)
    parser.add_option("-b", "--barcode_type", dest="barcode_type", default=None)
    parser.add_option("-t", "--trim", dest="trim", default=0)
    parser.add_option("-a", "--analysis", dest="analysis", default=None)
    parser.add_option("-d", "--description", dest="description", default=None)
    parser.add_option("-c", "--clear_description", dest="clear_description", default=False, \
                                                        action="store_true")
    parser.add_option("-i", "--ascii", dest="ascii", default=False, \
                                                        action="store_true")
    parser.add_option("-v", "--verbose", dest="verbose", default=False, \
                                                        action="store_true")
    options, args = parser.parse_args()
    if len(args) == 1:
        run_info_yaml, = args
    else:
        print __doc__
        sys.exit()

    main(run_info_yaml, int(options.lane), options.out_file, 
            options.genome_build, options.barcode_type, int(options.trim), \
            options.ascii, options.analysis, options.description, options.clear_description, options.verbose)
    
