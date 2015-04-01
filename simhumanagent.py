## simhumanagent.py
#
#  Uses data from human subjects experiments to emulate human agents
#

from configuration import *
from agentgroup import *
from utils import *
import datetime
import operator
import json

import numpy as np  # for genfromtxt and random.choice

## Data format after import:
# uuid:
#  condition
#  apply
#    nohist:  probability
#    deltapay:   glm(deltapay)
#    pastcontrib:   glm(deltapay+pastmeancontribknown)
#    time_q1, time_q3:  upper and lower quartiles for decision delay
#  acceptvote
#    nohist:  probability
#    deltapay:   glm(deltapay)
#    globalrtg:  glm(deltapay+globalrating)
#    pastcontrib:  glm(deltapay+pastmeancontribknown)
#    time_q1, time_q3:  upper and lower quartiles for decision delay
#  join
#    nohist:  probability
#    deltapay:  glm(deltapay)
#    globalrtg:  glm(deltapay+globalrtg)
#    time_q1, time_q3:  upper and lower quartiles for decision delay
#  pubgood
#    contrib_pastcontrib:  glm(meanmeancontrib)
#    contrib_globalrtg:  glm(globalmean)
#    rating_contrib:  glm(pctcontrib)
#    ratings_per_round:  integer
#    time_q1, time_q3:  upper and lower quartiles for decision delay


class humandata(object):
  def __init__(self, datafile):
    self.read_data(datafile)
  
  def read_data(self, filename):
    self.datadict = dat = {}
    
    filedata = np.genfromtxt('userdatatable.csv', delimiter=',', names=True, dtype=None)
    
    for row in filedata:
      udat = dat[row['uuid']] = {}
      udat['condition'] = row['condition']
      
      step = 'apply'
      sdat = udat[step] = {}
      sdat['nohist'] = row[step+'_nohist']
      if row[step+'_deltapay_aic']: # is not NA
        sdat['deltapay'] = {'intercept':row[step+'_deltapay_intercept'],'slope':row[step+'_deltapay_slope']}
      if row[step+'_pastcontrib_aic']: # is not NA
        sdat['pastcontrib'] = {'intercept':row[step+'_pastcontrib_intercept'],'slope':row[step+'_pastcontrib_slope'], 'slope_pay':row[step+'_pastcontrib_slope_pay']}
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
      step = 'acceptvote'
      sdat = udat[step] = {}
      sdat['nohist'] = row[step+'_nohist']
      if row[step+'_deltapay_aic']: # is not NA
        sdat['deltapay'] = {'intercept':row[step+'_deltapay_intercept'],'slope':row[step+'_deltapay_slope']}
      if row[step+'_globalrtg_aic']: # is not NA
        sdat['globalrtg'] = {'intercept':row[step+'_globalrtg_intercept'],'slope':row[step+'_globalrtg_slope'], 'slope_pay':row[step+'_globalrtg_slope_pay']}
      if row[step+'_pastcontrib_aic']: # is not NA
        sdat['pastcontrib'] = {'intercept':row[step+'_pastcontrib_intercept'],'slope':row[step+'_pastcontrib_slope'], 'slope_pay':row[step+'_pastcontrib_slope_pay']}
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
      step = 'join'
      sdat = udat[step] = {}
      sdat['nohist'] = row[step+'_nohist']
      if row[step+'_deltapay_aic']: # is not NA
        sdat['deltapay'] = {'intercept':row[step+'_deltapay_intercept'],'slope':row[step+'_deltapay_slope']}
      if row[step+'_globalrtg_aic']: # is not NA
        sdat['globalrtg'] = {'intercept':row[step+'_globalrtg_intercept'],'slope':row[step+'_globalrtg_slope'], 'slope_pay':row[step+'_globalrtg_slope_pay']}
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
      step = 'pubgood'
      sdat = udat[step] = {}
      sdat['avgcontrib'] = row[step+'_avgcontrib']
      if abs(row[step+'_contrib_globalrtg_r2']) > 0.2:
        sdat['contrib_globalrtg'] = {'intercept':row[step+'_contrib_globalrtg_intercept'], 'slope':row['_contrib_globalrtg_slope']}
      if abs(row[step+'_contrib_pastcontrib_r2']) > 0.2:
        sdat['contrib_pastcontrib'] = {'intercept':row[step+'_contrib_pastcontrib_intercept'], 'slope':row['_contrib_pastcontrib_slope']}
      if abs(row[step+'_rating_contrib_r2']) > 0.2:
        sdat['rating_contrib'] = {'intercept':row[step+'_rating_contrib_intercept'], 'slope':row[step+'_rating_contrib_slope'], 'stderr':row[step+'_rating_contrib_stderr']}
      sdat['ratings_per_round'] = row[step+'_ratings_per_round']
      sdat['ratings_per_round_sd'] = row[step+'_ratings_per_round_sd']
      sdat['rating_props'] = [row[step+'_pct'+str(i)] for i in range(1,6)]
      sdat['cum_rating_props'] = [sum(sdat['rating_props'][0:i]) for i in range(1,6)]
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
    #print dat
      
  def gen_agent(self, cfg, uuid=None):
    # Create a simhumanagent from one of the rows of the data file
    # If uuid is None, pick a row randomly
    if uuid:
      return simhumanagent(cfg, self.datadict[uuid])
    else:
      return simhumanagent(cfg, random.choice(self.datadict.keys()))



def logoddstoprob(logodds):
  odds = math.exp(logodds)
  return odds/(1+odds)

class simhumanagent(agent):
  # Currently mostly copied from dumbagent
  def __init__(self, cfg, probdata, adat=None, skills=None, aid=None):
    super(simhumanagent, self).__init__(cfg, adat, skills, aid)
    # get info from the humandata class to init probabilities
    
    self.type = 'simhuman'
    self.uuid = probdata['uuid']
    
    self.probdata = probdata
    
    self.current_ratings = {}
    self.contrib_history = {}
    self.contrib_avg = {}
    
    if self.cfg.delay_sim_agents:
      self.slow = True
    else:
      self.tf_delay=self.tf_delay_null
      
    # if pubgoods rating r2 is bad, assign to 'rate_random' or 'rate_contrib'
    if abs(row[step+'_rating_contrib_r2']) > 0.2:
      self.rate_pubgood = self.rate_contrib
    else:
      self.rate_pubgood = self.rate_random
  
  def propose(self):
    self.update()
    task = self.cfg.task
    nowpay = self.nowpay
    
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    if not len(nbrgroups):
      return
    
    self.tf_delay('propose')
    
    paylm = self.probdata['apply']['deltapay']
    contriblm = self.probdata['apply']['pastcontrib']
    
    ## There's really no reason to use the nohist probability
    
    for g in nbrgroups:
      deltapay = task(newskills)/(g.gsize+1) - self.nowpay
      pastcontribs = [self.contrib_avg[a.id] for a in g.agents if a.id in self.contrib_avg]
      
      if len(pastcontribs):
        # If there's contrib history, use the more detailed glm
        pastavg = sum(pastcontribs)/len(pastcontribs)
        papply = logoddstoprob(contriblm['intercept']+pastcontrib*contriblm['slope']+deltapay*contriblm['slope_pay'])
      else:
        # Otherwise, just figure on the difference in pay
        papply = logoddstoprob(paylm['intercept']+deltapay*paylm['slope'])
    
      if random.random() < papply:
        g.takeapplication(self)
    
  def acceptvote(self, applicants):
    # Generate a probability for all of them
    # Generate a random choice for all of them
    # if there is more than one chosen tiebreak based on... probability? Something?
    # if there is none chosen, that's ok
    
    if not len(applicants): # may not be necessary
      return
    
    self.tf_delay('acceptvote')

    task = self.cfg.task
    nowpay = self.nowpay
    nowgsize = self.group.gsize
    
    # glms: deltapay, globalrtg, pastcontrib
    # AIC is in all but one case improving in that order
    paylm = self.probdata['acceptvote']['deltapay']
    ratelm = self.probdata['acceptvote']['globalrtg']
    contriblm = self.probdata['acceptvote']['pastcontrib']
    
    accepts = {}
    for a in applicants:
      deltapay = task(self.group.withskills(a))/(nowgsize + a.gsize) - nowpay
      if a.id in self.contrib_avg:
        pastcontrib = self.contrib_avg[a.id]
        paccept = logoddstoprob(contriblm['intercept']+pastcontrib*contriblm['slope']+deltapay*contriblm['slope_pay'])
      elif a.id in self.global_ratings:
        globalrtg = self.global_ratings[a.id]
        paccept = logoddstoprob(ratelm['intercept']+globalrtg*ratelm['slope']+deltapay*ratelm['slope_pay'])
      else:
        paccept = logoddstoprob(paylm['intercept']+deltapay*paylm['slope'])
      
      if random.random() < paccept:
        accepts[a]= paccept
    
    if not len(accepts):    
      return None
    elif len(accepts) == 1:
      return accepts.keys()[0]
    else:
      agents = accepts.keys()
      probs = np.array(accepts.values())
      probs /= probs.sum()
      return np.random.choice(agents, p=probs)
    
  def consider(self):
    task=self.cfg.task
    
    # Find highest-value group to join
    if not len(self.acceptances):
      return
    self.update()
    
    self.tf_delay('join')
    
    paylm = self.probdata['join']['deltapay']
    ratelm = self.probdata['join']['globalrtg']
    
    joins = {}
    for g in self.acceptances:
      deltapay = task(newskills)/(g.gsize+1) - self.nowpay
      globalrtgs = [self.global_ratings[a.id] for a in g.agents if a.id in self.global_ratings]
      
      if len(globalrtgs):
        globalrtg = sum(globalrtgs)/len(globalrtgs)
        pjoin = logoddstoprob(ratelm['intercept']+globalrtg*ratelm['slope']+deltapay*ratelm['slope_pay'])
      else:
        pjoin = logoddstoprob(paylm['intercept']+deltapay*paylm['slope'])
    
      if random.random() < pjoin:
        joins[g] = pjoin
    
    if len(joins) == 1:
      self.switchgroup(joins.keys()[0])
    else:
      agents = joins.keys()
      probs = np.array(joins.values())
      probs /= probs.sum()
      self.switchgroup(np.random.choice(agents, p=probs))
    
    self.acceptances = []
  
  def expelvote(self):
    return random.choice(self.group.agents + [None])
  
  def postprocess(self, globalpay=None):
    pass

  def publicgoods(self, pgdict, potmult):
    self.update()
    nowpayint = int(self.nowpay)
    #return random.randint(0, int(self.nowpay))
    contrib = random.randint(0, nowpayint)
    pgdict[self] = (contrib, nowpayint-contrib)
  
  def publicgoods_postprocess(self, newpay, teampays):
    self.pgpay = newpay
    
    teammateids = [n.id for n in self.group.agents]
    pctcontribs = [teampays[n][0]/sum(teampays[n]) for n in teammateids]
    
    # Record history
    for nid,pctcontrib in zip(teammateids, pctcontribs):
      try:
        hist = self.contrib_history[nid]
        hist.append(pctcontrib)
        self.contrib_avg[nid] = sum(hist)/len(hist)
      except KeyError:
        self.contrib_avg[nid] = pctcontrib
        self.contrib_history[nid] = [pctcontrib]
    
    # Assign ratings
    #if abs(row[step+'_rating_contrib_r2']) > 0.2:
    #    sdat['rating_contrib'] = {'intercept':row[step+'_rating_contrib_intercept'], 'slope':row['_rating_contrib_slope']}
    #  sdat['ratings_per_round'] = row[step+'_ratings_per_round']
    ratings = self.rate_pubgood(teammateids, pctcontribs)
     
     
  def gen_num_ratings(self):
    pgdata = self.probdata['pubgood']
    nrats = pgdata['ratings_per_round']
    nzero = pgdata['prop_rounds_nrats_0']
    if nrats <= 1:
      return int(random.random() < nrats)
    elif random.random() < nzero:
      return 0
    elif nrats > 1:
      nratsd = pgdata['ratings_per_round']
      if nratsd:
        # Decide how many ratings to actually give, based on mean and sd
        # This is a very handwavy approximation of the very right-skewed ratings-per-round distribution
        nowrats = round(abs(random.normalvariate(nrats,nratsd)))
      else:
        nowrats = int(nrats)    # if there is no sd, all nrats must be the same, and therefore, must be an integer
      return nowrats
    else:
      return 0
      
  def rate_contrib(self, teamids, teamcontribs):
    pgdata = self.probdata['pubgood']
    nrats = self.gen_num_ratings()
    if nrats == 0:  return {}
    
    # Use linear model to generate ratings based on contributions
    tcdict = dict(zip(teamids, teamcontribs))
    try:
      rids = random.sample(teamids, nrats)
    except ValueError:
      rids = [random.choice(teamids) for i in range(nrats)]
    
    rdict = {}
    slope = pgdata['rating_contrib']['slope']
    intercept = pgdata['rating_contrib']['intercept']
    stderr = pgdata['rating_contrib']['stderr']
    for nid in rids:
      # Generate a rating for this person
      contrib = tcdict[nid]
      rawrtg = intercept + slope*contrib        # Calc rating from linear model
      rawrtg += random.normalvariate(0, stderr) # Add noise
      rating = int(round(rawrtg))
      rdict[nid] = rating
    return rdict  
  
  def gen_rating(self, cumprobs):
    rpick = random.random()   
    for i,prop in enumerate(cumprobs):
      if rpick < prop: return i + 1
      
  def rate_random(self, teamids, teamcontribs):
    pgdata = self.probdata['pubgood']
    return {random.choice(teamids):self.gen_rating(pgdata['cum_rating_props']) for i in range(self.gen_num_ratings())}
    
  def updateratings(self, ratings):
    self.global_ratings = ratings
  
  def tf_delay_null(self, stage):
    pass

  def tf_delay(self, stage):
    q1 = self.probdata[stage]['time_q1']
    med = self.probdata[stage]['time_med']
    q3 = self.probdata[stage]['time_q3']
    
    # This will be biased towards the central values, but that is ok
    # We don't want outliers here, especially on the high end
    waittime = random.triangular(q1, q3, med)
    time.sleep(waittime)
    
  
if __name__=='__main__':
  import sys
  datafile = sys.argv[1]
  h = humandata(datafile)