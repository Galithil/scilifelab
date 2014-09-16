import cProfile
import math
import numpy
import matplotlib.pyplot as plt
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

def thingy(data):
    finaldata={}
    for d in data:
        runinfo=[]
        for i in xrange(0,500):
            pr=cProfile.Profile()
            pr.enable()
            #psul.main(data[d][-1], False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
            psul.main(d, False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
            pr.disable()
            s = StringIO.StringIO()
            stats=pstats.Stats(pr, stream=s).sort_stats('cumulative')
            runinfo.append(stats.total_tt)
        finaldata[d]=runinfo
    return finaldata
        
def plothingy(data):
    labels=data.keys()
    formdata=[]
    for d in data:
        formdata.append(data[d])

    bp = plt.boxplot(formdata, notch=0, sym='+', vert=1, whis=1.5)
    plt.setp(bp['boxes'], color='black')
    plt.setp(bp['whiskers'], color='black')
    plt.setp(bp['fliers'], color='red', marker='+')
    plt.savefig('out.png')

def projectsperanp():
    data={}
    allprojs=lims.get_projects()
    f=open("plop.out", "w")
    for pname in [p.name for p in allprojs]:
        if p.open_date.startswith("2014"):
            nbpr=len(lims.get_processes(projectname=pname))
            samples=lims.get_samples(projectname=pname)
            totar=0
            for s in samples:
                totar+=len(lims.get_artifacts(sample_name=s.name))

            tot=totar+nbpr
            if tot not in data:
                data[tot]=[]
            else:
                data[tot].append(pname)

            f.write("{}\t{}\t{}\t{}\n".format(pname,tot, totar, nbpr))
    return data
def plotbis(data):
    allvalues=sorted(data)
    plt.hist(allvalues, 50)
    plt.savefig('hout.png')


def plotanp(data):
    allvalues=sorted(data.keys())
    print allvalues
    formdata=[]
    labels=[]
    for i in xrange(1,11):
        minindex=math.ceil(len(allvalues)/10)*(i-1)
        maxindex=math.ceil(len(allvalues)/10)*i
        print minindex
        print maxindex
        formdata.append[len(allvalues[minindex: maxindex])]
        labels.append(allvalues[maxindex])

    print formdata
    print labels
def get_av_times():
    data=[p.name for p in lims.get_projects()]
    flag=True
    for d in data:

        if (flag==True):
            f=open("times.out", "a")
            totime=0
            for i in xrange(0,100):
                pr=cProfile.Profile()
                pr.enable()
                psul.main(d, False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
                pr.disable()
                s = StringIO.StringIO()
                stats=pstats.Stats(pr, stream=s).sort_stats('cumulative')
                stats.print_stats()
                totime+=stats.total_tt
            totime/=100
            f.write("{}\t\{}\n".format(d, totime))
            f.close()
        if d=='Spruce_11_07':
            flag=True

def cachebias():
    data=['L.Dalen_14_03', 'M.Lundberg_13_03', 'A.Andersson_14_02','C.Wheat_14_03', 'L.Dalen_13_06', 'W.Ye_14_01']



get_av_times()
#plotbis(d.keys())



#data=['L.Dalen_14_03', 'M.Lundberg_13_03', 'A.Andersson_14_02','C.Wheat_14_03', 'L.Dalen_13_06', 'W.Ye_14_01']
#d=thingy(data)
#print d
#d={'a': [1,2,3,4,5,6,7], 'b' : [10,22,45,654,23,76,44]}
#plothingy(d)
#pr=cProfile.Profile()
#pr.enable()
#psul.main('L.Dalen_14_03', False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
#pr.disable()
#s = StringIO.StringIO()
#stats=pstats.Stats(pr, stream=s)
#stats.strip_dirs().sort_stats('cumulative').print_stats(70)
#print s.getvalue() 
#
#pr=cProfile.Profile()
#pr.enable()
#psul.main('W.Ye_14_01', False, 999, '/Users/denismoreno/opt/config/post_process.yaml', 'psul.out')
#pr.disable()
#s = StringIO.StringIO()
#stats=pstats.Stats(pr, stream=s)
#stats.strip_dirs().sort_stats('cumulative').print_stats(70)
#print s.getvalue() 
