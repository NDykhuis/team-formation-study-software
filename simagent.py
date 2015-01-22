from configuration import *
from agentgroup import *
 
class dumbagent(agent, ultagent):
  def __init__(self, cfg, adat=None, skills=None, aid=None):
    super(dumbagent, self).__init__(cfg, adat, skills, aid)
    self.dumb = True
  
  def propose(self):
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    if not len(nbrgroups):
      return
    
    npropose = random.randrange(0, len(nbrgroups))
    proposes = random.sample(nbrgroups, npropose)
    
    for g in proposes:
      g.takeapplication(self)
    
  def acceptvote(self, applicants):
    return random.choice(applicants + [None])
    
  def consider(self):
    bestgroup = random.choice(self.acceptances+[None])
    
    if bestgroup is not None:
      self.switchgroup(bestgroup)
      
    self.acceptances = []
  
  def expelvote(self):
    return random.choice(self.group.agents + [None])
  
  def postprocess(self, globalpay=None):
    pass

  def publicgoods(self, pgdict):
    self.update()
    nowpayint = int(self.nowpay)
    #return random.randint(0, int(self.nowpay))
    contrib = random.randint(0, nowpayint)
    pgdict[self] = (contrib, nowpayint-contrib)
  
  def publicgoods_postprocess(self, newpay, teampays):
    self.pgpay = newpay


class simagent(agent, ultagent):
  def __init__(self, cfg, adat=None, skills=None, aid=None):
    super(simagent, self).__init__(cfg, adat, skills, aid)
    
    if self.cfg.agent_memory:
      self.initmem()
      
    self.pgmem = {}         # Memory of what other agents have contributed
      
    if self.cfg.delay_sim_agents:
      self.slow = True
    else:
      self.tf_delay=self.tf_delay_null
  
  def initmem(self):
    self.proposemem = {}
    self.votemem = {}
    self.joinmem = {}
    self.expelmem = {}
  
  def reset(self):
    super(simagent, self).reset()
    
    if self.cfg.agent_memory:
      self.initmem()

  def tf_delay_null(self, stage):
    pass

  def tf_delay(self, stage):
    #print "tf_delay", self.id
    if self.cfg._agent_delays[stage] and (self.id < self.cfg.delay_n_sims or not self.cfg.delay_n_sims):
      time.sleep(max(random.gauss(self.cfg._agent_delays[stage], self.cfg._agent_delay_dev[stage]), 0.25))

  def switchgroup(self, newgroup):
    super(simagent, self).switchgroup(newgroup)
    if self.cfg.agent_memory:
      # Reset some memories since we're in a new group now
      self.proposemem = {}
      self.votemem = {}
      self.expelmem = {}
  
  # decides whether to do an action, based on the number of times action was previously done
  def do_mem(self, nprev):
    cfg = self.cfg
    return (nprev < cfg.agent_mem_threshold) or (random.random() < cfg.agent_mem_decay**(nprev-cfg.agent_mem_threshold))
  
  def propose(self):
    task=self.cfg.task
    self.update()
    
    self.tf_delay('propose')
    
    # Look at all of the neighboring groups and propose to the ones that improve pay
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    #for n in self.nbrs:     
    #  nbrgroups.add(n.group)
    
    totalweights = {}
    numnbrs = {}
    for nbr, dat in self.cfg._Gptr[self.id].iteritems():
      g = self.cfg._agentdict[nbr].group.id
      totalweights[g] = totalweights.get(g,0.0) + dat['weight']
      numnbrs[g] = numnbrs.get(g,0) + 1
    #print totalweights
    
    for g in nbrgroups:
      #g = n.group
      #if g == self.group:
      #  continue
      newskills = g.withagent(self)
      if self.cfg.bias:
        alist = [a.id for a in g.agents]+[self.id]
        if self.cfg._verbose > 5:
          print "agent", self.id, "in group", self.group.id, "proposing to", g.id
        #if task(newskills)*np.mean([self.bias.get(n, 1.0) for n in alist])/(len(alist)+1) >= self.nowpay:
        if task(newskills)*self.biasavg(alist) >= self.nowpay:
          g.takeapplication(self)
      else:
        gpay = task(newskills)
        if gpay > self.nowpay and totalweights.get(g.id, 0) >= 1:
          #if self.cfg._verbose > 5:
          #  print "agent", self.id, "in group", self.group.id, "proposing to", g.id
          if not self.cfg.agent_memory or self.do_mem(self.proposemem.get((g, gpay),0)):
            g.takeapplication(self)
            
            if self.cfg.agent_memory:
              self.proposemem[(g,gpay)] = self.proposemem.get((g,gpay),0) + 1

  def acceptvote(self, applicants):
    ### COPY in code from agentgroup group consider
    self.update()
    
    self.tf_delay('acceptvote')

    task = self.cfg.task
    nowpay = self.nowpay
    
    bestagent = None
    if self.cfg.social_sim_agents:
      #pay, memory, random, agent
      nowgsize = self.group.gsize
      clow, chigh = self.cfg.pg_contribrange[self.disposition]
      utility = [(task(self.group.withagent(a)) - nowpay, self.pgmem.get(a.id, 1.0)-clow, random.random(), a) for a in self.group.applications]
    else:
      utility = self.cfg.utility_group(self.group)

    if self.cfg.agent_memory:
      # Remove all agents who I've voted for more than x times
      utility = [u for u in utility if self.do_mem(self.votemem.get((u[-1],u[0]),0))]
      if not len(utility):
        return None


    bestagent = self.cfg.utility_tiebreaker(utility)
  
    if bestagent is not None and self.cfg._verbose > 5:
        print "Agent", self.id, "voting for agent", bestagent.id

    if self.cfg.agent_memory and bestagent is not None:
      # Increment counter of number of times we've voted for this agent
      bautil = [u[0] for u in utility if u[-1] == bestagent][0]
      self.votemem[(bestagent,bautil)] = self.votemem.get((bestagent, bautil), 0) + 1

    return bestagent
      

  def consider(self):
    task=self.cfg.task
    
    # Find highest-value group to join
    if not len(self.acceptances):
      return
    self.update()
    
    self.tf_delay('join')
    
    bestgroup = None
    utility = self.cfg.utility_agent(self)
    # Accept if we find a positive dimension before we find a negative dimension
    # (each dimension strictly dominates the one beneath)
    
    bestgroup = self.cfg.utility_tiebreaker(utility)
  
    if bestgroup is not None:
      self.switchgroup(bestgroup)
      if self.cfg._verbose > 5:
        print "Agent", self.id, "switching to", bestgroup.id, "  Utility:", [u[:-1]+(u[-1].id,) for u in utility]
      
    self.acceptances = []
  
  
  def expelvote(self):
    task = self.cfg.task
    self.update()
    
    self.tf_delay('expelvote')
    
    nowpay = self.nowpay
    myg = self.group
    
    #for agent in random.sample(myg.agents, myg.gsize):
    #  if agent == self:
    #    continue
    if self.cfg.social_sim_agents:
      clow, chigh = self.cfg.pg_contribrange[self.disposition]
      
      # Expel agents that contrib less than me in PG (first pass at AI)
      utilities = [
        (max(0, (task(myg.withoutagent(agent)) - nowpay)), # Always expel agents that lower pay, but keep the option open to expel ones that raise pay
        (clow+chigh)*0.5 - self.pgmem.get(agent.id,chigh) - random.random(), # Probability to expel agents that contrib less than my average
        agent)
        for agent in myg.agents if agent != self]
      worstagent = self.cfg.utility_tiebreaker(utilities)
      return worstagent
    else:
      utilities = [(task(myg.withoutagent(agent)) - nowpay, random.random(), agent) for agent in myg.agents if agent != self]
      worstagent = self.cfg.utility_tiebreaker(utilities)
      return worstagent
    
    # Old code; use new utility system instead
    #for agent in random.sample(myg.agents, myg.gsize):
      #if agent == self:
        #continue
      #if self.cfg.bias:
        #newpay = task(myg.withoutagent(agent))
        #paysans = float(sum([a.nowpaycalc(newpay, delagent=agent) for a in myg.agents]))
      #else:
        #paysans = task(myg.withoutagent(agent))
      #if paysans > nowpay:
        #return agent
      #else:
        #return None
  
  
  def postprocess(self, globalpay=None):
    # strengthen/weaken connections based on payoff
    cfg = self.cfg
    G = cfg._Gptr
    self.update()
    #self.neighbors()
    self.nbrs = set(self.cfg._agentdict[aid] for aid in G[self.id].iterkeys())
    teammates = set(a.id for a in self.group.agents)
    teammates.remove(self.id)
    #if not len(teammates):
    #  return
    nbrs = set(a.id for a in self.nbrs)
    
    ## Add payoff to my wealth
    self.addpay(self.nowpay)
    
    
    self.leftovers = self.maxweight - sum(dat['weight'] for dat in G[self.id].itervalues())
    
    if not len(nbrs):
      print "ERROR: node",self.id,"has no neighbors!"
      #return
    
    if globalpay is not None:
      mypay = self.nowpay
      avgpay = globalpay[tuple(self.skills)]
      happiness_threshold = 0.75
    
    ## IF WE'RE HAPPY WITH OUR TEAM:
    if cfg.strengthen_teams and (globalpay is None or not cfg.rewire_discontent or mypay >= avgpay*happiness_threshold) and len(teammates):
      # Somehow distribute weight from non-team neighbors to team neighbors
      #print self.leftovers
      available = self.maxweight
      zweight = {'weight':0.0}
      weights = { a:(G.get_edge_data(self.id,a,default=zweight)['weight']) for a in (teammates | nbrs) }   # All the nodes you know or interacted with
      lr = self.cfg.weight_learning_rate #* 0.5      # divide by two because BOTH agents do this same thing 
      addamount = [0.0, (lr * available+self.leftovers) / len(teammates)]
      #print "Before:", sum(weights.values()), self.totalweight
      for n,oldweight in weights.iteritems():
        weights[n] = (1-lr)*oldweight + addamount[n in teammates]
      
      #print "After:", sum(weights.values()), self.totalweight
      for a,w in weights.iteritems():
        try:
          G[self.id][a]['weight'] = w
        except KeyError:
          G.add_edge(self.id, a, weight=w)
          #self.nbrs.add(self.cfg._agentdict[a])
        
      # if there are any connections that are too weak, consider rewiring
      removenbrs = [a for a,w in weights.iteritems() if w < self.cfg.weak_threshold]
      G.remove_edges_from( (self.id, a) for a in removenbrs )
      
      ## Need to redistribute this weight back to the real teammates
      #self.leftovers = sum(w for w in weights.values() if w < self.cfg.weak_threshold)
      #print self.leftovers
    
    ## OTHERWISE, LOOK FOR NEW CONNECTIONS
    elif cfg.rewire_discontent:
      # find my weakest connection 
      zweight = {'weight':0.0}
      #weights = { a:(G.get_edge_data(self.id,a,default=zweight)['weight']) for a in nbrs }   # All the nodes you know
      weights = [ ((G.get_edge_data(self.id,a,default=zweight)['weight']), a) for a in nbrs ]   # All the nodes you know
      
      moveweight = 0
      #moveweight += self.leftovers
      #self.leftovers = 0
      
      movenbrs = []
      
      while moveweight < 1.0 and len(weights):
        mins = [(w, n) for w,n in weights if w == min(weights)[0]]
        minwght, minnbr = random.choice(mins)
        weights.remove( (minwght, minnbr) )
        moveweight += minwght
        movenbrs.append(minnbr)
      
      # remove the weak connection
      for minnbr in movenbrs:
        G.remove_edge( self.id, minnbr )
      
      self.leftovers += moveweight
      
      print self.id, 'removes', movenbrs
      
    if self.leftovers >= 1.0:
      # move it to a random person in the network
      newnbr = random.choice(G.nodes())
      G.add_edge( self.id, newnbr, weight=self.leftovers )
      self.leftovers = 0
      
      print self.id, 'connects to', newnbr, "(maxweight", self.maxweight, ")"
      ## ISSUE: no one will "listen to" this neighbor because they don't have enough of a connection to them!
    
    #self.neighbors()
    ## PROBLEM:  having agents at both ends of an edge edit the weight messes up the total weight (social bandwidth) for the agents
    ##   Should we make this a digraph? Or is there some other way to fix this?
    

  def publicgoods(self,pgdict):
    self.update()
    if self.cfg.persistent_pubgoods:
      nowpayint = int(self.totalpay)
    else:
      nowpayint = int(self.nowpay)
    
    self.tf_delay('publicgoods')
    
    clow, chigh = self.cfg.pg_contribrange[self.disposition]
    contrib = random.randint(int(clow*nowpayint), int(chigh*nowpayint))
    
    #if self.cfg.persistent_pubgoods:
    #  self.addpay(-contrib)     # Remove the contribution from my total pay

    #return contrib
    pgdict[self] = (contrib, nowpayint-contrib)
  
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, potpay, teampays):
    ## newpay === keep + potpay
    self.pgpay = privatepay+potpay
    
    prepay = startpay
    if prepay == 0:     # This may be a problem
      return
  
    print "Agent", self.id, "has", self.totalpay, "nowpay", self.nowpay, "newpay", newpay
    
    ## Add payoff to my wealth
    newpay = privatepay + potpay
    if self.cfg.persistent_pubgoods:
      self.addpay(newpay-keep)
    else:
      self.addpay(newpay)
    
    # Keep a running mean of percent contribution for each neighbor
    alpha = self.cfg.social_learning_rate
    for aid,(contrib, keep) in teampays.iteritems():
      pctcontrib = 0 if (contrib + keep) == 0 else float(contrib) / (contrib + keep)
      if aid in self.pgmem:
        self.pgmem[aid] = (alpha*pctcontrib + (1.0-alpha)*self.pgmem[aid])
      else:
        self.pgmem[aid] = pctcontrib

  def getratings(self):
    ratings = {}
    clow, chigh = self.cfg.pg_contribrange[self.disposition]
    for aid, pctcontrib in self.pgmem.iteritems():
      #rating = min(max(int(pctcontrib/chigh*4.0+1),1),5)   # Fancy version
      #rating = int(pctcontrib*4.0+1)                       # Simple version
      noise = random.random()-0.5   # Half a rating
      rating = int(min(max(pctcontrib*4.0+1+noise, 1),5))    # Noisy version
      
      # More likely to post rating if high or low
      probs = [99, 0.8, 0.5, 0.25, 0.5, 0.8]    # Can't rate zero; ratings can be 1-5
      if random.random() < probs[rating]:
        ratings[aid] = rating
    return ratings
  
  
