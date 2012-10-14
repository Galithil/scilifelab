import os
import subprocess
import unittest
import collections

class ScilifeTest(unittest.TestCase):
    def setUp(self):
        self._install_bcbio_test_files(os.path.join(os.path.dirname(__file__), "data", "production"))

    def _install_bcbio_test_files(data_dir):
        """Download required sequence and reference files.
        """
        
        DlInfo = collections.namedtuple("DlInfo", "fname dirname version")
        download_data = [DlInfo("110106_FC70BUKAAXX.tar.gz", None, None),
                         DlInfo("genomes_automated_test.tar.gz", "genomes", 6),
                         DlInfo("110907_ERP000591.tar.gz", None, None),
                         DlInfo("100326_FC6107FAAXX.tar.gz", None, 2)]
        for dl in download_data:
            url = "http://chapmanb.s3.amazonaws.com/{fname}".format(fname=dl.fname)
            dirname = os.path.join(data_dir, os.pardir,
                                   dl.fname.replace(".tar.gz", "") if dl.dirname is None
                                   else dl.dirname)
            if os.path.exists(dirname) and dl.version is not None:
                version_file = os.path.join(dirname, "VERSION")
                is_old = True
                if os.path.exists(version_file):
                    with open(version_file) as in_handle:
                        version = int(in_handle.read())
                    is_old = version < dl.version
                if is_old:
                    shutil.rmtree(dirname)
            if not os.path.exists(dirname):
                self._download_to_dir(url, dirname)

    def _download_to_dir(self, url, dirname):
        print dirname
        cl = ["wget", url]
        subprocess.check_call(cl)
        cl = ["tar", "-xzvpf", os.path.basename(url)]
        subprocess.check_call(cl)
        os.rename(os.path.basename(dirname), dirname)
        os.remove(os.path.basename(url))
