import shutil
import os
import logbook

from ..pm.test_default import PmTest

from cement.core import handler
from scilifelab.pm.core.production import ProductionController

LOG = logbook.Logger(__name__)


JDOE01 = os.path.join(os.curdir, "data", "production", "J.Doe_00_01")
JDOE04 = os.path.join(os.curdir, "data", "production", "J.Doe_00_04")

class ProductionTest(PmTest):
    def setUp(self):
        LOG.info("Copy tree {} to {}".format(JDOE01, JDOE04))
        if not os.path.exists(JDOE04):
            shutil.copytree(JDOE01, JDOE04)

    # def tearDown(self):
    #     LOG.info("Removing directory tree {}".format(JDOE04))
    #     shutil.rmtree(JDOE04)

    def test_production_setup(self):
        self.app = self.make_app(argv = ['production', 'run', 'J.Doe_00_04', '--debug', '--force', '--only_setup'])
        handler.register(ProductionController)
        self._run_app()

    def test_production(self):
        self.app = self.make_app(argv = ['production', 'run', 'J.Doe_00_04', '--debug', '--force', '--halo'])
        handler.register(ProductionController)
        self._run_app()
