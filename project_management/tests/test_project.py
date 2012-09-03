"""
Test project subcontroller
"""
import os
import sys
import glob
from cement.core import handler
from cement.utils import shell
from test_default import PmTest, safe_makedir
from pmtools.core.project import ProjectController
# from pmtools.lib.runinfo import get_runinfo

flowcell = "120829_SN0001_0001_AA001AAAXX"
runinfo = os.path.join(os.path.curdir, "data", "archive", flowcell, "run_info.yaml")

class ProjectTest(PmTest):

    FASTQ_COMPRESS_FILES = [
        '1_120829_AA001AAAXX_nophix_10_1_fastq.txt',
        '1_120829_AA001AAAXX_nophix_10_2_fastq.txt',
        '1_120829_AA001AAAXX_nophix_12_1_fastq.txt',
        '1_120829_AA001AAAXX_nophix_12_2_fastq.txt',
        '1_120829_AA001AAAXX_nophix_1_1.fastq',
        '1_120829_AA001AAAXX_nophix_1_2.fastq',
        '1_120829_AA001AAAXX_nophix_2_1.fastq',
        '1_120829_AA001AAAXX_nophix_2_2.fastq',
        '1_120829_AA001AAAXX_nophix_3_1.fq',
        '1_120829_AA001AAAXX_nophix_3_2.fq',
        '1_120829_AA001AAAXX_nophix_4_1_fastq.txt',
        '1_120829_AA001AAAXX_nophix_4_2_fastq.txt',
        '1_120829_AA001AAAXX_nophix_8_1_fastq.txt',
        '1_120829_AA001AAAXX_nophix_8_2_fastq.txt',
        ]


    OUTPUT_FILES = []

    def setUp(self):
        super(ProjectTest, self).setUp()
        ## FIX ME: deliver data first - serves as test data
        self.app = self.make_app(argv = [])
        self.app.setup()
        self.fastq_dir = os.path.join(self.app.config.get("project", "root"), "j_doe_00_01", "data", flowcell)
        safe_makedir(self.fastq_dir)
        ## FIX ME: make safe_touch
        for f in self.FASTQ_COMPRESS_FILES:
            m = glob.glob("{}*".format(os.path.join(self.fastq_dir, f)))
            if not m:
                exit_code = shell.exec_cmd2(['touch', os.path.join(self.fastq_dir, f)])

    def test_1_project_deliver(self):
        self.app = self.make_app(argv = ['project', 'deliver'])
        handler.register(ProjectController)
        self._run_app()
        
    def test_2_project_data_delivery(self):
        pass

    def test_3_compress(self):
        """Test compression of project data"""
        self.app = self.make_app(argv = ['project', 'compress', 'j_doe_00_01', '--fastq', '--force'])
        handler.register(ProjectController)
        self._run_app()

    def test_3_decompress(self):
        """Test decompression of project data"""
        self.app = self.make_app(argv = ['project', 'decompress', 'j_doe_00_01', '--fastq', '--force'])
        handler.register(ProjectController)
        self._run_app()

    def test_4_compress_distributed(self):
        """Test distributed compression of project data"""
        self.app = self.make_app(argv = ['project', 'compress', 'j_doe_00_01', '--fastq', '--drmaa', '-A', 'a2010002', '-t', '00:01:00', '--partition', 'devel'] , extensions=['pmtools.ext.ext_distributed'])
        handler.register(ProjectController)
        self._run_app()

    def test_4_decompress_distributed(self):
        """Test distributed compression of project data"""
        self.app = self.make_app(argv = ['project', 'decompress', 'j_doe_00_01', '--fastq', '--drmaa', '-A', 'a2010002', '-t', '00:01:00', '--partition', 'devel'] , extensions=['pmtools.ext.ext_distributed'])
        handler.register(ProjectController)
        self._run_app()

    def test_5_compress_pbzip2_node(self):
        """Test distributed compression of project data"""
        self.app = self.make_app(argv = ['project', 'compress', 'j_doe_00_01', '--fastq', '--drmaa', '-A', 'a2010002', '-t', '00:01:00', '--partition', 'devel', '--pbzip2'] , extensions=['pmtools.ext.ext_distributed'])
        handler.register(ProjectController)
        self._run_app()
