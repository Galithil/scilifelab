"""
Test extensions
"""

import os
from cement.core import handler
from cement.utils import shell
from pmtools.core.analysis import AnalysisController
from test_default import PmTest

class PmShellTest(PmTest):
    def test_1_wait(self):
        """Test that submitted shell jobs are run sequentially"""
        # self.app  = self.make_app(argv=[], extensions=['pmtools.ext.ext_shell'])
        # self._run_app()
        # print self.app.cmd
        print "running first sleep"
        out = shell.exec_cmd(["sleep", "3"])
        print "finishing first sleep"
        print "running second sleep"
        shell.exec_cmd(["sleep", "3"])
        print "finishing second sleep"

class PmHsMetricsTest(PmTest):
    def test_1_hsmetrics(self):
        """Run hs metrics"""
        self.app = self.make_app(argv=['analysis', 'hs-metrics', '120829_SN0001_0001_AA001AAAXX', '-p', 'J.Doe_00_01', '-r', 'regionfile', '--force', '-n'], extensions=['pmtools.ext.ext_hs_metrics'])
        handler.register(AnalysisController)
        self._run_app()
        hsmetrics_str = "(DRY_RUN): java -jar $PICARD_HOME/CalculateHsMetrics.jar -I {}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_1-sort-dup.bam -TI regionfile -BI regionfile -O {}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_1-sort-dup.hs_metrics".format(self.app.config.get("analysis", "root"), self.app.config.get("analysis", "root"))
        self.eq(hsmetrics_str, str(self.app._output_data['stderr'].getvalue().split("\n")[0]))

    def test_2_hsmetrics_empty(self):
        """Run hs metrics when no files present"""
        self.app = self.make_app(argv=['analysis', 'hs-metrics', '120829_SN0001_0001_AA001AAAXX', '-p', 'J.Doe_00_02', '-r', 'regionfile', '--force', '-n'], extensions=['pmtools.ext.ext_hs_metrics'])
        handler.register(AnalysisController)
        self._run_app()
        ## Shouldn't produce any output 
        self.eq([''], self.app._output_data['stdout'].getvalue().split("\n"))

    def test_3_hsmetrics_drmaa(self):
        """Run hs metrics over drmaa"""
        self.app = self.make_app(argv=['analysis', 'hs-metrics', '120829_SN0001_0001_AA001AAAXX', '-p', 'J.Doe_00_01', '-r', 'regionfile', '--force',  '-A', 'jobaccount', '--drmaa', '-n'], extensions=['pmtools.ext.ext_hs_metrics', 'pmtools.ext.ext_distributed'])
        handler.register(AnalysisController)
        self._run_app()
        hsmetrics_str = "(DRY_RUN): java -jar -Xmx3g $PICARD_HOME/CalculateHsMetrics.jar INPUT={}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_1-sort-dup.bam TARGET_INTERVALS=regionfile BAIT_INTERVALS=regionfile OUTPUT={}/120829_SN0001_0001_AA001AAAXX/1_120829_AA001AAAXX_nophix_1-sort-dup.hs_metrics".format(self.app.config.get("analysis", "root"), self.app.config.get("analysis", "root"))
        if not os.getenv("DRMAA_LIBRARY_PATH"):
            self.eq('', str(self.app._output_data['stderr'].getvalue().split("\n")[0]))
        else:
            self.eq(hsmetrics_str, str(self.app._output_data['stderr'].getvalue().split("\n")[0]))
