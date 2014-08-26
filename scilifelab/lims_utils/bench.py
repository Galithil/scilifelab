import cProfile
from pprint import pprint
import time
import pstats
import StringIO
import project_summary_upload_LIMS as psul
from genologics.entities import *
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
lims = Lims(BASEURI, USERNAME, PASSWORD)
def get_all_projects_with_samples():
    data={}
    allprojs=lims.get_projects()
    for pname in [p.name for p in allprojs]:
        if p.open_date.startswith("2014"):
            nbsamples=len(lims.get_samples(projectname=pname))
            if not data.get(nbsamples):
                data[nbsamples]=[]

            data[nbsamples].append(pname)
    return data

#data=['L.Dalen_14_03', 'M.Lundberg_13_03', 'A.Andersson_14_02','C.Wheat_14_03', 'L.Dalen_13_06']
def get_times(data):
    finaldata={}
    for d in data:
        pr=cProfile.Profile()
        pr.enable()
        #psul.main(data[d][-1], False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
        psul.main(d, False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
        pr.disable()
        s = StringIO.StringIO()
        stats=pstats.Stats(pr, stream=s).sort_stats('cumulative')
        stats.print_stats()
        print "time taken by {} : {}".format(d, stats.total_tt)
        finaldata[d]=stats.total_tt
    

    pprint(finaldata)

pr=cProfile.Profile()
pr.enable()
psul.main('L.Dalen_14_03', False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
pr.disable()
s = StringIO.StringIO()
stats=pstats.Stats(pr, stream=s)
stats.strip_dirs().sort_stats('cumulative').print_stats(70)
print s.getvalue() 

pr=cProfile.Profile()
pr.enable()
psul.main('W.Ye_14_01', False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
pr.disable()
s = StringIO.StringIO()
stats=pstats.Stats(pr, stream=s)
stats.strip_dirs().sort_stats('cumulative').print_stats(70)
print s.getvalue() 
