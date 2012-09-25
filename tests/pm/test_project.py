"""
Test project subcontroller
"""
import os
import sys
import glob
from cement.core import handler
from cement.utils import shell, test
from test_default import PmTest, safe_makedir
from scilifelab.pm.core.project import ProjectController, ProjectRmController

filedir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
flowcell = "120829_SN0001_0001_AA001AAAXX"
runinfo = os.path.join(filedir, "data", "archive", flowcell, "run_info.yaml")

class ProjectTest(PmTest):

    COMPRESS_FILES = [
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
        '1_120829_AA001AAAXX_nophix_8_2.pileup',
        ]


    OUTPUT_FILES = []

    def setUp(self):
        super(ProjectTest, self).setUp()
        ## FIX ME: deliver data first - serves as test data
        self.app = self.make_app(argv = [])
        self.app.setup()
        self.fastq_dir = os.path.join(self.app.config.get("project", "root"), "j_doe_00_01", "data", flowcell)
        safe_makedir(self.fastq_dir)
        for f in self.COMPRESS_FILES:
            m = glob.glob("{}*".format(os.path.join(self.fastq_dir, f)))
            if not m:
                exit_code = shell.exec_cmd2(['touch', os.path.join(self.fastq_dir, f)])

    def test_1_project_transfer(self):
        self.app = self.make_app(argv = ['project', 'transfer'])
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
        if os.getenv("DRMAA_LIBRARY_PATH"):
            self.app = self.make_app(argv = ['project', 'compress', 'j_doe_00_01', '--pileup', '--drmaa', '-A', 'jobaccount', '-t', '00:01:00', '--partition', 'core', '-n'] , extensions=['scilifelab.pm.ext.ext_distributed'])
            handler.register(ProjectController)
            self._run_app()

    def test_4_decompress_distributed(self):
        """Test distributed compression of project data"""
        if os.getenv("DRMAA_LIBRARY_PATH"):
            self.app = self.make_app(argv = ['project', 'decompress', 'j_doe_00_01', '--pileup', '--drmaa', '-A', 'jobaccount', '-t', '00:01:00', '--partition', 'core', '-n'] , extensions=['scilifelab.pm.ext.ext_distributed'])
            handler.register(ProjectController)
            self._run_app()

    def test_5_compress_pbzip2_node(self):
        """Test distributed compression of project data with pbzip2"""
        if os.getenv("DRMAA_LIBRARY_PATH"):
            self.app = self.make_app(argv = ['project', 'compress', 'j_doe_00_01', '--pileup', '--drmaa', '-A', 'jobaccount', '-t', '00:01:00', '--partition', 'core', '--pbzip2', '-n'] , extensions=['scilifelab.pm.ext.ext_distributed'])
            handler.register(ProjectController)
            self._run_app()

    def test_5_decompress_pbzip2_node(self):
        """Test distributed decompression of project data with pbzip2"""
        if os.getenv("DRMAA_LIBRARY_PATH"):
            self.app = self.make_app(argv = ['project', 'decompress', 'j_doe_00_01', '--pileup', '--drmaa', '-A', 'jobaccount', '-t', '00:01:00', '--partition', 'core', '--pbzip2', '-n'] , extensions=['scilifelab.pm.ext.ext_distributed'])
            handler.register(ProjectController)
            self._run_app()

    @test.raises(Exception)
    def test_6_rm_analysis_1(self):
        """Test removal of non-existing intermediate analysis"""
        self.app = self.make_app(argv = ['project', 'rm', 'j_doe_00_04', 'analysisoe'])
        handler.register(ProjectController)
        handler.register(ProjectRmController)
        try:
            self._run_app()
        except:
            raise Exception

    def test_6_rm_analysis_1_dry(self):
        """Test dry removal of one intermediate analysis"""
        self.app = self.make_app(argv = ['project', 'rm', 'j_doe_00_04', 'analysis_1','-n'])
        handler.register(ProjectController)
        handler.register(ProjectRmController)
        self._run_app()

    @test.raises(Exception)
    def test_7_rm_analysis_1(self):
        """Test removal of one intermediate analysis"""
        self.app = self.make_app(argv = ['project', 'rm', 'j_doe_00_04', 'analysis_1'])
        handler.register(ProjectController)
        handler.register(ProjectRmController)
        self._run_app()
        try:
            os.listdir(os.path.join(filedir, "data", "projects", "j_doe_00_04", "intermediate", "analysis_1"))
        except:
            raise Exception
        
        
