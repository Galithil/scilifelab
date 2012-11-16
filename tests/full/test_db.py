import os
import csv
import yaml
import couchdb
from couchdb.design import ViewDefinition
import unittest
import time
import logbook
import socket

from classes import PmFullTest
from scilifelab.pm.ext.ext_qc import update_fn
from scilifelab.db.statusdb import SampleRunMetricsConnection, VIEWS, flowcell_run_metrics, sample_run_metrics, project_summary, ProjectSummaryConnection
from scilifelab.bcbio.qc import FlowcellRunMetricsParser, SampleRunMetricsParser
from scilifelab.pm.bcbio.utils import fc_id, fc_parts, fc_fullname

filedir = os.path.dirname(os.path.abspath(__file__))
dirs = {'production': os.path.join(filedir, "data", "production")}

LOG = logbook.Logger(__name__)

flowcells = ["120924_SN0002_0003_AC003CCCXX", "121015_SN0001_0002_BB002BBBXX"]
flowcell_dir = os.path.join(filedir, "data", "archive")
projects = ["J.Doe_00_01", "J.Doe_00_02", "J.Doe_00_03"]
project_dir = os.path.join(filedir, "data", "production")

## Try connecting to server
has_couchdb = True
try:
    server = couchdb.Server()
    dbstats = server.stats()
except socket.error as e:
    has_couchdb = False
    LOG.info("To run db tests setup a local couchdb server at http://localhost:5984")
    time.sleep(3)
    pass


def _save(db, obj, update_fn=None):
    """Save/update database object <obj> in database <dbname>. If
    <obj> already exists and <update_fn> is passed, update will
    only take place if object has been modified
    
    :param db: database
    :param obj: database object to save
    :param update_fn: function that operates on object and makes sure it doesn't already exist
    """
    if not update_fn:
        db.save(obj)
        LOG.info("Saving object {} with id {}".format(repr(obj), obj["_id"]))
    else:
        (new_obj, dbid) = update_fn(None,db, obj)
        if not new_obj is None:
            LOG.info("Saving object {} with id {}".format(repr(new_obj), new_obj["_id"]))
            db.save(new_obj)
        else:
            LOG.info("Object {} with id {} present and not in need of updating".format(repr(obj), dbid.id))

def _save_samples(flowcell):
    server = couchdb.Server()
    db = server["samples-test"]
    fcdir = flowcell
    (fc_date, fc_name) = fc_parts(flowcell)
    runinfo_csv = os.path.join(os.path.abspath(flowcell), "{}.csv".format(fc_id(flowcell)))
    try:
        with open(runinfo_csv) as fh:
            runinfo_reader = csv.reader(fh)
            runinfo = [x for x in runinfo_reader]
    except IOError as e:
        LOG.warn(str(e))
        raise e
    for sample in runinfo[1:]:
        d = dict(zip(runinfo[0], sample))
        sampledir = os.path.join(os.path.abspath(dirs["production"]), d['SampleProject'].replace("__", "."), d['SampleID'])
        if not os.path.exists(sampledir):
            LOG.warn("No such sample directory: {}".format(sampledir))
            continue
        sample_fcdir = os.path.join(sampledir, fc_fullname(flowcell))
        if not os.path.exists(sample_fcdir):
            LOG.warn("No such sample flowcell directory: {}".format(sample_fcdir))
            continue
        runinfo_yaml_file = os.path.join(sample_fcdir, "{}-bcbb-config.yaml".format(d['SampleID']))
        if not os.path.exists(runinfo_yaml_file):
            LOG.warn("No such yaml file for sample: {}".format(runinfo_yaml_file))
            raise IOError(2, "No such yaml file for sample: {}".format(runinfo_yaml_file), runinfo_yaml_file)
        with open(runinfo_yaml_file) as fh:
            runinfo_yaml = yaml.load(fh)
        if not runinfo_yaml['details'][0].get("multiplex", None):
            LOG.warn("No multiplex information for sample {}".format(d['SampleID']))
            continue
        sample_kw = dict(flowcell=fc_name, date=fc_date, lane=d['Lane'], barcode_name=d['SampleID'], sample_prj=d['SampleProject'].replace("__", "."), barcode_id=runinfo_yaml['details'][0]['multiplex'][0]['barcode_id'], sequence=runinfo_yaml['details'][0]['multiplex'][0]['sequence'])
        parser = SampleRunMetricsParser(sample_fcdir)
        obj = sample_run_metrics(**sample_kw)
        obj["picard_metrics"] = parser.read_picard_metrics(**sample_kw)
        obj["fastq_scr"] = parser.parse_fastq_screen(**sample_kw)
        obj["bc_metrics"] = parser.parse_bc_metrics(**sample_kw)
        obj["fastqc"] = parser.read_fastqc_metrics(**sample_kw)
        obj["project_sample_name"] = "test"
        _save(db, obj, update_fn)
        
def _save_flowcell(flowcell):
    server = couchdb.Server()
    db = server["flowcells-test"]
    fcdir = flowcell
    (fc_date, fc_name) = fc_parts(flowcell)
    fc_kw = dict(fc_date = fc_date, fc_name=fc_name)
    parser = FlowcellRunMetricsParser(fcdir)
    fcobj = flowcell_run_metrics(**fc_kw)
    fcobj["RunInfo"] = parser.parseRunInfo(**fc_kw)
    fcobj["illumina"] = parser.parse_illumina_metrics(fullRTA=False, **fc_kw)
    fcobj["bc_metrics"] = parser.parse_bc_metrics(**fc_kw)
    fcobj["illumina"].update({"Demultiplex_Stats" : parser.parse_demultiplex_stats_htm(**fc_kw)})
    fcobj["samplesheet_csv"] = parser.parse_samplesheet_csv(**fc_kw)
    _save(db, fcobj, update_fn)


def setUpModule():
    """Create test databases in local server"""
    if not has_couchdb:
        return
    server = couchdb.Server()
    ## Create databases
    for x in DATABASES:
        if not server.__contains__(x):
            LOG.info("Creating database {}".format(x))
            server.create(x)
    ## Create views for flowcells and samples
    for dbname in DATABASES:
        dblab = dbname.replace("-test", "")
        db = server[dbname]
        for k,v in VIEWS[dblab].items():
            for title, view in v.items():
                viewdef = ViewDefinition(k, title, view)
                viewdef.sync(db)
    
    ## Create project summary
    with open(os.path.join(filedir, "data", "config", "project_summary.yaml")) as fh:
        prj_sum = yaml.load(fh)
    db = server["samples-test"]
    p_con = ProjectSummaryConnection(dbname="projects-test", username="u", password="p")
    for p in prj_sum:
        prj = project_summary(**p)
        p_con.save(prj, viewname="project/project_id")

    #
    # def tearDownModule():
    #     db = couchdb.Server()
    #     for x in DATABASES:
    #         LOG.info("Deleting database {}".format(x))
    #         del db[x]
    
DATABASES = ["samples-test", "projects-test", "flowcells-test"]
@unittest.skipIf(not has_couchdb, "No couchdb server running in http://localhost:5984")
class TestCouchDB(unittest.TestCase):

    def test_dbcon(self):
        s_con = SampleRunMetricsConnection(dbname="samples-test", username="u", password="p")
        samples = [s_con.get_entry(x) for x in s_con.name_view.keys()]
        for s in samples:
            print s

    def test_srm_upload(self):
        """Test upload of Sample Run Metrics"""
        # View results at http://localhost:5984/_utils/database.html?samples-test
        for fc in flowcells:
            _save_samples(os.path.join(flowcell_dir, fc))

    def test_fc_upload(self):
        for fc in flowcells:
            _save_flowcell(os.path.join(flowcell_dir, fc))

@unittest.skipIf(not has_couchdb, "No couchdb server running in http://localhost:5984")
class TestQCUpload(PmFullTest):
    def test_qc_upload(self):
        self.app = self.make_app(argv = ['qc', 'upload-qc', flowcells[0], '--mtime',  '100'], extensions=['scilifelab.pm.ext.ext_qc'])
        self._run_app()

