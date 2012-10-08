"""Pm deliver module"""
import os
import re
import shutil
import itertools

from cement.core import controller
from scilifelab.pm.core.controller import AbstractBaseController
from scilifelab.report import sequencing_success, set_status
from scilifelab.report.rl import *
from scilifelab.db.statusdb import *

## QC data cutoff values
qc_cutoff = {
    'rnaseq':{'PCT_PF_READS_ALIGNED':70,'PERCENT_DUPLICATION':30},
    'reseq':{'PCT_PF_READS_ALIGNED':70,'PERCENT_DUPLICATION':30},
    'seqcap':{'PCT_PF_READS_ALIGNED':70,'PERCENT_ON_TARGET':60, 'PCT_TARGET_BASES_10X':90, 'PERCENT_DUPLICATION':30},
    'customcap':{'PCT_PF_READS_ALIGNED':70, 'PERCENT_DUPLICATION':30},
    'finished':{},
    }
## Mapping from genomics project list application names
application_map = {'RNA-seq (Total RNA)':'rnaseq','Resequencing':'reseq', 'Exome capture':'seqcap', 'Custom':'customcap', 'Finished library':'finished' }

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

## Main delivery controller
class DeliveryReportController(AbstractBaseController):
    """
    Functionality for deliveries
    """
    class Meta:
        label = 'report'
        description = 'Make delivery reports and assess qc'
        arguments = [
            (['project_id'], dict(help="Project id. Standard format is 'J.Doe_00_00'", default=None, nargs="?")),
            (['flowcell_id'], dict(help="Flowcell id, formatted as AA000AAXX (i.e. without date, machine name, and run number).", default=None, nargs="?")),
            (['-u', '--uppnex_id'], dict(help="Manually insert Uppnex project ID into the report.", default=None, action="store", type=str)),
            (['-o', '--ordered_million_reads'], dict(help="Manually insert the ordered number of read pairs (in millions)", default=None, action="store", type=str)),
            (['-r', '--customer_reference'], dict(help="Manually insert customer reference (the customer's name for the project) into reports", default=None, action="store", type=str)),
            (['-q', '--qcinfo'], dict(help="Write qcinfo to console", default=False, action="store_true")),
            (['--check_consistency'], dict(help="Check consistency of project sample name mapping to sample run metrics names", default=False, action="store_true")),
            (['--use_ps_map'], dict(help="Use project summary mapping in cases where no sample_run_metrics is available", default=True, action="store_false")),
            (['--use_bc_map'], dict(help="Use sample run metrics barcode mapping in cases where no sample_run_metrics is available", default=False, action="store_true")),
            (['--application'], dict(help="Set application for qc evaluation. One of '{}'".format(",".join(qc_cutoff.keys())), action="store", type=str, default=None))
            ]

    def _process_args(self):
        pass

    @controller.expose(hide=True)
    def default(self):
        print self._help_text

    @controller.expose(help="Print summary QC data for a flowcell/project for application QC control")
    def qc(self):
        if not self._check_pargs(["project_id"]):
            return
        header = ["project","sample","lane","flowcell", "date", "application", "TOTAL_READS",
                  "MEAN_INSERT_SIZE","GENOME_SIZE","FOLD_ENRICHMENT", "PCT_USABLE_BASES_ON_TARGET",
                  "PERCENT_ON_TARGET", "PERCENT_DUPLICATION", "PCT_TARGET_BASES_10X", "PCT_PF_READS_ALIGNED", "status"]

        s_con = SampleRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        qc_data = s_con.get_qc_data(self.pargs.project_id, self.pargs.flowcell_id)
        def assess_qc(x):
            status = "PASS"
            app_label = application_map[x["application"]] if x["application"] else self.pargs.application 
            if app_label:
                for k in qc_cutoff[app_label].keys():
                    self.log.debug("assessing qc metric {}".format(k))
                    if k == "PERCENT_DUPLICATION":
                        if float(x[k]) > qc_cutoff[app_label][k]: 
                            status = "FAIL"
                    else:
                        if float(x[k]) < qc_cutoff[app_label][k]:
                            status = "FAIL"
            return [x["project"], x["sample"],x["lane"],x["flowcell"], x["date"], x["application"], x["TOTAL_READS"],
                    "{:.1f}".format(float(x["MEAN_INSERT_SIZE"])),x["GENOME_SIZE"],"{:.1f}".format(float(x["FOLD_ENRICHMENT"])), "{:.1f}".format(float(x["PCT_USABLE_BASES_ON_TARGET"])),
                    "{:.1f}".format(float(x["PERCENT_ON_TARGET"])),"{:.1f}".format(float(x["PERCENT_DUPLICATION"])),"{:.1f}".format(float(x["PCT_TARGET_BASES_10X"])), "{:.1f}".format(float(x["PCT_PF_READS_ALIGNED"])), status]
        self.app._output_data["stdout"].write("\t".join(header) + "\n")
        for k,v in sorted(qc_data.iteritems()):
            y = [str(x) for x in assess_qc(v)]
            self.app._output_data["stdout"].write("\t".join(y) + "\n")

    @controller.expose(help="Make sample status note")
    def sample_status(self):
        if not self._check_pargs(["project_id", "flowcell_id"]):
            return
        ## Cutoffs
        cutoffs = {
            "phix_err_cutoff" : 2.0,
            }

        ## parameters
        parameters = {
            "project_name" : None,
            "start_date" : None,
            "FC_id" : None,
            "scilifelab_name" : None,
            "rounded_read_count" : None,
            "phix_error_rate" : None,
            "avg_quality_score" : None,
            "success" : None,
            }
        ## key mapping from sample_run_metrics to parameter keys
        srm_to_parameter = {"project_name":"sample_prj", "FC_id":"flowcell", 
                            "scilifelab_name":"barcode_name", "start_date":"date", "rounded_read_count":"bc_count"}

        self.log.debug("got parameters {}".format(parameters))
        ## Write qcinfo if needed
        if self.pargs.qcinfo:
            self.app._output_data["stdout"].write("*** Quality stats ***\n")
            self.app._output_data["stdout"].write("Scilifelab ID\tPhiXError\tAvgQV\n")

        ## Connect and run
        s_con = SampleRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        fc_con = FlowcellRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        p_con = ProjectSummaryConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        paragraphs = sample_note_paragraphs()
        headers = sample_note_headers()
        project = p_con.get_entry(self.pargs.project_id)

        if not project:
            self.log.warn("No such project '{}'".format(self.pargs.project_id))
            return
        samples = p_con.map_srm_to_name(self.pargs.project_id, include_all=False, fc_id=self.pargs.flowcell_id, use_ps_map=self.pargs.use_ps_map, use_bc_map=self.pargs.use_bc_map, check_consistency=self.pargs.check_consistency)
        for k,v  in samples.items():
            s_param = {}
            self.log.debug("working on sample '{}', id '{}'".format(k, v["id"]))
            s_param.update(parameters)
            if not v['id'] is None:
                if not s_con.name_fc_view[k].value == self.pargs.flowcell_id:
                    self.log.debug("skipping sample '{}' since it isn't run on flowcell {}".format(k, self.pargs.flowcell_id))
                    continue
            else:
                if re.search("NOSRM", k):
                    self.log.warn("No sample run metrics information for project sample '{}'".format(k.strip("NOSRM_")))
                    continue
            s = s_con.get_entry(k)
            s_param.update({key:s[srm_to_parameter[key]] for key in srm_to_parameter.keys()})
            fc = "{}_{}".format(s["date"], s["flowcell"])
            s_param["phix_error_rate"] = fc_con.get_phix_error_rate(str(fc), s["lane"])
            s_param['avg_quality_score'] = s_con.calc_avg_qv(s["name"])
            if self.pargs.qcinfo:
                self.app._output_data["stdout"].write("{}\t{}\t{}\n".format(s["barcode_name"], s_param["phix_error_rate"], s_param["avg_quality_score"]))
            s_param['rounded_read_count'] = round(float(s_param['rounded_read_count'])/1e6,1) if s_param['rounded_read_count'] else None
            s_param['ordered_amount'] = s_param.get('ordered_amount', p_con.get_ordered_amount(self.pargs.project_id))
            s_param['customer_reference'] = s_param.get('customer_reference', project.get('customer_reference'))
            s_param['uppnex_project_id'] = s_param.get('uppnex_project_id', project.get('uppnex_id'))
            if self.pargs.ordered_million_reads:
                s_param["ordered_amount"] = self.pargs.ordered_million_reads
            if self.pargs.uppnex_id:
                s_param["uppnex_project_id"] = self.pargs.uppnex_id
            if self.pargs.customer_reference:
                s_param["customer_reference"] = self.pargs.customer_reference
            s_param['customer_name'] = project['samples'].get(v["sample"], {}).get("customer_name", None)
            s_param['success'] = sequencing_success(s_param, cutoffs)
            s_param.update({k:"N/A" for k in s_param.keys() if s_param[k] is None})
            make_note("{}_{}_{}.pdf".format(s["barcode_name"], s["date"], s["flowcell"]), headers, paragraphs, **s_param)

    @controller.expose(help="Make project status note")
    def project_status(self):
        if not self._check_pargs(["project_id"]):
            return
        ## parameters
        parameters = {
            "project_name" : self.pargs.project_id,
            "finished" : "Not finished, or cannot yet assess if finished.",
            }
        ## mapping project_summary to parameter keys
        ps_to_parameter = {"scilife_name":"scilife_name", "customer_name":"customer_name", "project_name":"project_id"}
        ## mapping project sample to table
        table_keys = ['ScilifeID', 'CustomerID', 'BarcodeSeq', 'MSequenced', 'MOrdered', 'Status']
        prjs_to_table = {'ScilifeID':'scilife_name', 'CustomerID':'customer_name', 'MSequenced':'m_reads_sequenced'}#, 'MOrdered':'min_m_reads_per_sample_ordered', 'Status':'status'}
        
        ## Connect and run
        s_con = SampleRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        fc_con = FlowcellRunMetricsConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        p_con = ProjectSummaryConnection(username=self.pargs.user, password=self.pargs.password, url=self.pargs.url)
        paragraphs = project_note_paragraphs()
        headers = project_note_headers()
        param = parameters
        project = p_con.get_entry(self.pargs.project_id)
        if not project:
            self.log.warn("No such project '{}'".format(self.pargs.project_id))
            return
        
        self.log.debug("Working on project '{}'.".format(self.pargs.project_id))
        samples = p_con.map_srm_to_name(self.pargs.project_id, use_ps_map=self.pargs.use_ps_map, use_bc_map=self.pargs.use_bc_map, check_consistency=self.pargs.check_consistency)
        sample_list = project['samples']
        param.update({key:project.get(ps_to_parameter[key], None) for key in ps_to_parameter.keys()})
        param["ordered_amount"] = param.get("ordered_amount", p_con.get_ordered_amount(self.pargs.project_id))
        param['customer_reference'] = param.get('customer_reference', project.get('customer_reference'))
        param['uppnex_project_id'] = param.get('uppnex_project_id', project.get('uppnex_id'))
        if self.pargs.ordered_million_reads:
            param["ordered_amount"] = self.pargs.ordered_million_reads
        if self.pargs.uppnex_id:
            param["uppnex_project_id"] = self.pargs.uppnex_id
        if self.pargs.customer_reference:
            param["customer_reference"] = self.pargs.customer_reference
        if not param["ordered_amount"]:
            param["ordered_amount"] = self.pargs.ordered_million_reads
        ## Start collecting the data
        sample_table = []
        all_passed = True
        self.log.debug("Looping through sample map that maps project sample names to sample run metrics ids")
        for k,v in samples.items():
            self.log.debug("project sample '{}' maps to '{}'".format(k, v))
            if re.search("Unexpected", k):
                continue
            project_sample = sample_list[v['sample']]
            vals = {x:project_sample.get(prjs_to_table[x], None) for x in prjs_to_table.keys()}
            ## Set status
            vals['Status'] = project_sample.get("status", "N/A")
            vals['MOrdered'] = param["ordered_amount"]
            vals['BarcodeSeq'] = s_con.get_entry(k, "sequence")
            vals.update({k:"N/A" for k in vals.keys() if vals[k] is None})
            if vals['Status']=="N/A" or vals['Status']=="NP": all_passed = False
            sample_table.append([vals[k] for k in table_keys])
        if all_passed: param["finished"] = 'Project finished.'
        sample_table.sort()
        sample_table = list(sample_table for sample_table,_ in itertools.groupby(sample_table))
        sample_table.insert(0, ['ScilifeID', 'CustomerID', 'BarcodeSeq', 'MSequenced', 'MOrdered', 'Status'])
        paragraphs["Samples"]["tpl"] = make_sample_table(sample_table)
        make_note("{}_summary.pdf".format(self.pargs.project_id), headers, paragraphs, **param)






    
