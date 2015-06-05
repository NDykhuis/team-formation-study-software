## simhumanagent.py
#
#  Uses data from human subjects experiments to emulate human agents
#

import math
import random
import time

import numpy as np  # for genfromtxt and random.choice

from configuration import Configuration
from agentgroup import Agent

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


class HumanData(object):
  def __init__(self, datafile):
    self.read_data(datafile)
  
  def qstrip(self, text):
    return text.strip('"')
  
  def read_data(self, filename):
    self.datadict = dat = {}
    
    filedata = np.genfromtxt(filename, delimiter=',', 
                             names=True, dtype=None, missing_values='NA')
    
    for row in filedata:
      uuid = self.qstrip(row['uuid'])
      udat = dat[uuid] = {}
      udat['condition'] = self.qstrip(row['condition'])
      udat['uuid'] = uuid
      
      step = 'apply'
      sdat = udat[step] = {}
      sdat['nohist'] = row[step+'_nohist']
      if row[step+'_deltapay_aic']: # is not NA
        sdat['deltapay'] = {
          'intercept':row[step+'_deltapay_intercept'],
          'slope':row[step+'_deltapay_slope']
        }
      if row[step+'_pastcontrib_aic']: # is not NA
        sdat['pastcontrib'] = {
          'intercept':row[step+'_pastcontrib_intercept'],
          'slope':row[step+'_pastcontrib_slope'],
          'slope_pay':row[step+'_pastcontrib_slope_pay']
        }
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
      step = 'acceptvote'
      sdat = udat[step] = {}
      sdat['nohist'] = row[step+'_nohist']
      sdat['noaccept'] = row[step+'_noaccept']
      sdat['stayaccept'] = row[step+'_stayaccept']
      if row[step+'_deltapay_aic']: # is not NA
        sdat['deltapay'] = {
          'intercept':row[step+'_deltapay_intercept'],
          'slope':row[step+'_deltapay_slope']
        }
      if row[step+'_globalrtg_aic']: # is not NA
        sdat['globalrtg'] = {
          'intercept':row[step+'_globalrtg_intercept'],
          'slope':row[step+'_globalrtg_slope'],
          'slope_pay':row[step+'_globalrtg_slope_pay']
        }
      if row[step+'_pastcontrib_aic']: # is not NA
        sdat['pastcontrib'] = {
          'intercept':row[step+'_pastcontrib_intercept'],
          'slope':row[step+'_pastcontrib_slope'],
          'slope_pay':row[step+'_pastcontrib_slope_pay']
        }
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
      step = 'join'
      sdat = udat[step] = {}
      sdat['nohist'] = row[step+'_nohist']
      if row[step+'_deltapay_aic']: # is not NA
        sdat['deltapay'] = {
          'intercept':row[step+'_deltapay_intercept'], 
          'slope_stay':row[step+'_deltapay_stay'], 
          'slope':row[step+'_deltapay_slope']
        }
      if row[step+'_globalrtg_aic']: # is not NA
        sdat['globalrtg'] = {
          'intercept':row[step+'_globalrtg_intercept'], 
          'slope_stay':row[step+'_deltapay_stay'], 
          'slope':row[step+'_globalrtg_slope'], 
          'slope_pay':row[step+'_globalrtg_slope_pay']
        }
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
      step = 'pubgood'
      sdat = udat[step] = {}
      sdat['avgcontrib'] = row[step+'_avgcontrib']
      sdat['sdcontrib'] = row[step+'_sdcontrib']
      if abs(row[step+'_contrib_globalrtg_r2']) > 0.2:
        sdat['contrib_globalrtg'] = {
          'intercept':row[step+'_contrib_globalrtg_intercept'], 
          'slope':row[step+'_contrib_globalrtg_slope'], 
          'stderr':row[step+'_contrib_globalrtg_stderr'], 
          'r2':row[step+'_contrib_globalrtg_r2']
        }
      if abs(row[step+'_contrib_pastcontrib_r2']) > 0.2:
        sdat['contrib_pastcontrib'] = {
          'intercept':row[step+'_contrib_pastcontrib_intercept'], 
          'slope':row[step+'_contrib_pastcontrib_slope'], 
          'stderr':row[step+'_contrib_pastcontrib_stderr'], 
          'r2':row[step+'_contrib_pastcontrib_r2']
        }
      if abs(row[step+'_rating_contrib_r2']) > 0.2:
        sdat['rating_contrib'] = {
          'intercept':row[step+'_rating_contrib_intercept'], 
          'slope':row[step+'_rating_contrib_slope'], 
          'stderr':row[step+'_rating_contrib_stderr']
        }
      sdat['ratings_per_round'] = row[step+'_ratings_per_round']
      sdat['ratings_per_round_sd'] = row[step+'_ratings_per_round_sd']
      sdat['prop_rounds_nrats_0'] = row[step+'_prop_rounds_nrats_0']
      sdat['rating_props'] = [row[step+'_pct'+str(i)] for i in range(1, 6)]
      sdat['cum_rating_props'] = [sum(sdat['rating_props'][0:i]) 
                                  for i in range(1, 6)]
      sdat['time_q1'] = row[step+'_time_q1']
      sdat['time_med'] = row[step+'_time_med']
      sdat['time_q3'] = row[step+'_time_q3']
      
    #print dat
    
    self.datapublic = [dat[u] for u in dat if dat[u]['condition'] == 'public']
    self.dataprivate = [dat[u] for u in dat if dat[u]['condition'] == 'private']
      
  def gen_agent(self, cfg, adat=None, uuid=None):
    # Create a SimHumanAgent from one of the rows of the data file
    # If uuid is None, pick a row randomly
    if uuid:
      try:
        return SimHumanAgent(cfg, self.datadict[uuid], adat)
      except KeyError as e:
        print "Fail to create agent: agent",uuid,"not in data!"
        time.sleep(10)  # Wait for database to flush
        raise e
        
        # Actually, just return a random agent so we don't crash?
        #pass
    
    #return SimHumanAgent(cfg, self.datadict[random.choice(self.datadict.keys())], adat)
    if cfg.show_global_ratings:
      return SimHumanAgent(cfg, random.choice(self.datapublic), adat)
    else:
      return SimHumanAgent(cfg, random.choice(self.dataprivate), adat)



def logoddstoprob(logodds):
  try:
    odds = math.exp(logodds)
    return odds/(1+odds)
  except OverflowError:
    return 1.0

class SimHumanAgent(Agent):
  # Currently mostly copied from dumbagent
  def __init__(self, cfg, probdata, adat=None, skills=None, aid=None):
    super(SimHumanAgent, self).__init__(cfg, adat, skills, aid)
    # get info from the humandata class to init probabilities
    
    self.type = 'simhuman'
    self.disposition = probdata['uuid']
    
    self.probdata = probdata
    
    self.current_ratings = {}
    self.contrib_history = {}
    self.contrib_avg = {}
    
    if self.cfg.delay_sim_agents:
      self.slow = True
      self.tf_delay = self.tf_delay_real
    else:
      self.tf_delay = self.tf_delay_null
      
    # if pubgoods rating r2 is bad, assign to 'rate_random' or 'rate_contrib'
    if 'rating_contrib' in probdata['pubgood']:
      self.rate_pubgood = self.rate_contrib
    else:
      self.rate_pubgood = self.rate_random
      
    self.my_ratings = {}
  
  def propose(self):
    self.update()
    task = self.cfg.task
    nowpay = self.nowpay
    
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    if not len(nbrgroups):
      return
    
    self.tf_delay('propose')
    
    paylm = self.probdata['apply'].get('deltapay', None)
    contriblm = self.probdata['apply'].get('pastcontrib', None)
    
    ## There's really no reason to use the nohist probability
    
    applies = []
    for g in nbrgroups:
      newskills = g.withskills(self)
      deltapay = task(newskills)/(g.gsize+1) - self.nowpay
      pastcontribs = [self.contrib_avg[a.id] for a in g.agents 
                      if a.id in self.contrib_avg]
      
      if contriblm and len(pastcontribs):
        # If there's contrib history, use the more detailed glm
        pastavg = sum(pastcontribs)/len(pastcontribs)
        papply = logoddstoprob(contriblm['intercept'] + \
          pastavg*contriblm['slope'] + deltapay*contriblm['slope_pay'])
      elif paylm:
        # Otherwise, just figure on the difference in pay
        papply = logoddstoprob(paylm['intercept'] + deltapay*paylm['slope'])
      else:
        # Should never be used
        papply = self.probdata['apply']['apply_nohist']
    
      if random.random() < papply:
        applies.append(g.id)
        g.takeapplication(self)
      
    self.logp( ('Agent', self.id, self.disposition, 'applies to', applies) )
    
  def acceptvote(self, applicants):
    # Generate a probability for all of them
    # Generate a random choice for all of them
    # if there is more than one chosen tiebreak based on... probability?
    # if there is none chosen, that's ok
    
    if not len(applicants): # may not be necessary
      return
    
    self.tf_delay('acceptvote')

    task = self.cfg.task
    nowpay = self.nowpay
    nowgsize = self.group.gsize
    
    # glms: deltapay, globalrtg, pastcontrib
    # AIC is in all but one case improving in that order
    paylm = self.probdata['acceptvote'].get('deltapay', None)
    ratelm = self.probdata['acceptvote'].get('globalrtg', None)
    contriblm = self.probdata['acceptvote'].get('pastcontrib', None)
    
    accepts = {}
    maxdeltapay = 0
    for a in applicants:
      deltapay = task(self.group.withskills(a))/(nowgsize + a.gsize) - nowpay
      maxdeltapay = max(maxdeltapay, deltapay)
      if contriblm and a.id in self.contrib_avg:
        pastcontrib = self.contrib_avg[a.id]
        paccept = logoddstoprob(contriblm['intercept'] + \
          pastcontrib*contriblm['slope'] + deltapay*contriblm['slope_pay'])
      elif ratelm and a.id in self.global_ratings:
        globalrtg = self.global_ratings[a.id]
        paccept = logoddstoprob(ratelm['intercept'] + \
          globalrtg*ratelm['slope'] + deltapay*ratelm['slope_pay'])
      elif paylm:
        paccept = logoddstoprob(paylm['intercept']+deltapay*paylm['slope'])
      else:
        paccept = self.probdata['acceptvote']['acceptvote_nohist']
      
      accepts[a] = paccept
    
    if maxdeltapay:
      accepts[None] = self.probdata['acceptvote']['noaccept']
    else:
      accepts[None] = self.probdata['acceptvote']['stayaccept']
      
    #print self.id, self.disposition, "accepts", accepts
      
    agents = accepts.keys()
    probs = np.array(accepts.values())
    if probs.sum():
      probs /= probs.sum()
      choice = np.random.choice(agents, p=probs)
    else:
      print "ZERO PROBS IN ACCEPT"
      print self.id, self.disposition, "accepts", accepts
      choice = None
      
    self.logp( ('Agent', self.id, self.disposition, 'accepts', 
                choice.id if choice is not None else choice) )
    return choice
    
  def consider(self):
    task = self.cfg.task
    
    # Find highest-value group to join
    if not len(self.acceptances):
      return
    self.update()
    
    self.tf_delay('join')
    
    paylm = self.probdata['join'].get('deltapay', None)
    ratelm = self.probdata['join'].get('globalrtg', None)
    
    joins = {}
    self.acceptances.append(self.group)
    for g in self.acceptances:
      newskills = g.withskills(self)
      deltapay = task(newskills)/(g.gsize+1) - self.nowpay
      globalrtgs = [self.global_ratings[a.id] for a in g.agents 
                    if a.id in self.global_ratings]
      
      # because staygroup is always zero, I don't think we need to include that term?
      # Unless we're doing some sort of softmax?
      if ratelm and len(globalrtgs):
        globalrtg = sum(globalrtgs)/len(globalrtgs)
        pjoin = logoddstoprob(ratelm['intercept'] + globalrtg*ratelm['slope'] + \
          deltapay*ratelm['slope_pay'] + (g==self.group)*ratelm['slope_stay'])
      elif paylm:
        pjoin = logoddstoprob(paylm['intercept'] + deltapay*paylm['slope'] + \
          (g==self.group)*ratelm['slope_stay'])
      else:
        # Should not be used - should always be using paylm as the fallback
        ## DOES NOT account for switch/stay!
        pjoin = self.probdata['join']['join_nohist']
    
      joins[g] = pjoin
    
    #print self.id, self.disposition, "joins", joins
    
    agents = joins.keys()
    probs = np.array(joins.values())
    if probs.sum():
      probs /= probs.sum()
      bestgroup = np.random.choice(agents, p=probs)
      if bestgroup != self.group:
        self.logp( ('Agent', self.id, self.disposition, 'joins', bestgroup.id) )
        self.switchgroup(bestgroup)
      else:
        self.logp( ('Agent', self.id, self.disposition, 'stays') )
    else:
      print "ZERO PROBS IN JOIN"
      self.logp( (self.id, self.disposition, "joins", joins) )
    
    self.acceptances = []
  
  def expelvote(self):
    return random.choice(self.group.agents + [None])
  
  def postprocess(self, globalpay=None):
    pass

  def publicgoods(self, pgdict, potmult):
    self.update()
    nowpayint = int(self.nowpay)
    
    teammates = [a for a in self.group.agents if a != self]
    pastcontribs = [self.contrib_avg[a.id] for a in teammates 
                    if a.id in self.contrib_avg]
    glorats = [self.global_ratings[a.id] for a in teammates 
               if a.id in self.global_ratings]
    contriblm = self.probdata['pubgood'].get('contrib_pastcontrib', None)
    ratelm = self.probdata['pubgood'].get('contrib_globalrtg', None)
    contribr2 = abs(contriblm['r2']) if contriblm else 0
    rater2 = abs(ratelm['r2']) if ratelm else 0
    
    # Use the best model for which we have data.
    if len(glorats) and ratelm and (not len(pastcontribs) or rater2 > contribr2):
      rateavg = sum(glorats)/len(glorats)
      pctcontrib = ratelm['intercept'] + rateavg*ratelm['slope']
      pctcontrib += random.normalvariate(0, ratelm['stderr'])
    elif (len(pastcontribs) and contriblm and 
          (not len(glorats) or contribr2 > rater2) ):
      pastavg = sum(pastcontribs)/len(pastcontribs)
      pctcontrib = contriblm['intercept'] + pastavg*contriblm['slope']
      pctcontrib += random.normalvariate(0, contriblm['stderr'])
    else:
      pctcontrib = self.probdata['pubgood']['avgcontrib'] + \
        random.normalvariate(0, self.probdata['pubgood']['sdcontrib'])
    pctcontrib = min(max(pctcontrib, 0.0), 1.0)
    
    contrib = int(round(nowpayint * pctcontrib))
    
    pgdict[self] = (contrib, nowpayint-contrib)
    self.logp( ('Agent', self.id, self.disposition, 'contribs', contrib) )
  
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, 
                              potpay, teampays):
    self.pgpay = privatepay+potpay
    self.finalpay += self.pgpay
    
    teammateids = [n.id for n in self.group.agents]
    pctcontribs = [teampays[n][0]/sum(teampays[n]) for n in teammateids]
    
    # Record history
    for nid, pctcontrib in zip(teammateids, pctcontribs):
      try:
        hist = self.contrib_history[nid]
        hist.append(pctcontrib)
        self.contrib_avg[nid] = sum(hist)/len(hist)
      except KeyError:
        self.contrib_avg[nid] = pctcontrib
        self.contrib_history[nid] = [pctcontrib]
    
    # Assign ratings
    ratings = self.rate_pubgood(teammateids, pctcontribs)
    if len(ratings):
      print self.id, self.disposition, 'rates', ratings
    
    self.my_ratings.update(ratings)
    
     
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
        # This is a very handwavy approximation of the very right-skewed 
        #   ratings-per-round distribution
        nowrats = int(round(abs(random.normalvariate(nrats, nratsd))))
      else:
        # if there is no sd, all nrats must be the same, and therefore, 
        # must be an integer
        nowrats = int(nrats)
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
      rids = [random.choice(teamids) for _ in range(nrats)]
    
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
      rating = max(min(rating, 5), 1)           # Constrain to valid range
      rdict[nid] = rating
    return rdict  
  
  def gen_rating(self, cumprobs):
    # This could be replaced by np.random.choice(vals, p=probs)
    rpick = random.random()   
    for i, prop in enumerate(cumprobs):
      if rpick < prop: return i + 1
      
  def rate_random(self, teamids, teamcontribs):
    pgdata = self.probdata['pubgood']
    return {random.choice(teamids):self.gen_rating(pgdata['cum_rating_props']) 
            for i in range(self.gen_num_ratings())}
    
  def updateratings(self, ratings):
    self.global_ratings = ratings
  
  def getratings(self):
    return self.my_ratings
  
  def tf_delay_null(self, stage):
    pass

  def tf_delay_real(self, stage):
    q1 = self.probdata[stage]['time_q1']
    med = self.probdata[stage]['time_med']
    q3 = self.probdata[stage]['time_q3']
    
    # This will be biased towards the central values, but that is ok
    # We don't want outliers here, especially on the high end
    waittime = random.triangular(q1, q3, med)
    time.sleep(waittime)
    

def _test_readfile():
  import sys
  datafile = sys.argv[1]
  h = HumanData(datafile)
  c = Configuration()
  a = h.gen_agent(c)

if __name__ == '__main__':
  _test_readfile()
