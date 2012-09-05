#!/usr/bin/env python
import os
import sys
import glob
import yaml
import time
import ConfigParser
import subprocess
import stat
import logbook
import copy
from optparse import OptionParser
from hashlib import md5
from miseq_data import MiSeqRun

from bcbio.utils import safe_makedir
from bcbio.pipeline.config_loader import load_config

DEFAULT_CONF = {
                "transfer_db": os.path.join("~","log","miseq_transferred.db"),
                "logfile": os.path.join("~","log","miseq_deliveries.log"),
                "samplesheet_name": "SampleSheet.csv",
                "fastq_path": os.path.join("Data","Intensities","BaseCalls"),
                "project_root": os.path.join("/proj"),
                "uppnexid_field": "Description",
                "smtp_host": "smtp.uu.se",
                "smtp_port": 25,
                "email_recipient": "seqmaster@scilifelab.se",
                "force": false,
                "dryrun": false
                }

LOG_NAME = "Miseq Delivery"
logger2 = logbook.Logger(LOG_NAME)

def update_config_with_local(config, local):
    cconf = copy.deepcopy(config)
    for key in local.keys():
        if local[key] is not None:
            cconf[key] = local[key]
    return cconf
    

def process_run_folder(run_folder, transferred_db, force=false, dry_run=false):
                
    # Skip this folder if it has already been processed
    logger2.info("Processing %s" % run_folder)
    if _is_processed(run_folder,transferred_db) and not force:
        logger2.info("%s has already been processed, skipping" % run_folder) 
        return
 
    # Create a MiSeqRun object from the run_folder
    miseqrun = MiSeqRun(run_folder)
    
    
                # Locate the samplesheet and pasre the uppnex id if necessary
                if uppnexid is None:
                    local_samplesheet = samplesheet
                    if local_samplesheet is None: local_samplesheet = os.path.join(input_path,folder,config.get("samplesheet_name",DEFAULT_SS_NAME))
                    assert os.path.exists(local_samplesheet), "Could not find expected sample sheet %s" % local_samplesheet
                    local_uppnexid = _fetch_uppnexid(local_samplesheet, config.get("uppnexid_field",DEFAULT_UPPNEXID_FIELD))
                    assert local_uppnexid is not None and len(local_uppnexid) > 0, "Could not parse Uppnex ID for project from samplesheet %s" % local_samplesheet
                else:
                    local_uppnexid = uppnexid
                    
                logger2.info("Will deliver to inbox of project %s" % local_uppnexid)
                   
    
            

def main(input_path, transferred_db=None, run_folder=None, uppnexid=None, samplesheet=None, logfile=None, email_notification=None, config_file=None, force=None, dryrun=None):

    local_conf = update_config_with_local(DEFAULT_CONF, 
    
    
    config = DEFAULT_CONF
    if config_file is not None:
        config = update_config_with_local(config,load_config(config_file))
    config = update_config_with_local(config,{
                                              "transfer_db": transferred_db,
                                              "logfile": logfile,
                                              "samplesheet_name": samplesheet,
                                              "uppnexid": uppnexid,
                                              "run_folder": run_folder,
                                              "email_recipient": email_notification,
                                              "force": force,
                                              "dryrun": dryrun
                                              }
                                      )
    
    email_handler = None
    # Don't write dry runs to log
    dryrun = config["dryrun"]
    if dryrun:
        handler = logbook.StreamHandler(sys.stdout)
    else:
        # Log to the logfile
        logfile = config["logfile"]
        if not os.path.exists(logfile):
            safe_makedir(os.path.dirname(logfile))
            open(logfile,"w").close()
        handler = logbook.FileHandler(logfile)
        
        # If email recipients were specified, setup logging via email
        recipients = config["email_recipient"].split(",")
        if len(recipients) > 0:
            email_handler = logbook.MailHandler("seqmaster@scilifelab.se", recipients, 
                                                server_addr=[config["smtp_host"],config["smtp_port"]],
                                                format_string=u'''Subject: [MiSeq delivery] {record.extra[run]}\n\n {record.message}''')
                                          
    with handler.applicationbound():
        
        if dryrun:
            logger2.info("This is just a dry-run. Nothing will be delivered and no directories will be created/changed")
            
        # If no run folder was specified, try with the folders in the input_path
        run_folder = config.get("run_folder",None)
        if run_folder is None:    
            pat = "*_M*_AMS*"
            folders = [os.path.relpath(os.path.normpath(file),input_path) for file in glob.glob(os.path.join(input_path,pat))]
        else:
            run_folder = os.path.basename(os.path.normpath(run_folder))
            assert os.path.exists(os.path.join(input_path,run_folder)), "The specified run folder %s does not seem to exist in the %s folder" % (run_folder, input_path)
            folders = [run_folder]
        
        logger2.info("Will process %s folders: %s" % (len(folders),folders))
        
        # Parse the supplied db of transferred flowcells, or a db in the default location if present
        transferred_db = os.path.normpath(os.path.expanduser(config["transfer_db"])) 
        assert os.path.exists(transferred_db), "Could not locate transferred_db (expected %s)" % transferred_db
        logger2.info("Transferred db is %s" % transferred_db)
        
        # Process each run folder
        for folder in folders:
            
            try:
                
                # Skip this folder if it has already been processed
                logger2.info("Processing %s" % folder)
                if _is_processed(folder,transferred_db) and not force:
                    logger2.info("%s has already been processed, skipping" % folder) 
                    continue
            
                # Locate the samplesheet and pasre the uppnex id if necessary
                if uppnexid is None:
                    local_samplesheet = samplesheet
                    if local_samplesheet is None: local_samplesheet = os.path.join(input_path,folder,config.get("samplesheet_name",DEFAULT_SS_NAME))
                    assert os.path.exists(local_samplesheet), "Could not find expected sample sheet %s" % local_samplesheet
                    local_uppnexid = _fetch_uppnexid(local_samplesheet, config.get("uppnexid_field",DEFAULT_UPPNEXID_FIELD))
                    assert local_uppnexid is not None and len(local_uppnexid) > 0, "Could not parse Uppnex ID for project from samplesheet %s" % local_samplesheet
                else:
                    local_uppnexid = uppnexid
                    
                logger2.info("Will deliver to inbox of project %s" % local_uppnexid)
                
                # Locate the fastq-files to be delivered
                pat = os.path.join(input_path,folder,config.get("fastq_path",DEFAULT_FQ_LOCATION),"*.fastq*")
                fq_files = glob.glob(pat)
                assert len(fq_files) > 0, "Could not locate fastq files for folder %s using pattern %s" % (folder,pat)
                
                logger2.info("Found %s fastq files to deliver: %s" % (len(fq_files),fq_files))
                if dryrun:
                    logger2.info("Remember that this is a dry-run. Nothing will be delivered and no directories will be created/changed")
                    
                # Create the destination directory if required
                dest_dir = os.path.normpath(os.path.join(config.get("project_root",DEFAULT_PROJECT_ROOT),local_uppnexid,"INBOX",folder,"fastq"))
                
                _update_processed(folder,transferred_db,dryrun)
                assert _create_destination(dest_dir, dryrun), "Could not create destination %s" % dest_dir
                assert _deliver_files(fq_files,dest_dir, dryrun), "Could not transfer files to destination %s" % dest_dir
                assert _verify_files(fq_files,dest_dir,dryrun), "Integrity of files in destination directory %s could not be verified. Please investigate" % dest_dir
                assert _set_permissions(dest_dir, dryrun), "Could not change permissions on destination %s" % dest_dir
                
                if email_handler is not None:
                    with email_handler.applicationbound():
                        with logbook.Processor(lambda record: record.extra.__setitem__('run', folder)):
                            logger2.info("The MiSeq sequence data for run %s was successfully delivered to the inbox of Uppnex project %s (%s)" % (folder,local_uppnexid,dest_dir))
                
            except AssertionError as e:
                logger2.error("Could not deliver data from folder %s. Reason: %s. Please fix problems and retry." % (folder,e))
                logger2.info("Rolling back changes to %s" % transferred_db)
                _update_processed(folder,transferred_db,dryrun,True)

def _update_processed(folder, transferred_db, dryrun, rollback=False):
    rows = _get_processed(transferred_db)
    present = False
    for row in rows:
        if row[0] == folder:
            if rollback:
                logger2.info("Removing entry for %s from %s" % (folder,transferred_db))
                rows.remove(row)
            else:
                logger2.info("Updating entry for %s in %s" % (folder,transferred_db))
                row[1] = time.strftime("%x-%X")
            present = True
            break
    if not present and not rollback:
        logger2.info("Adding entry for %s to %s" % (folder,transferred_db))
        rows.append([folder,time.strftime("%x-%X")])
        
    _put_processed(transferred_db, rows, dryrun)
    
def _get_processed(transferred_db, folder=None):
    rows = []
    with open(transferred_db,"r") as fh:
        for row in fh:
            data = row.split()
            if len(data) > 0 and (folder is None or data[0] == folder):
                rows.append(data)
    return rows
        
def _put_processed(transferred_db, rows, dryrun):
    if dryrun: return
    with open(transferred_db,"w") as fh:
        for row in rows:
            fh.write("%s\n" % " ".join(row))
    
def _is_processed(folder,transferred_db):
    rows = _get_processed(transferred_db,folder)
    return len(rows) > 0

def _fetch_uppnexid(samplesheet, uppnexid_field):
    uppnexid = None
    logger2.info("Parsing UppnexId from %s" % samplesheet)
    with open(samplesheet,"r") as fh:
        for line in fh:
            if not line.startswith("[Data]"): continue
            header = fh.next().split(',')
            index = header.index(uppnexid_field)
            for line in fh:
                values = line.split(',')
                if len(values) != len(header):
                    return uppnexid
                if values[index] is None or len(values[index]) == 0:
                    continue
                local_uppnexid = values[index]
                if uppnexid is not None and local_uppnexid != uppnexid:
                    logger2.error("Found multiple UppnexIds (%s,%s) in %s" % (uppnexid,local_uppnexid,samplesheet))
                    return None
                uppnexid = local_uppnexid
    return uppnexid
                
def _set_permissions(destination, dryrun):
    try:
        logger2.info("Setting permissions on %s" % destination)
        for root, dirs, files in os.walk(destination):
            if not dryrun: os.chmod(root, stat.S_IRWXU | stat.S_IRWXG)
            for file in files:
                if not dryrun: os.chmod(os.path.join(root,file), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
    except Exception as e:
        logger2.error("Encountered exception when setting permissions for %s: %s" % (destination,e))
        return False
    return True    
    
def _create_destination(destination, dryrun):
    try:
        logger2.info("Creating destination directory %s" % destination)
        if not dryrun: os.makedirs(destination,0770)
    except OSError as e:
        logger2.info("Could not create destination directory %s, probably because it already exists" % destination)
        pass
    return dryrun or os.path.exists(destination)
    
def _deliver_files(files,destination, dryrun):
    try:
        cl = ["rsync",
              "-cra"]
        cl.extend(files)
        cl.append(destination)
        cl = [str(i) for i in cl]
            
        logger2.info("Will deliver using command: %s" % cl)
        if not dryrun: subprocess.check_call(cl)
    except Exception as e:
        logger2.error("Failed when trying to deliver to %s: %s" % (destination,e))
        return False
    return True

def _verify_files(source_files, destination, dryrun):
    try:
        for source_file in source_files:
            filename = os.path.basename(source_file)
            dest_file = os.path.join(destination,filename)
            
            logger2.info("Verifying integrity of %s using md5" % dest_file)
            
            if not dryrun and not os.path.exists(dest_file):
                logger2.error("The file %s does not exist in destination directory %s" % (filename,destination))
                return False
            source_md5 = _file_md5(source_file)
            
            if not dryrun: dest_md5 = _file_md5(dest_file)
            if not dryrun and source_md5.hexdigest() != dest_md5.hexdigest():
                logger2.error("The md5 sums of %s is differs between source and destination" % filename)
                return False
    except Exception as e:
        logger2.error("Encountered exception when verifying file integrity: %s" % e)
        return False
    return True

def _file_md5(file):
    block_size = 2**20
    hash = md5()
    with open(file,"rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            hash.update(data)
    return hash

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-r", "--run-folder", dest="run_folder", default=None)
    parser.add_option("-d", "--transferred-db", dest="transferred_db", default=None)
    parser.add_option("-u", "--uppnexid", dest="uppnexid", default=None)
    parser.add_option("-s", "--samplesheet", dest="samplesheet", default=None)
    parser.add_option("-l", "--log-file", dest="logfile", default=None)
    parser.add_option("-e", "--email-notification", dest="email_notification", default=None)
    parser.add_option("-c", "--config-file", dest="config_file", default=None)
    parser.add_option("-f", "--force", dest="force", action="store_true", default=False)
    parser.add_option("-n", "--dry-run", dest="dryrun", action="store_true", default=False)
    options, args = parser.parse_args()
    
    input_path = None
    if len(args) == 1:
        input_path = args[0]
    else:
        print __doc__
        sys.exit()
    main(os.path.normpath(input_path), 
         options.transferred_db, options.run_folder, 
         options.uppnexid, options.samplesheet,
         options.logfile, options.email_notification,
         options.config_file, options.force,
         options.dryrun)

