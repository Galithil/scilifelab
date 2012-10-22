"""Distributed Extension"""
import re
import os
import sys

from cement.core import backend, handler, hook

from scilifelab.pm.core import command

LOG = backend.minimal_logger(__name__)

class DistributedCommandHandler(command.CommandHandler):
    """ 
    This class is an implementation of the :ref:`ICommand
    <scilifelab.pm.core.command>` interface.
    """    

    class Meta:
        """Handler meta-data"""
        
        interface = command.ICommand
        """The interface that this class implements."""

        label = 'distributed'
        """The string identifier of this handler."""

        n_submitted_jobs = 0
        """The number of submitted jobs"""

        jobid = None
        """The submitted jobid"""

        platform_args = None
        """Platform specific arguments"""

    def command(self, cmd_args, capture=True, ignore_error=False, cwd=None, **kw):
        ## Is there no easier way to get at --drmaa and --sbatch?!?
        if '--drmaa' in self.app._meta.argv:
            self.drmaa(cmd_args, capture, ignore_error, cwd, **kw)
        else:
            pass

    def drmaa(self, cmd_args, capture=True, ignore_error=False, cwd=None, **kw):
        if self.app.pargs.partition == "node" and self.app.pargs.max_node_jobs < self._meta.n_submitted_jobs:
            self.app.log.info("number of submitted jobs larger than maximum number of allowed node jobs; not submitting job")
            return
        self._meta.n_submitted_jobs = self._meta.n_submitted_jobs + 1
        if not self.app.pargs.job_account:
            self.app.log.warn("no job account provided; cannot proceed with drmaa command")
            return
        command = " ".join(cmd_args)
        def runpipe():
            if not os.getenv("DRMAA_LIBRARY_PATH"):
                self.app.log.info("No environment variable DRMAA_LIBRARY_PATH: will not attempt to submit job via DRMAA")
                return
            else:
                import drmaa
            s = drmaa.Session()
            s.initialize()

            jt = s.createJobTemplate()
            jt.remoteCommand = cmd_args[0]
            jt.args = cmd_args[1:]
            if kw['platform_args']:
                platform_args = kw['platform_args']
            else:
                platform_args = []
            if not "-J" or "--job-name" in platform_args:
                jt.jobName = self.app.pargs.jobname
            if not "-t" or "--time"  in platform_args:
                platform_args.extend(["-t", self.app.pargs.time])
            if not "-A" or "--job_account" in platform_args:
                platform_args.extend(["-A", self.app.pargs.job_account])
            if not "-p" or "--partition"  in platform_args:
                platform_args.extend(["-p", self.app.pargs.partition])
            if "-o" in platform_args:
                #jt.outputPath = ":"+platform_args[platform_args.index("-o")+1]
                del platform_args[platform_args.index("-o")+1]
                del platform_args[platform_args.index("-o")]
            if "-D" in platform_args:
                #jt.workingDirectory = platform_args[platform_args.index("-D")+1]
                del platform_args[platform_args.index("-D")+1]
                del platform_args[platform_args.index("-D")]
            idel = []
            for i in range(len(platform_args)):
                if platform_args[i].startswith("--mail"):
                    idel.append(i)
            for i in sorted(idel, reverse=True):
                del platform_args [i]
            jt.nativeSpecification = " ".join(platform_args)
            self._meta.jobid = s.runJob(jt)
            self.app.log.info('Your job has been submitted with id ' + self._meta.jobid)
            s.deleteJobTemplate(jt)
            s.exit()
            
        return self.dry(command, runpipe)

def add_drmaa_option(app):
    """
    Adds the '--drmaa' argument to the argument object.
    
    :param app: The application object.
    
    """
    app.args.add_argument('--drmaa', dest='cmd_handler', 
                          action='store_const', help='toggle drmaa command handler', const='drmaa')

def add_shared_distributed_options(app):
    """
    Adds shared distributed arguments to the argument object.
    
    :param app: The application object.
    
    """
    app.args.add_argument('-A', '--job_account', type=str,
                          action='store', help='job account', default=None)
    app.args.add_argument('--jobname', type=str,
                          action='store', help='job name', default="pm_distributed")
    app.args.add_argument('-t', '--time',
                          action='store', help='time limit', default="00:10:00")
    app.args.add_argument('--partition', type=str,
                          action='store', help='partition', default="core")
    app.args.add_argument('--max_node_jobs', type=int, default=10,
                          action='store', help='maximum number of node jobs (default 10)')

def set_distributed_handler(app):
    """
    Overrides the configured command handler if ``--drmaa`` is passed at the
    command line.
    
    :param app: The application object.
    
    """
    if '--drmaa' in app._meta.argv:
        app._meta.cmd_handler = 'distributed'
        app._setup_cmd_handler()

def load():
    """Called by the framework when the extension is 'loaded'."""
    hook.register('post_setup', add_drmaa_option)
    hook.register('post_setup', add_shared_distributed_options)
    hook.register('pre_run', set_distributed_handler)
    handler.register(DistributedCommandHandler)
