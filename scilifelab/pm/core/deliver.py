"""
Pm deliver module

Perform data delivery.

Commands:

         sample_status
         project_status
"""

import os
import shutil

from cement.core import controller
from scilifelab.pm.core.controller import AbstractBaseController
from scilifelab.report import sequencing_success
from scilifelab.report.rl import *
from scilifelab.db.statusdb import *

## Main delivery controller
class DeliveryController(AbstractBaseController):
    """
    Functionality for deliveries
    """
    class Meta:
        label = 'deliver'
        description = 'Deliver data'
        arguments = [
            ]

    @controller.expose(hide=True)
    def default(self):
        self._not_implemented()
        #print self._help_text
    
## Main delivery controller
class DeliveryReportController(AbstractBaseController):
    """
    Functionality for deliveries
    """
    class Meta:
        label = 'report'
        description = 'Make delivery reports'
        arguments = [
            (['project_id'], dict(help="project id", default="")),
            (['flowcell_id'], dict(help="flowcell id", default="", nargs="?")),
            (['-u', '--uppmax_id'], dict(help="Manually insert Uppnex project ID into the report.", default=None, action="store", type=str)),
            (['-o', '--ordered_million_reads'], dict(help="Manually insert the ordered number of read pairs (in millions)", default=None, action="store", type=str)),
            (['-r', '--customer-reference'], dict(help="Manually insert customer reference (the customer's name for the project) into reports", default=None, action="store", type=str)),
            ]

    @controller.expose(hide=True)
    def default(self):
        print self._help_text

    @controller.expose(help="Make sample status note")
    def sample_status(self):
        ## Cutoffs
        cutoffs = {
            "phix_err_cutoff" : 2.0,
            }

        ## parameters
        parameters = {
            "project_name" : None,
            "customer_reference": None,
            "uppnex_project_id" : None,
            "ordered_amount" : None,
            "start_date" : None,
            "FC_id" : None,
            "scilifelab_name" : None,
            "customer_name" : None,
            "rounded_read_count" : None,
            "phix_error_rate" : None,
            "avg_quality_score" : None,
            "success" : None,
            }

        ## key mapping from sample_run_metrics to parameter keys
        srm_to_parameter = {"project_name":"sample_prj", "FC_id":"flowcell", 
                            "scilifelab_name":"barcode_name", "start_date":"date", "rounded_read_count":"bc_count"}
        ## mapping project_summary to parameter keys
        ps_to_parameter = {"customer_reference":"Customer_reference", "uppnex_project_id":"Uppnex_id", "ordered_amount": "Min_M_reads_per_sample_ordered"}

        ## Data dicts
        error_rates = {}
        qvs = {}

        ## Connect and run
        s_con = SampleRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        fc_con = FlowcellRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        p_con = ProjectQCSummaryConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        paragraphs = sample_note_paragraphs()
        headers = sample_note_headers()
        samples = s_con.get_samples(self.pargs.flowcell_id, self.pargs.project_id)
        project = p_con.get_entry(self.pargs.project_id)
        for s in samples:
            s_param = parameters
            s_param.update({key:s[srm_to_parameter[key]] for key in srm_to_parameter.keys()})
            fc = "{}_{}".format(s["date"], s["flowcell"])
            s_param["phix_error_rate"] = fc_con.get_phix_error_rate(str(fc), s["lane"])
            s_param['avg_quality_score'] = s_con.calc_avg_qv(s["name"])
            s_param['rounded_read_count'] = round(float(s_param['rounded_read_count'])/1e6,1) if s_param['rounded_read_count'] else None
            s_param['success'] = sequencing_success(s_param, cutoffs)
            ## Set success of run
            if project:
                s_param.update({key:project[ps_to_parameter[key]] for key in ps_to_parameter.keys() })
            s_param.update({k:"N/A" for k in s_param.keys() if s_param[k] is None})
            make_note("{}.pdf".format(s["barcode_name"]), headers, paragraphs, **s_param)

    @controller.expose(help="Make project status note")
    def project_status(self):
        ## parameters
        parameters = {
            "project_name" : None,
            "customer_reference": None,
            "uppnex_project_id" : None,
            "finished":None,
            }
        ## key mapping from sample_run_metrics to parameter keys
        srm_to_parameter = {"project_name":"sample_prj"}
        ## mapping project_summary to parameter keys
        ps_to_parameter = {"customer_reference":"customer_reference", "uppnex_project_id":"uppnex_id", "scilife_name":"scilife_name", "customer_name":"customer_name", "project_name":"project_id"}
        ## mapping project sample to table
        srm_to_table = {'BarcodeSeq':'sequence'}
        table_keys = ['ScilifeID', 'CustomerID', 'BarcodeSeq', 'MSequenced', 'MOrdered', 'Status']
        prjs_to_table = {'ScilifeID':'scilife_name', 'CustomerID':'customer_name', 'MSequenced':'m_reads_sequenced', 'MOrdered':'min_m_reads_per_sample_ordered', 'Status':'status'}
        
        ## Connect and run
        s_con = SampleRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        fc_con = FlowcellRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        p_con = ProjectSummaryConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        paragraphs = project_note_paragraphs()
        headers = project_note_headers()
        param = parameters
        project = p_con.get_entry(self.pargs.project_id)
        ## Start collecting the data
        sample_table = []
        sample_table.append(['ScilifeID', 'CustomerID', 'BarcodeSeq', 'MSequenced', 'MOrdered', 'Status'])
        if project:
            sample_list = project['samples']
            param.update({key:project.get(ps_to_parameter[key], None) for key in ps_to_parameter.keys()})
            sample_map = p_con.map_sample_run_names(self.pargs.project_id, self.pargs.flowcell_id)
            for k,v in sample_map.items():
                project_sample = sample_list[v['project_sample']]
                vals = {x:project_sample.get(prjs_to_table[x], None) for x in prjs_to_table.keys()}
                vals['BarcodeSeq'] = s_con.get_entry(k, "sequence")
                vals.update({k:"N/A" for k in vals.keys() if vals[k] is None})
                sample_table.append([vals[k] for k in table_keys])
            paragraphs["Samples"]["tpl"] = make_sample_table(sample_table)
            make_note("{}.pdf".format(self.pargs.project_id), headers, paragraphs, **param)

    
