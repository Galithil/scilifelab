"""
Test extensions
"""

import os
from cement.core import handler
from cement.utils import shell
from scilifelab.pm.core.production import ProductionController
from test_default import PmTest

class PmShellTest(PmTest):
    def test_1_wait(self):
        """Test that submitted shell jobs are run sequentially"""
        print "running first sleep"
        out = shell.exec_cmd(["sleep", "3"])
        print "finishing first sleep"
        print "running second sleep"
        shell.exec_cmd(["sleep", "3"])
        print "finishing second sleep"

class PmHsMetricsTest(PmTest):
    def test_1_hsmetrics(self):
        """Run hs metrics"""
        self.app = self.make_app(argv=['production', 'hs-metrics', 'J.Doe_00_01', '-f', '120829_SN0001_0001_AA001AAAXX', '--region_file', 'regionfile', '--force', '-n'], extensions=['scilifelab.pm.ext.ext_hs_metrics'])
        handler.register(ProductionController)
        self._run_app()
        hsmetrics_str = "(DRY_RUN): java -Xmx3g -jar {}/CalculateHsMetrics.jar INPUT={}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_10-sort-dup.bam TARGET_INTERVALS={}/regionfile BAIT_INTERVALS={}/regionfile OUTPUT={}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_10-sort-dup.hs_metrics VALIDATION_STRINGENCY=SILENT".format(os.getenv("PICARD_HOME"), self.app.config.get("production", "root"), os.path.abspath(os.curdir), os.path.abspath(os.curdir), self.app.config.get("production", "root"))
        self.eq(hsmetrics_str, str(self.app._output_data['stderr'].getvalue().split("\n")[0]))

    def test_2_hsmetrics_empty(self):
        """Run hs metrics when no files present"""
        self.app = self.make_app(argv=['production', 'hs-metrics', 'J.Doe_00_02',  '-f', '120829_SN0001_0001_AA001AAAXX','--region_file', 'regionfile', '--force', '-n'], extensions=['scilifelab.pm.ext.ext_hs_metrics'])
        handler.register(ProductionController)
        self._run_app()
        ## Shouldn't produce any output 
        self.eq([''], self.app._output_data['stdout'].getvalue().split("\n"))

    def test_3_hsmetrics_drmaa(self):
        """Run hs metrics over drmaa"""
        self.app = self.make_app(argv=['production', 'hs-metrics', 'J.Doe_00_01',  '-f', '120829_SN0001_0001_AA001AAAXX', '--region_file', 'regionfile', '--force',  '-A', 'jobaccount', '--drmaa', '-n'], extensions=['scilifelab.pm.ext.ext_hs_metrics', 'scilifelab.pm.ext.ext_distributed'])
        handler.register(ProductionController)
        self._run_app()
        hsmetrics_str = "(DRY_RUN): java -Xmx3g -jar {}/CalculateHsMetrics.jar INPUT={}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_10-sort-dup.bam TARGET_INTERVALS={}/regionfile BAIT_INTERVALS={}/regionfile OUTPUT={}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_10-sort-dup.hs_metrics VALIDATION_STRINGENCY=SILENT".format(os.getenv("PICARD_HOME"), self.app.config.get("production", "root"), os.path.abspath(os.curdir), os.path.abspath(os.curdir), self.app.config.get("production", "root"))
        self.eq(hsmetrics_str, str(self.app._output_data['stderr'].getvalue().split("\n")[0]))
