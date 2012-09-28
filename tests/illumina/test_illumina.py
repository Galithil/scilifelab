
import unittest
import shutil
import tempfile
import os
import random
import string
import bcbio.utils as utils
import tests.generate_test_data as td
from scilifelab.illumina import IlluminaRun


class TestIllumina(unittest.TestCase):
    
    def setUp(self): 
        self.rootdir = tempfile.mkdtemp(prefix="test_illumina_")
        
    def tearDown(self):
        shutil.rmtree(self.rootdir)
    
    def test__get_flowcell(self):
        """Get flowcell from analysis directory
        """
        
        # Create some folders
        fc_dirs = []
        for i in range(3):
            fc_dirs.append(tempfile.mkdtemp(suffix="{}_fc_dir".format(i), dir=self.rootdir))
        
        # Assert nothing is returned for non-existing flowcell
        self.assertListEqual(IlluminaRun._get_flowcell(self.rootdir,'flowcell_id'),
                             [],
                             "Nothing should be returned for a non-existing flowcell id")
        # Assert nothing is returned for None or empty flowcell id
        self.assertListEqual(IlluminaRun._get_flowcell(self.rootdir,''),
                             [],
                             "Nothing should be returned for a 0-length flowcell id")
        self.assertListEqual(IlluminaRun._get_flowcell(self.rootdir,None),
                             [],
                             "Nothing should be returned for an empty flowcell id")
        
        # Assert that the correct folders are returned for exact matches
        for fc_dir in fc_dirs:
            self.assertListEqual([fc_dir],
                                 IlluminaRun._get_flowcell(self.rootdir,os.path.basename(fc_dir)),
                                 "Did not return the correct folder for exact match")
        
        # Assert that a partial match is resolved to the correct folder
        self.assertListEqual([fc_dirs[-1]],
                             IlluminaRun._get_flowcell(self.rootdir,"{}_fc_dir".format(str(len(fc_dirs)-1))),
                             "Did not return the correct folder for partial match")
        
        # Assert that an ambiguous match returns the matching folders
        self.assertListEqual(sorted(fc_dirs),
                             sorted(IlluminaRun._get_flowcell(self.rootdir,"_fc_dir")),
                             "Did not return the correct folders for ambiguous matches")
        
        # Assert that the correct folder is returned for an exact match that matches ambiguously when allowing wildcards
        ambig_dir = os.path.join(self.rootdir,"_fc_dir")
        utils.safe_makedir(ambig_dir)
        self.assertListEqual([ambig_dir],
                             sorted(IlluminaRun._get_flowcell(self.rootdir,os.path.basename(ambig_dir))),
                             "Did not return the correct folder for specific non-wildcard match")
    
    def test__get_samplesheet(self):
        """Locate the samplesheet in a folder
        """
        # Create a few random files and folders and assert that they are not returned
        suffixes = [".csv","",""]
        for n in range(3):
            os.mkdir(os.path.join(self.rootdir,''.join(random.choice(string.ascii_uppercase) for x in range(5))))
            fh, _ = tempfile.mkstemp(dir=self.rootdir, suffix=suffixes[n])
            os.close(fh)
            
        self.assertIsNone(IlluminaRun._get_samplesheet(self.rootdir),
                          "Getting non-existing samplesheet did not return None")
        
        # Create a SampleSheet.csv and a [FCID].csv file and assert that they are
        # returned with a preference for the [FCID].csv file
        fcid = td.generate_fc_barcode()
        fcdir = os.path.join(self.rootdir,td.generate_run_id(fc_barcode=fcid))
        os.mkdir(fcdir)
        
        ss = [os.path.join(fcdir,"SampleSheet.csv"),
              os.path.join(fcdir,"{}.csv".format(fcid))]
        for s in ss:
            utils.touch_file(s)
            self.assertEqual(s,IlluminaRun._get_samplesheet(fcdir),
                             "Did not get existing {}".format(os.path.basename(s)))
    
