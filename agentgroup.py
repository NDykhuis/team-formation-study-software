import random
from configuration import *
import threading
import numpy as np
import time

class actor(object):
  skills = []
  gsize = 0
  idcounter = 0
  def propose(self):
    pass
  def consider(self):
    pass
  def accept(self):
    pass
  def reset(self):
    # Reset simulation-specific parameters, such as group, pay, etc.
    pass

class ultagent(object):
  ## ULTIMATUM FUNCTIONS
  def ultimatum_init(self, distribution='normal', p1=5, p2=1, delaymean=5, delaysd=2):
    self.p1, self.p2, self.delaymean, self.delaysd = p1, p2, delaymean, delaysd
    if distribution == 'normal':
      # p1 is mean, p2 is sd
      self.random = random.gauss
    elif distribution == 'uniform':
      # p1 is lower bound, p2 is upper
      self.random = random.randint
  
  def fake_wait(self):
    if configuration.delay_sim_agents:
      time.sleep(max(random.gauss(self.delaymean, self.delaysd), 0))

  def ultimatum(self, other_player):
    pass
  
  def dictator(self, other_player):
    pass
  
  def ask_for_offer(self, other_player):
    offer = int(round(self.random(self.p1, self.p2), 0))
    offer = max(offer, 0)
    offer = min(offer, 10)
    
    print "Going to offer", offer
    self.fake_wait()
    print "Offering!"
    
    return offer
  
  def wait_offer(self, other_player):
    pass
  
  def decide_offer(self, other_player, amount):
    # threshold for offer the player will accept is inverse of the kind of offers this player makes
    threshold = 10-int(round(self.random(self.p1, self.p2), 0))
    
    self.fake_wait()
    
    return (amount > threshold)
  
  def wait_decide(self, other_player):
    pass
  
  def show_conclusion_u(self, other_player, amount, result, role):
    pass
  
  def show_conclusion_d(self, other_player, amount, role):
    pass

class agent(actor):
  def __init__(self, cfg, adat=None, skills=None, aid=None):
    self.cfg = cfg
    if adat is None:
      if aid is None:
        self.id = agent.idcounter; agent.idcounter += 1
      else:
        self.id = aid 
      if skills is None: 
        #skills=[0]*cfg.nskills
        skills = np.zeros(cfg.nskills, dtype='int')
      self.skills = np.array(skills)
      self.group = 0
      self.switches = 0
      self.bias = {}
      self.nowpay = 0
    else:
      self.id = adat['id']
      self.skills = np.array(adat['skills'])
      self.switches = adat['switches']
      self.group = adat['group']
      self.nowpay = adat['nowpay']
      #self.bias = adat['bias']
      self.bias = {}
    self.gsize = 1
    self.acceptances = []
    
    self.leftovers = 0
    
    self.worth = 0  # TEMPORARY
    
    self.slow = False   # For threading
    self.dumb = False
    self.type = 'sim'
    
  def randskills(self):
    nskills = len(self.skills)
    lev = random.randint(1,min(nskills,self.cfg.maxskills))
    #s = [1]*lev + [0]*(nskills-lev)
    s = np.zeros(nskills, dtype='int')
    for i in range(lev):
      s[random.choice(nskills)] += 1
    #random.shuffle(s)
    self.skills=s
  
  def randbiases(self):
    for n in self.nbrs:
      #self.bias[n] = np.random.normal()    # does not use the same random seed
      self.bias[n.id] = random.triangular(1.0, self.cfg.biasrange, 1)**random.choice((-1.0, 1.0))   # multiplier for utility of working with someone
  
  def update(self):
    if self.cfg.bias:
      self.nowpay = self.nowpaycalc(self.cfg.task(self.group.skills))
    else:
      self.nowpay = self.cfg.task(self.group.skills)/self.group.gsize
    
  def nowpaycalc(self, pay, addagent=-1, delagent=-1):
    alist = [a.id for a in self.group.agents if a.id != delagent]
    if addagent != -1:
      alist += [addagent]
    #return pay*np.mean([self.bias.get(n, 1.0) for n in alist])/len(alist)
    return pay/(len(alist))*self.biasavg(alist)
  
  def biasavg(self, agents):
    return float(sum([self.bias.get(nid, 1.0) for nid in agents]))/(len(agents))    # one for average bias, other for fraction of pay
  
  def propose(self):
    ### IMPLEMENT IN CHILDREN ###
    pass

  def notifyaccept(self, group):
    self.acceptances.append(group)

  def acceptvote(self, applicants):
    ### IMPLEMENT IN CHILDREN ###
    pass

  def consider(self):
    ### IMPLEMENT IN CHILDREN ###
    pass

  def expelvote(self):
    ### IMPLEMENT IN CHILDREN ###
    pass
  
  def switchgroup(self, newgroup):
    if self.cfg._verbose > 3:
      print "Agent", self.id, "joining group", newgroup.id
    self.group.remove(self)
    self.group = newgroup
    newgroup.add(self)
    self.switches += 1
    self.update()
  
  def notifygaccept(self, aid):
    ### IMPLEMENT IN HUMAN CLIENT ###
    pass
  
  def notifyjoin(self, aid, add=True):
    ### IMPLEMENT IN HUMAN CLIENT ###
    pass
  
  def neighbors(self):
    G = self.cfg._Gptr
    self.nbrs = set(self.cfg._agentdict[aid] for aid in G[self.id].iterkeys())
    self.totalweight = sum(dat['weight'] for dat in G[self.id].itervalues())
    
  def nbrweight(self):
    G = self.cfg._Gptr
    self.maxweight = sum(dat['weight'] for dat in G[self.id].itervalues())
 
  def addnbrgroups(self, nbrdict):
    for n in self.nbrs:
      nbrdict[n.group.id] = n.group
  
  def addnbr(self, nbr):
    self.nbrs.add(nbr)

  def postprocess_iter(self):
    pass

  def postprocess(self, globalpay=None):
    ### IMPLEMENT IN CHILDREN ###
    pass
  
  def publicgoods(self, pgdict):
    pass
  
  def publicgoods_postprocess(self, newpay, teampays):
    pass
    
  def reset(self):
    if not self.cfg.keep_teams:
      self.group = 0
    self.acceptances = []
    self.switches = 0
    self.gsize = 1      # for compatibility with group merging
    self.nowpay = 0
    self.neighbors()
    
class group(actor):
  def __init__(self, gid, cfg):
    self.id = gid
    self.cfg = cfg
    self.skills = np.zeros(cfg.nskills, dtype='int')
    self.nskills = cfg.nskills
    self.agents = []
    self.applications = []
    self.acceptances = []
    self.gsize = 0
    self.nowpay = 0
    self.worth = 0
    self.slow = False
    
  def update(self):
    # Update all cached values
    self.worth = sum(a.worth for a in self.agents)
    self.gsize = len(self.agents)
    self.slow = any(a.slow for a in self.agents)
    try:
      if self.cfg.bias:
        self.nowearns = self.cfg.task(self.skills)
        self.nowpay = sum(a.nowpaycalc(self.nowearns) for a in self.agents)/self.gsize
      else:
        self.nowpay = self.cfg.task(self.skills)/self.gsize
    except ZeroDivisionError:
      self.nowpay = 0

  def addfirst(self, agent):
    agent.group = self
    self.add(agent)

  def add(self, agent):
    self.notifyjoin(agent.id, add=True)
    self.agents.append(agent)
    self.skills = self.withskills(agent)
    self.update()
    
    if self.cfg.fully_connect_groups:
      for a in self.agents:
        if a != agent:
          self.cfg._Gptr.add_edge(a.id, agent.id, weight=1.0, bias=0.0)
          a.addnbr(agent)
          agent.addnbr(a)
    
  def remove(self, agent):
    if agent in self.agents:
      self.agents.remove(agent)
      self.skills = self.withoutskills(agent)
      self.update()
      self.notifyjoin(agent.id, add=False)

  def withskills(self, agent):
    #return [self.skills[i] + agent.skills[i] for i in range(self.nskills)]
    #print type(self.skills), type(agent.skills)
    return self.skills + agent.skills
  def withoutskills(self, agent):
    return self.skills - agent.skills

  def takeapplication(self, agent):
    self.applications.append(agent)

  def propose(self):
    if self.cfg.bias:
      raise NotImplementedError("Propose does not work with bias yet!")
    if self.gsize == 1:
      return
    task=self.cfg.task
    nbrgroups = self.findnbrgroups()
    for g in nbrgroups.values():
      if g == self:
        continue
      newskills = g.withskills(self)
      if task(newskills)/(g.gsize+self.gsize) >= self.nowpay:
        #print "group", self.id, "proposing to", g.id
        g.takeapplication(self)

  def acceptvote_thread(self, a, applications, votes):
    vote = a.acceptvote(applications)
    votes.append(vote)

  def consider(self):
    # This function handles both groups and agents in the groupmerge case
    if not len(self.applications):
      return
    
    # This speeds things up immensely in the complete graph!
    #self.applications = random.sample(self.applications, len(self.applications))
    # no longer necessary because of random value in the tiebreaking code
    
    self.update()
    
    task = self.cfg.task
    nowpay = self.nowpay
    
    bestagent = None
    
    # Have each member vote on who to accept (-1 means accept no one)
    votes = []
    if self.cfg._threaded_sim:
      mythreads = []
      for a in random.sample(self.agents, self.gsize):
        ## Should only start threads for the human agents
        if a.slow:
          t = threading.Thread(target=self.acceptvote_thread, args=(a, self.applications, votes))
          t.start()
          #print "Starting thread with apps:", [a.id for a in self.applications]
          mythreads.append(t)
        else:
          votes.append(a.acceptvote(self.applications))            
      for t in mythreads:
        t.join()
    else:
      votes = [a.acceptvote(self.applications) for a in self.agents]
    
    if not len(votes):
      print "ERROR: no votes received!"
      self.applications = []
      return
    if self.cfg._verbose > 3 and self.slow:
      print "Group", self.id, "receives votes:", [(a.id if a is not None else -1) for a in votes]
    
    # Tabulate the votes
    voted = {}
    for v in votes:
      voted[v] = voted.get(v,0)+1
    sortvotes = sorted(zip(voted.values(), voted.keys()))
    maxvotes = max(v for v,a in sortvotes)
    tops = [a for v, a in sortvotes if v == maxvotes]
    
    if self.cfg._verbose > 5:
      print "Group", self.id, "votes:", [(v, (a.id if a is not None else -1)) for v, a in sortvotes]
    
    if len(tops) == 1:
      pick = tops[0]
    else:
      pick = random.choice(tops)
    
    if pick != None:
      pick.notifyaccept(self)
      if self.cfg._verbose > 5:
        print "Group", self.id, "accepts", pick.id
      for a in self.agents:
        # Notify the group about the agent that is accepted
        a.notifygaccept(pick.id)
    else:
      for a in self.agents:
        # Notify the group that no one was accepted
        a.notifygaccept(-1)
      
    self.applications = []

  def considermerge(self):
    if self.cfg.bias:
      raise NotImplementedError("Propose does not work with bias yet!")
    # Find highest-value group to join
    if not len(self.acceptances):
      return
    task=self.cfg.task
    self.update()
    
    bestgroup = None
    utility = self.cfg.utility_groupmerge(self)

    bestgroup = self.cfg.utility_tiebreaker(utility)
      
    if bestgroup is not None:
      if self.cfg._verbose > 5:
        print "Group", self.id, "merging with group", bestgroup.id
      while len(self.agents):
        self.agents[len(self.agents)-1].switchgroup(bestgroup)
      bestgroup.finishmerge()
        
    self.acceptances = []

  def notifyaccept(self, group):
    self.acceptances.append(group)

  def notifygaccept(self, aid):
    for a in self.agents:
      a.notifygaccept(aid)
  
  def notifyjoin(self, aid, add=True):
    for a in self.agents:
      a.notifyjoin(aid, add)

  def finishmerge(self):
    self.acceptances = []

  def expelvote_thread(self, a, votes):
    vote = a.expelvote()
    votes.append(vote)

  def expel_agent(self):
    if self.gsize == 1:
      return None
    task = self.cfg.task
    self.update()
    nowpay = self.nowpay
    
    badagent = None
    
    # Have each member vote on who to accept (-1 means accept no one)
    votes = []
    if self.cfg._threaded_sim:
      mythreads = []
      for a in random.sample(self.agents, self.gsize):
        ## Should only start threads for the human agents
        if a.slow:
          t = threading.Thread(target=self.expelvote_thread, args=(a, votes))
          t.start()
          mythreads.append(t)
        else:
          votes.append(a.expelvote())
      for t in mythreads:
        t.join()
    else:
      votes = [a.expelvote() for a in self.agents]
    
    if not len(votes):
      print "ERROR: no votes received!"
      self.applications = []
      return
    if self.cfg._verbose > 3 and self.slow:
      print "Group", self.id, "receives expel votes:", [(a.id if a is not None else -1) for a in votes]
    
    # Tabulate the votes
    voted = {}
    for v in votes:
      voted[v] = voted.get(v,0)+1
    sortvotes = sorted(zip(voted.values(), voted.keys()))
    maxvotes = max(v for v,a in sortvotes)
    tops = [a for v, a in sortvotes if v == maxvotes]
    
    if self.cfg._verbose > 5:
      print "Group", self.id, "expel votes:", [(v, (a.id if a is not None else -1)) for v, a in sortvotes]
    
    if len(tops) == 1:
      pick = tops[0]
    else:
      pick = random.choice(tops)
    
    if pick != None:
      if self.cfg._verbose > 5:
        print "Group", self.id, "expels", pick.id
      for a in self.agents:
        # Notify the group about the agent that joined
        a.notifyjoin(pick.id, add=False)    ## TEMPORARY: should probably be "notifygexpel"
      return pick
    else:
      for a in self.agents:
        # Notify the group about the agent that joined
        a.notifyjoin(-1, add=False)
      return None

  def postprocess(self):
    pass

  def findnbrgroups(self):
    nbrs = {}
    for a in self.agents:
      a.addnbrgroups(nbrs)
    return nbrs
    #adjacent_nodes = set(v for u,v in nx.edge_boundary(G, g['agents']))
    #nbgroups = set(G.node[n]['group'] for n in adjacent_nodes)
    #adjacent_nodes = node_boundary(self.G, [a.id for a in self.agents])
    #return nbrgroups  

  def printgroup(self):
    aids = ""
    for a in self.agents:
      aids += str(a.id) + " "
    print "Group", str(self.id)
    print "Agents:", aids
    print "Skills:", self.skills
    
  def reset(self):
    self.skills = np.zeros(self.cfg.nskills, dtype='int') #[0]*self.cfg.nskills
    self.nskills = self.cfg.nskills
    self.agents = []
    self.applications = []
    self.acceptances = []
    self.gsize = 0
    self.nowpay = 0
    self.worth = 0
