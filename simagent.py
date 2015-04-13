#
# simagent.py - provides simulated agents for team formation
# 
# Copyright (C) 2015  Nathan Dykhuis
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.
#
"""Defines simulated agents that can play Team Formation.

Includes DumbAgent which decides randomly, and greedy SimAgent.
"""

import random
import time

from agentgroup import Agent, UltAgent
 
class DumbAgent(Agent, UltAgent):
  """Barebones agent that makes all decisions randomly."""
  
  def __init__(self, cfg, adat=None, skills=None, aid=None):
    """Sets self.dumb to True"""
    super(DumbAgent, self).__init__(cfg, adat, skills, aid)
    self.dumb = True
  
  def propose(self):
    """Randomly chooses 0 to n groups to apply to."""
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    if not len(nbrgroups):
      return
    
    npropose = random.randrange(0, len(nbrgroups))
    proposes = random.sample(nbrgroups, npropose)
    
    for g in proposes:
      g.takeapplication(self)
    
  def acceptvote(self, applicants):
    """Randomly chooses from applicants, or None"""
    return random.choice(applicants + [None])
    
  def consider(self):
    """Randomly chooses a group to join, or None"""
    bestgroup = random.choice(self.acceptances+[None])
    
    if bestgroup is not None:
      self.switchgroup(bestgroup)
      
    self.acceptances = []
  
  def expelvote(self):
    """Randomly chooses an agent to expel, or None"""
    return random.choice(self.group.agents + [None])
  
  def postprocess(self, globalpay=None):
    """Does nothing"""
    pass

  def publicgoods(self, pgdict, potmult):
    """Contributes a random amount from 0 to self.nowpay"""
    self.update()
    nowpayint = int(self.nowpay)
    #return random.randint(0, int(self.nowpay))
    contrib = random.randint(0, nowpayint)
    pgdict[self] = (contrib, nowpayint-contrib)
  
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, potpay, teampays):
    """Sets self.pgpay to keep + nowpay"""
    self.pgpay = keep+potpay


class SimAgent(Agent, UltAgent):
  """Greedy agent that chooses the option of greatest pay at each step.
  
  At every step, choose the option that pays the most. 
  In the case of ties, break ties randomly (unless social_sim_agents set).
  If no group pays more, stay with current group.
  
  During public goods, contribute according to self.disposition.
  
  Rate the other agents by transforming 0-100% contributions to 1-5 scale,
  with some noise and probability of actually posting the rating.
  
  Uses configuration options:
    delay_sim_agents, _agent_delays, _agent_delay_dev: 
      Take real time making decisions to emulate human behavior
    agent_memory, agent_mem_threshold, agent_mem_decay:
      Stop applying to groups after repeated rejections with no change
    social_sim_agents, social_learning_rate:
      Expel or refuse to accept agents based on past contributions
    pg_contribrange:
      How much to contribute based on disposition
  """
  
  def __init__(self, cfg, adat=None, skills=None, aid=None):
    super(SimAgent, self).__init__(cfg, adat, skills, aid)
    
    if self.cfg.agent_memory:
      self.initmem()
      
    self.pgmem = {}         # Memory of what other agents have contributed
      
    if self.cfg.delay_sim_agents:
      self.slow = True
      self.tf_delay = self.tf_delay_real
    else:
      self.tf_delay = self.tf_delay_null
      
    self.disposition = None
  
  def initmem(self):
    """Initialize memory (for cfg.agent_memory)
    
    Stop repeating an unsuccessful action after a few tries,
    unless something changes.
    """
    self.proposemem = {}
    self.votemem = {}
    self.joinmem = {}
    self.expelmem = {}
  
  def reset(self):
    super(SimAgent, self).reset()
    
    if self.cfg.agent_memory:
      self.initmem()

  def tf_delay_null(self, stage):
    """Dummy function for no delay"""
    pass

  def tf_delay_real(self, stage):
    """Wait based on times defined in cfg._agent_delays for stage"""
    #print "tf_delay", self.id
    if self.cfg._agent_delays[stage] and (self.id < self.cfg.delay_n_sims or not self.cfg.delay_n_sims):
      time.sleep(max(random.gauss(self.cfg._agent_delays[stage], self.cfg._agent_delay_dev[stage]), 0.25))

  def switchgroup(self, newgroup):
    """Switch group, and reset memory (because something changed"""
    super(SimAgent, self).switchgroup(newgroup)
    if self.cfg.agent_memory:
      # Reset some memories since we're in a new group now
      self.proposemem = {}
      self.votemem = {}
      self.expelmem = {}
  
  def do_mem(self, nprev):
    """Decide whether to do an action, based on the number of times 
       action was previously done.
       
    Likelihood of doing the action decays after cfg.agent_mem_threshold
    by cfg.agent_mem_decay to the power of number of steps past threshold.
    """
       
    cfg = self.cfg
    return (nprev < cfg.agent_mem_threshold) or (random.random() < cfg.agent_mem_decay**(nprev-cfg.agent_mem_threshold))
  
  def propose(self):
    """Look at all of the neighboring groups and propose 
       to the ones that improve pay."""
    task=self.cfg.task
    self.update()
    
    self.tf_delay('propose')
    
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
      newskills = g.withskills(self)
      if self.cfg.bias:
        alist = [a.id for a in g.agents]+[self.id]
        self.logp(("agent", self.id, "in group", self.group.id, "proposing to", g.id), 6)
        #if task(newskills)*np.mean([self.bias.get(n, 1.0) for n in alist])/(len(alist)+1) >= self.nowpay:
        if task(newskills)/(len(alist)+1)*self.biasavg(alist) >= self.nowpay:
          g.takeapplication(self)
      else:
        gpay = task(newskills)/(g.gsize+1)
        if gpay > self.nowpay and totalweights.get(g.id, 0) >= 1:
          #if self.cfg._verbose > 5:
          #  print "agent", self.id, "in group", self.group.id, "proposing to", g.id
          if not self.cfg.agent_memory or self.do_mem(self.proposemem.get((g, gpay),0)):
            g.takeapplication(self)
            
            if self.cfg.agent_memory:
              self.proposemem[(g,gpay)] = self.proposemem.get((g,gpay),0) + 1

  def acceptvote(self, applicants):
    """Look at all applicants, and accept one that improves pay most.
    
    With social_sim_agents, refuse to accept agents who contribute less
    than my minimum contribution level, and rank agents by contribution.
    In absence of contribution memory, use global ratings information.
    """
    
    self.update()
    
    self.tf_delay('acceptvote')

    task = self.cfg.task
    nowpay = self.nowpay
    
    bestagent = None
    if self.cfg.social_sim_agents:
      #pay, memory, random, agent
      nowgsize = self.group.gsize
      if self.disposition == 'conditional':
        clow = self.pgmem.get(self.id, 0.5)+((random.random()-0.5)*self.cfg.conditional_variance)
      else:
        clow, chigh = self.cfg.pg_contribrange[self.disposition]
      utility = [(task(self.group.withskills(a))/(nowgsize + a.gsize) - nowpay, 
                  self.pgmem.get(a.id, (self.global_ratings.get(a.id, 1)-1)/4.0)-clow,   # If no memory, use scaled global rating
                  #self.pgmem.get(a.id, self.cfg.default_assumed_contrib)-clow, 
                  #self.global_ratings.get(a.id, 0), 
                  random.random(), a) for a in self.group.applications]
    else:
      utility = self.cfg.utility_group(self.group)

    if self.cfg.agent_memory:
      # Remove all agents who I've voted for more than x times
      utility = [u for u in utility if self.do_mem(self.votemem.get((u[-1],u[0]),0))]
      if not len(utility):
        return None


    bestagent = self.cfg.utility_tiebreaker(utility)
  
    if bestagent is not None:
      self.logp(("Agent", self.id, "voting for agent", bestagent.id), 6)

    if self.cfg.agent_memory and bestagent is not None:
      # Increment counter of number of times we've voted for this agent
      bautil = [u[0] for u in utility if u[-1] == bestagent][0]
      self.votemem[(bestagent,bautil)] = self.votemem.get((bestagent, bautil), 0) + 1

    return bestagent
      

  def consider(self):
    """Join the highest-value group, or stay in the case of a tie."""
    task=self.cfg.task
    
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
      self.logp(("Agent", self.id, "switching to", bestgroup.id, "  Utility:", [u[:-1]+(u[-1].id,) for u in utility]),6)
      
    self.acceptances = []
  
  
  def expelvote(self):
    """Expel any agent that reduces pay, or makes low contributions.
    
    Only consider contributions if social_sim_agents is set.
    """
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
        (max(0, (task(myg.withoutskills(agent))/(myg.gsize-1) - nowpay)), # Always expel agents that lower pay, but keep the option open to expel ones that raise pay
        (clow+chigh)*0.5 - self.pgmem.get(agent.id,chigh) - random.random(), # Probability to expel agents that contrib less than my average
        agent)
        for agent in myg.agents if agent != self]
      worstagent = self.cfg.utility_tiebreaker(utilities)
      return worstagent
    else:
      utilities = [(task(myg.withoutskills(agent))/(myg.gsize-1) - nowpay, random.random(), agent) for agent in myg.agents if agent != self]
      worstagent = self.cfg.utility_tiebreaker(utilities)
      return worstagent
      
  
  def postprocess(self, globalpay=None):
    """Evaluate the results of team formation and public goods
    
    If cfg.strengthen_teams or cfg.rewire_discontent:
      Compare my pay to global pay for agents with my skills.
      Strengthen or weaken connection weight to teammates based on pay.
    (these cases are not currently in use)
    """
    
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
    
    self.leftovers = self.maxweight - sum(dat['weight'] for dat in G[self.id].itervalues())
    
    if not len(nbrs):
      self.logp(("ERROR: node",self.id,"has no neighbors!"), -1)
      #return
    
    if globalpay is not None:
      mypay = self.nowpay
      avgpay = globalpay[tuple(self.skills)]
      happiness_threshold = 0.75
    
    ### Below code is not currently in use in experiments:
    
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
      
      self.logp((self.id, 'removes', movenbrs))
      
    if self.leftovers >= 1.0:
      # move it to a random person in the network
      newnbr = random.choice(G.nodes())
      G.add_edge( self.id, newnbr, weight=self.leftovers )
      self.leftovers = 0
      
      self.logp((self.id, 'connects to', newnbr, "(maxweight", self.maxweight, ")"))
      ## ISSUE: no one will "listen to" this neighbor because they don't have enough of a connection to them!
    
    #self.neighbors()
    ## PROBLEM:  having agents at both ends of an edge edit the weight messes up the total weight (social bandwidth) for the agents
    ##   Should we make this a digraph? Or is there some other way to fix this?
    

  def publicgoods(self, pgdict, potmult):
    """Return a contribution for public goods by setting it in pgdict.
    
    Contribute based on self.disposition:
      'conditional' contribute the expected average for the team, plus noise.
      all others contribute based on cfg.pg_contribrange
    
    Does not currently consider potmult.
    
    Returns:
      sets pgdict[self] = (amount contributed, amount kept)
    """
    self.update()
    nowpayint = int(self.nowpay)
    
    self.tf_delay('publicgoods')
    
    if self.disposition == 'conditional':
      #othercontribs = self.pgmem.values()  # This would include all the other agents...
      othercontribs = [self.pgmem[a.id] for a in self.group.agents if a.id in self.pgmem and a.id != self.id]
      if len(othercontribs):
        avgcontrib = sum(othercontribs)/len(othercontribs)
        mypctcontrib = avgcontrib + ((random.random()-0.5)*self.cfg.conditional_variance)
        mypctcontrib = min(max(mypctcontrib,0),1)   # Keep in 0,1 range
      else:
        mypctcontrib = random.random()
      contrib = int(round(mypctcontrib*nowpayint))
    else:
      clow, chigh = self.cfg.pg_contribrange[self.disposition]
      contrib = random.randint(int(clow*nowpayint), int(chigh*nowpayint))
      #return contrib
    
    pgdict[self] = (contrib, nowpayint-contrib)
    
  
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, potpay, teampays):
    """Add pay and keep track of contribution statistics.
    
    Set self.pgpay to my total pay for this round.
    Update self.pgmem with alpha-decay running average of contributions.
    """
    self.pgpay = privatepay+potpay
    
    prepay = startpay
    if prepay == 0:     # This may be a problem
      return
  
    ## Add payoff to my wealth
    newpay = privatepay + potpay
    #self.addpay(newpay)             ## Only useful in PPG
    
    # Keep a running mean of percent contribution for each neighbor
    alpha = self.cfg.social_learning_rate
    for aid,(contrib, keep) in teampays.iteritems():
      pctcontrib = 0 if (contrib + keep) == 0 else float(contrib) / (contrib + keep)
      if aid in self.pgmem:
        self.pgmem[aid] = (alpha*pctcontrib + (1.0-alpha)*self.pgmem[aid])
      else:
        self.pgmem[aid] = pctcontrib

  def getratings(self):
    """Calculate ratings for the other agents and return them.
    
    Compute rating by mapping past average contributions (0 to 100%)
    to the 1-5 rating scale, and adding +- half a rating of noise.
    
    Agent is more likely to post extreme ratings (1s or 5s).
    
    Note that the ratings will change each time this function is called.
    Also note that this function has the ability to NOT return a rating
    for a previously-rated agent, which human players cannot do.
    """
    
    ratings = {}
    #clow, chigh = self.cfg.pg_contribrange[self.disposition]
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
  
  def updateratings(self, ratings):
    """Update my knowledge of the public ratings"""
    self.global_ratings = ratings
