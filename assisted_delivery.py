# A script to help doing the deliveries.

# The user is asked to provide a project ID, a run name, and an UPPMAX project

import sys, os, yaml, glob, shutil
from datetime import datetime

if len(sys.argv) < 5:
    print "USAGE: python " + sys.argv[0] + " <project ID> <run name> <UPPMAX project> <Dry run, y/n>"
    sys.exit(0)

#base_path = '/bubo/proj/a2010002/nobackup/romanvg/'
base_path = '/proj/a2010002/nobackup/pontus/'
dry = True

projid = sys.argv[1].lower()
runname = sys.argv[2].strip("/")
yamlfile = base_path + 'store/' + runname + "/run_info.yaml"
uppmaxproj = sys.argv[3]

if sys.argv[4].lower() == "n": dry = False

projdata = yaml.load(open(yamlfile))

dt = datetime.now()
time_str  = str(dt.year) + "_" + str(dt.month) + "_" + str(dt.day) + "_" + str(dt.hour) + "_" + str(dt.minute) + "_" + str(dt.second)

if not dry:
    logfilename = "/bubo/home/h9/mikaelh/delivery_logs/" + time_str + ".log" 
    logfile = open(logfilename, "w")

print "Project to copy files for:", projid
if not dry: logfile.write("Project to copy files for:" + "\n" + projid + "\n")

matching = set()
available = set()

for entry in projdata:
    available.add(entry['description'].split(',')[-1].strip())
    if entry['description'].split(',')[-1].strip().lower()==projid: 
        matching.add(entry['lane'])
    elif entry.has_key('multiplex'):
            for sample in entry['multiplex']:
                if sample.has_key('description'):
                    available.add(sample['description'])
                    if sample['description'].split(',')[-1].strip().lower()==projid: 
                        matching.add(entry['lane'])
                    
if len(matching)==0:
    print "No matching project found. Possibilities:"
    for prid in sorted(available):
        print prid
    sys.exit(0)

elif dry:
    print "I will copy files from lanes " + ",".join(matching) 

if not dry: logfile.flush()

# Create directory in user's INBOX

temp = runname.split('_')
start_date = temp[0]
flow_cell = temp[3][0] # A or B
created_dir_name = "20" + start_date + flow_cell + "_hiseq2000"

del_path = '/bubo/proj/' +  uppmaxproj + "/INBOX/" + created_dir_name

print "Will create a delivery directory", del_path       
if not dry: 
    logfile.write("Creating delivery directory:" + del_path + " (or leaving it in place if already present)\n")
    if os.path.exists(del_path):
        print "Directory", del_path, " already exists!"
    else:
        try:
            os.mkdir(del_path)
        except:
            print "Could not create delivery directory!"
            sys.exit(0)

# Start looking for the files to transfer

temp = runname.split('_')
dirs_to_process = []
for m in sorted(matching):
    d = m + "_" + temp[0] + "_" + temp[3] 
    dirs_to_process.append(d)

os.chdir(base_path + runname)

for d in dirs_to_process:
    dirpath = d + "_barcode"
    
    if not os.path.exists(dirpath):
        print "Could not find directory", dirpath 
        sys.exit(0)
    os.chdir(dirpath)
    bcname = d + "_bc.metrics"
    lane = dirpath[0]
    print "LANE ", lane
    if not dry: logfile.write("LANE " + lane + "\n")
# Print table of Illumina vs. bcbb barcodes
    sample_id_and_idx = {}
    lane_info = "none"
    # 
    main_proj_for_lane = ''
    for entry in projdata:
        if entry['lane'] == lane:
            lane_info = entry
            is_main_proj = True
            main_proj_for_lane = entry['description'].split(',')[-1].strip().lower() 
            if main_proj_for_lane == projid:
                print projid, "is the main project for lane", lane
            else:
                print "This project is not the main project for lane ", lane, ". The main project is ", main_proj_for_lane
                is_main_proj = False

    lane_sample = ''
    if lane_info.has_key('multiplex'):
        for bc in lane_info['multiplex']:
            if bc.has_key('description'):
                if bc['description'].split(',')[-1].strip().lower() == projid:
                    sample_id_and_idx[bc['barcode_id']] = bc['name']
            elif is_main_proj:
                sample_id_and_idx[bc['barcode_id']] = bc['name']

        print "Pipeline index\tSampleName\t# matching sequences"
        if not dry: logfile.write("Pipeline index\tIllumina index/sample ID\tMatches\n")
        if os.path.exists(bcname):
            for line in open(bcname):
                [bcbb_bc, hits] = line.strip().split()
                try:
                    if sample_id_and_idx.has_key(int(bcbb_bc)): print bcbb_bc + "\t" + sample_id_and_idx[int(bcbb_bc)] + "\t" + hits
                    if not dry: logfile.write(bcbb_bc + "\t" + sample_id_and_idx[int(bcbb_bc)] + "\t" + hits + "\n")
                except:
                    if bcbb_bc == "unmatched": 
                        print bcbb_bc + "\t" + "N.A." + "\t" + hits 
                        if not dry: logfile.write(bcbb_bc + "\t" + "N.A." + "\t" + hits + "\n")
                    else:
                        print "Encountered parsing error in barcode conversion: " + bcbb_bc
                        print sample_id_and_idx
                        sys.exit(0)              
        else:
            print "BC metrics file", bcname, " not found"
            sys.exit(0)

    else:
        print "Non-multiplexed lane"
        print "Please type a sample name for this lane"
        lane_sample = raw_input()
        if not dry: logfile.write("Non-multiplexed lane\n")

    # print os.listdir(".")
    files_to_copy = []

    for fastq_file in glob.glob("*fastq.txt"):
        if lane_info.has_key('multiplex'):
            new_file_name = ''
            if 'unmatched' in fastq_file: continue
            # Extract barcode
            [lane, date, run_id, bcbb_bc, pe_read, dummy] = fastq_file.split("_")
            if sample_id_and_idx.has_key(int(bcbb_bc)):
                customer_sample_id = sample_id_and_idx[int(bcbb_bc)]
                new_file_name = lane + "_" + date + "_" + run_id + "_" + customer_sample_id.replace("/", "_") + "_" + pe_read + ".fastq"   
        else:
            [lane, date, run_id, name, pe_read,dummy] = fastq_file.split("_")
            new_file_name = lane + "_" + date + "_" + run_id + "_" + lane_sample + "_" + pe_read + ".fastq"   
       #  print "Preparing to copy file", fastq_file, "as ", new_file_name
        if new_file_name != '': files_to_copy.append([fastq_file, new_file_name])

    for pair in files_to_copy:
        source = os.getcwd() + "/" + pair[0]
        dest = del_path + "/" + pair[1]
        
        if not dry: 
            print "Copying from " + source + " to " + dest
            logfile.write("Copying " + source + " to " + dest + "\n")
            logfile.flush()
            shutil.copyfile(source, dest)
        else:
            print "Will copy from ", source, "to", dest

    os.chdir('..')

if not dry: 
    logfile.close()
    os.system("chmod -R g+rw " + del_path)
