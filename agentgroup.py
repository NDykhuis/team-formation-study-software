#
# agentgroup.py - base classes for implementing agents and groups
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
"""Defines base classes for implementing agents and groups.

Includes all classes necessary to make agents for team formation and ultimatum,
as well as groups for team formation.
"""

import random
import threading
import numpy as np
import time

from configuration import Configuration

class Actor(object):
  """Base class for actions required to play Team Formation .
     Parent of Agent and Group classes."""
  skills = []
  gsize = 0
  idcounter = 0
  def propose(self):
    """Should look at n.group for n in neighbors, and call
       n.group.takeapplication() to make any desired proposals"""
    pass
  def acceptvote(self, applicants):
    """Should look at agents in applicants, and return one of them,
       or None to accept no one."""
    pass
  def consider(self):
    """Should look at groups in self.acceptances and call
       self.switchgroup(g) for any group to join"""
    pass
  def reset(self):
    """Should reset simulation-specific parameters, such as group, pay, etc."""
    pass

  def log(self, message, level=5):
    """Log a message to the server console, based on _verbose cfg option.
       Converts its argument to a string before printing."""
    if level <= Configuration._verbose:
      print str(message)
  
  def logp(self, messagetuple, level=5):
    """Log a message to the server console, based on _verbose cfg option.
       Takes a tuple of message elements, and joins them before printing."""
    if level <= Configuration._verbose:
      print ' '.join(str(s) for s in messagetuple)


class UltAgent(object):
  """Base class with functions necessary for playing Ultimatum.
  
  Methods contain just enough code to play Ultimatum randomly
  based on offer distribution defined by initialization parameters;
  can be overridden in derived classes
  """
  def __init__(self):
    self.p1, self.p2, self.delaymean, self.delaysd = None
    self.random = None
  
  ## ULTIMATUM FUNCTIONS
  def ultimatum_init(self, distribution='normal', p1=5, p2=1, delaymean=5, delaysd=2):
    """Initialize parameters of offer distribution.
    
    Arguments:
      distribution: 'normal' or 'uniform'
      p1, p2: mean and sd of normal, or upper and lower bound of uniform
      delaymean, delaysd: time required to make decisions
    """
    self.p1, self.p2, self.delaymean, self.delaysd = p1, p2, delaymean, delaysd
    if distribution == 'normal':
      # p1 is mean, p2 is sd
      self.random = random.gauss
    elif distribution == 'uniform':
      # p1 is lower bound, p2 is upper
      self.random = random.randint
  
  def fake_wait(self):
    """Sleep to simulate time to decide, based on cfg.delay_sim_agents"""
    if Configuration.delay_sim_agents:
      time.sleep(max(random.gauss(self.delaymean, self.delaysd), 0))

  def ultimatum(self, other_player):
    """Notify this agent that they are playing Ultimatum with other_player."""
    pass
  
  def dictator(self, other_player):
    """Notify this agent that they are playing Dictator with other_player."""
    pass
  
  def ask_for_offer(self, other_player):
    """Request this player to make an offer to other_player.
    
    Returns:
      an offer amount between 0 and 10
    """
    offer = int(round(self.random(self.p1, self.p2), 0))
    offer = max(offer, 0)
    offer = min(offer, 10)
    
    print "Going to offer", offer
    self.fake_wait()
    print "Offering!"
    
    return offer
  
  def wait_offer(self, other_player):
    """Notify this agent to wait for an offer from other_player."""
    pass
  
  def decide_offer(self, other_player, amount):
    """Decide whether to accept an offer of amount from other_player.
       Accept the offer if it is the kind of offer this agent would make.
       (ex. Agents who offer 7 will accept 3, and vice-versa)
       
    Returns:
      boolean indicating whether offer was accepted
    """
    threshold = 10-int(round(self.random(self.p1, self.p2), 0))
    
    self.fake_wait()
    
    return (amount > threshold)
  
  def wait_decide(self, other_player):
    """Notify this agent to wait for other_player to decide on an offer"""
    pass
  
  def show_conclusion_u(self, other_player, amount, result, role):
    """Show conclusion of one round of Ultimatum with other_player
    
    Arguments:
      other_player: ID of other player (int)
      amount: amount that was offered (int)
      result: accept or reject (boolean)
      role: 0 if I made the offer, 1 if the other player did
    """
    pass
  
  def show_conclusion_d(self, other_player, amount, role):
    """Show conclusion of one round of Dictator with other_player
    
    Arguments:
      other_player: ID of other player (int)
      amount: amount that was offered (int)
      role: 0 if I made the offer, 1 if the other player did
    """
    pass

class Agent(Actor):
  """Base class for Team Formation individual agents.
  
  Includes methods for making decisions in Team Formation, as well as
  dealing with ratings, history, and pay calculations.
  
  Attributes:
    id: the agent's id (integer)
    group: reference to this agent's current Group
    nowpay: pay this agent would receive in the current group.
            This should stay updated by self.update()
    skills: list of the agent's skills (length==cfg.nskills)
    gsize: always 1, since this is a single agent
    slow: boolean; does this agent take time (seconds) to make decisions?
    dumb: boolean; does this agent always decide randomly?
    type: 'sim' or 'human'
  """
  def __init__(self, cfg, adat=None, skills=None, aid=None):
    self.cfg = cfg
    if adat is None:
      if aid is None:
        self.id = Agent.idcounter; Agent.idcounter += 1
      else:
        self.id = aid 
      if skills is None: 
        #skills=[0]*cfg.nskills
        skills = np.zeros(cfg.nskills, dtype='int')
      self.skills = np.array(skills)
      self.group = None
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
    self.nbrs = set()
    self.gsize = 1
    self.acceptances = []
    
    self.leftovers = 0
    
    self.worth = 0  # TEMPORARY
    
    self.slow = False   # For threading
    self.dumb = False
    self.type = 'sim'
    
    self.global_ratings = {}
    
  def randskills(self):
    """Assign a random set of skills to this agent"""
    nskills = len(self.skills)
    lev = random.randint(1, min(nskills, self.cfg.maxskills))
    #s = [1]*lev + [0]*(nskills-lev)
    skills = np.zeros(nskills, dtype='int')
    for _ in range(lev):
      skills[random.choice(nskills)] += 1
    #random.shuffle(s)
    self.skills = skills
  
  def randbiases(self):
    """Assign bias to each neighbor edge randomly"""
    for n in self.nbrs:
      #self.bias[n] = np.random.normal()    # does not use the same random seed
      # multiplier for utility of working with someone
      bias = random.triangular(1.0, self.cfg.biasrange, 1.0)
      bias = bias**random.choice((-1.0, 1.0))
      self.bias[n.id] = bias
  
  def update(self):
    """Update self.nowpay with pay in current group"""
    if self.cfg.bias:
      self.nowpay = self.nowpaycalc(self.cfg.task(self.group.skills))
    else:
      self.nowpay = self.cfg.task(self.group.skills)/self.group.gsize
    
  def nowpaycalc(self, pay, addagent=-1, delagent=-1):
    """Calculate current utility taking into account opinions of neighbors"""
    alist = [a.id for a in self.group.agents if a.id != delagent]
    if addagent != -1:
      alist += [addagent]
    #return pay*np.mean([self.bias.get(n, 1.0) for n in alist])/len(alist)
    return pay/(len(alist))*self.biasavg(alist)
  
  def biasavg(self, agents):
    """Get this agent's average bias (opinion) for a list of agents"""
    # one for average bias, other for fraction of pay
    return float(sum([self.bias.get(nid, 1.0) for nid in agents]))/(len(agents))
  
  def propose(self):
    """Should look at n.group for n in neighbors, and call
       n.group.takeapplication() to make any desired proposals"""
    pass

  def notifyaccept(self, group):
    """Notify this agent that it has been accepted by group"""
    self.acceptances.append(group)

  def acceptvote(self, applicants):
    """Should look at agents in applicants, and return one of them,
       or None to accept no one."""
    pass

  def consider(self):
    """Should look at groups in self.acceptances and call
       self.switchgroup(g) for any group to join"""
    pass

  def expelvote(self):
    """Should look at agents in self.group.agents and return one of them
       to expel, or None to expel no one."""
    pass
  
  def switchgroup(self, newgroup):
    """Remove this agent from its current group, and add it to newgroup"""
    if self.cfg._verbose > 3:
      print "Agent", self.id, "joining group", newgroup.id
    self.group.remove(self)
    self.group = newgroup
    newgroup.add(self)
    self.switches += 1
    self.update()
  
  def notifygaccept(self, aid):
    """Notify this agent that its group has voted to accept an agent.
       Argument: aid - integer ID of an agent"""
    pass
  
  def notifyjoin(self, aid, add=True, expel=False):
    """Notify this agent that an agent has joined, left, or been expelled."""
    pass
  
  def neighbors(self):
    """Set up self.nbrs with a list of neighbors based on the NetworkX
       graph stored in a Configuration._Gptr."""
    G = self.cfg._Gptr
    self.nbrs = set(self.cfg._agentdict[aid] for aid in G[self.id].iterkeys())
    self.totalweight = sum(dat['weight'] for dat in G[self.id].itervalues())
    
  def nbrweight(self):
    """Calculate the total weight on neighbor edges in the NetworkX graph
       stored in Configuration._Gptr. 
       Used to enforce social bandwidth limitations."""
    G = self.cfg._Gptr
    self.maxweight = sum(dat['weight'] for dat in G[self.id].itervalues())
 
  def addnbrgroups(self, nbrdict):
    """Add the groups of all my neighbors to the dictionary nbrdict
    Arguments:
      nbrdict: dictionary mapping group ID to Group object
    """
    for n in self.nbrs:
      nbrdict[n.group.id] = n.group
  
  def addnbr(self, nbr):
    """Add a neighbor to self.nbrs"""
    self.nbrs.add(nbr)

  def postprocess_iter(self):
    """Notify the agent that an iteration has finished, and do any
       necessary postprocessing."""
    pass

  def postprocess(self, globalpay=None):
    """Notify the agent that a round has finished, and do any
       necessary postprocessing.
    Argument: 
      globalpay: average pay for all agents with the same skillset"""
    pass
  
  def publicgoods(self, pgdict, potmult):
    """Decide how much to contribute in public goods game.
    
    Report two integers, contrib and keep, that add up to self.nowpay.
    Uses a dictionary to return an amount for threading compatibility.
    
    Arguments:
      pgdict: dictionary of agent ID -> (contrib, keep) tuples
      potmult: current pot multiplier, or (low, high) potential multipliers
               for alternative public goods
    Returns:
      Set pgdict[self] = (contrib, keep)"""
    pass
  
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, 
                              potpay, teampays):
    """Learn the results of publicgoods, and do any postprocessing.
    
    Arguments:
      startpay: how much pay I earned from working with this team (int)
      keep: how much pay I kept (int)
      contrib: how much pay I contributed (int)
      privatepay: how much pay I received on my own (float)
      potpay: how much pay I received from the shared public pot (float)
      teampays: agent ID -> (contrib, keep) dictionary for my team.
    """
    pass
    
  def getratings(self):
    """Return a dictionary of my ratings of the other agents.
    Dictionary maps agent ID (int) to my rating of that agent (int, 1-5)"""
    return {}
  
  def updatehistory(self, pghistory):
    """Update my known history of pubgoods contributions.
    Argument:
      pghistory: dictionary of agent ID -> list of previous contributions
    """
    pass
  
  def updateratings(self, ratings):
    """Update my knowledge of global ratings of the other agents.
    Argument:
      ratings: dictionary of agent ID -> average rating (float, 1-5)
    """
    pass
    
  def reset(self):
    """Reset all simulation-specific member variables."""
    if not self.cfg.keep_teams:
      self.group = None
    self.acceptances = []
    self.switches = 0
    self.gsize = 1      # for compatibility with group merging
    self.nowpay = 0
    self.neighbors()
    
    
class Group(Actor):
  """A Group is a collection of Agents
  
  Groups can accept or expel members. If cfg.groups_can_merge is set,
  groups can also act like an agent, and apply to merge with other groups.
  A group has the same attributes (from Actor class) as an Agent: 
  it has skills, a size, current pay, and can propose to join other groups.
  
  Note that the simplest group is a single agent.
  
  Attributes:
    id: ID of the group, set by default to first agent's ID (integer)
    skills: cumulative skills of the group (list of length nskills)
    agents: list of group members (Agent objects)
    gsize: number of members ( len(self.agents) )
    slow: boolean; one or more agents take real time to make decisions
    nowpay: pay of each individual agent in the group
  """
  
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
    """ Update all cached values, including gsize, slow, and nowpay"""
    self.worth = sum(a.worth for a in self.agents)
    self.gsize = len(self.agents)
    self.slow = any(a.slow for a in self.agents)
    try:
      if self.cfg.bias:
        nowearns = self.cfg.task(self.skills)
        self.nowpay = sum(a.nowpaycalc(nowearns) for a in self.agents)
        self.nowpay /= self.gsize
      else:
        self.nowpay = self.cfg.task(self.skills)/self.gsize
    except ZeroDivisionError:
      self.nowpay = 0

  def addfirst(self, agent):
    """Add the first agent to the group. Sets the agent's group variable"""
    agent.group = self
    self.add(agent)

  def add(self, agent):
    """Add an agent to this group, and update relevant values
       such as nowpay and skills.
       Also add network connections if cfg.fully_connect_groups is set.
    """
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
    """Remove an agent (if a member) from the group, and update values.
       If agent is not a member, do nothing.
    """
    if agent in self.agents:
      self.agents.remove(agent)
      self.skills = self.withoutskills(agent)
      self.update()
      self.notifyjoin(agent.id, add=False)

  def withskills(self, agent):
    """Return the group's cumulative skills plus the skills of agent"""
    #return [self.skills[i] + agent.skills[i] for i in range(self.nskills)]
    #print type(self.skills), type(agent.skills)
    return self.skills + agent.skills
  def withoutskills(self, agent):
    """Return the group's cumulative skills minus the skills of agent"""
    return self.skills - agent.skills

  def takeapplication(self, agent):
    """Receive an application to join from agent"""
    self.applications.append(agent)

  def propose(self):
    """Apply to all neighboring groups that increase pay (group merge)"""
    if self.cfg.bias:
      raise NotImplementedError("Propose does not work with bias yet!")
    if self.gsize == 1:
      return
    task = self.cfg.task
    nbrgroups = self.findnbrgroups()
    for g in nbrgroups.values():
      if g == self:
        continue
      newskills = g.withskills(self)
      if task(newskills)/(g.gsize+self.gsize) >= self.nowpay:
        #print "group", self.id, "proposing to", g.id
        g.takeapplication(self)

  def acceptvote_thread(self, a, applications, votes):
    """Function to take acceptvotes in separate threads."""
    vote = a.acceptvote(applications)
    votes.append(vote)

  def consider(self):
    """Consider all applications, and allow members to vote to accept one."""
    
    # This function handles both groups and agents in the groupmerge case
    if not len(self.applications):
      return
    
    # This speeds things up immensely in the complete graph!
    #self.applications = random.sample(self.applications, len(self.applications))
    # no longer necessary because of random value in the tiebreaking code
    
    self.update()
    
    # Have each member vote on who to accept (-1 means accept no one)
    votes = []
    if self.cfg._threaded_sim:
      mythreads = []
      for a in random.sample(self.agents, self.gsize):
        ## Should only start threads for the human agents
        if a.slow:
          t = threading.Thread(target=self.acceptvote_thread, 
                               args=(a, self.applications, votes))
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
      print "Group", self.id, "receives votes:", \
        [(a.id if a is not None else -1) for a in votes]
    
    # Tabulate the votes
    voted = {}
    for v in votes:
      voted[v] = voted.get(v, 0)+1
    sortvotes = sorted(zip(voted.values(), voted.keys()))
    maxvotes = max(v for v, a in sortvotes)
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
    """Consider all acceptances from other groups to merge, and merge
       if an offer improves pay"""
    if self.cfg.bias:
      raise NotImplementedError("Propose does not work with bias yet!")
    # Find highest-value group to join
    if not len(self.acceptances):
      return
    
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
    """Notify this group that it has been accepted to merge with group"""
    self.acceptances.append(group)

  def notifygaccept(self, aid):
    """Notify everyone in this group of the acceptance of an agent"""
    for a in self.agents:
      a.notifygaccept(aid)
  
  def notifyjoin(self, aid, add=True):
    """Notify everyone in this group that an agent has joined or left"""
    for a in self.agents:
      a.notifyjoin(aid, add)

  def finishmerge(self):
    """Complete a group merge by clearing out self.acceptances"""
    self.acceptances = []

  def expelvote_thread(self, a, votes):
    """Function to take expelvotes in separate threads."""
    vote = a.expelvote()
    votes[a] = vote

  def expel_agent(self):
    """Consider all members, and allow members to vote to expel one.
    
    Returns: an Agent to expel, or None
    """
    if self.gsize == 1:
      return None
    
    self.update()
    
    # Have each member vote on who to accept (-1 means accept no one)
    votes = {}
    if self.cfg._threaded_sim:
      mythreads = []
      for a in random.sample(self.agents, self.gsize):
        ## Should only start threads for the human agents
        if a.slow:
          t = threading.Thread(target=self.expelvote_thread, args=(a, votes))
          t.start()
          mythreads.append(t)
        else:
          votes[a] = a.expelvote()
      for t in mythreads:
        t.join()
    else:
      votes = {a:a.expelvote() for a in self.agents}
    
    voters = votes.keys()
    votes = votes.values()
    
    if not len(votes):
      print "ERROR: no votes received!"
      self.applications = []
      return
    if self.cfg._verbose > 3 and self.slow:
      #print "Group", self.id, "receives expel votes:", [(a.id if a is not None else -1) for a in votes]
      print "Group", self.id, "receives expel votes:", {v.id:(a.id if a is not None else -1) for v,a in zip(voters,votes)}
    
    # Master list of agents to expel
    expelees = []
    
    # If any agent votes for itself, make it leave the group
    newvotes = []
    for v, a in zip(votes, voters):
      if v != None and v.id == a.id:
        expelees.append(a)
      else:
        newvotes.append(v)  # If agent left the group, remove from the expel vote.
    votes = newvotes
    
    for a in self.agents:
      # Notify the group about agents that left
      for e in expelees:
        a.notifyjoin(e.id, add=False)
    
    # Tabulate the votes
    voted = {}
    for v in votes:
      voted[v] = voted.get(v, 0)+1
    sortvotes = sorted(zip(voted.values(), voted.keys()))
    maxvotes = max(v for v, a in sortvotes)
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
        # Notify the group about the agent that got expelled
        a.notifyjoin(pick.id, add=False, expel=True)    ## TEMPORARY: should probably be "notifygexpel"
      expelees.append(pick)
    else:
      for a in self.agents:
        # Notify the group that no one got expelled
        a.notifyjoin(-1, add=False, expel=True)
    
    return expelees

  def postprocess(self):
    pass

  def findnbrgroups(self):
    """Find all neighboring groups by gathering neighbors of every agent"""
    nbrs = {}
    for a in self.agents:
      a.addnbrgroups(nbrs)
    return nbrs
    #adjacent_nodes = set(v for u,v in nx.edge_boundary(G, g['agents']))
    #nbgroups = set(G.node[n]['group'] for n in adjacent_nodes)
    #adjacent_nodes = node_boundary(self.G, [a.id for a in self.agents])
    #return nbrgroups  

  def printgroup(self):
    """Print out ID, member IDs, and skills of this group"""
    aids = ""
    for a in self.agents:
      aids += str(a.id) + " "
    print "Group", str(self.id)
    print "Agents:", aids
    print "Skills:", self.skills
    
  def reset(self):
    """Reset the group - remove all members and reset skills"""
    self.skills = np.zeros(self.cfg.nskills, dtype='int') #[0]*self.cfg.nskills
    self.nskills = self.cfg.nskills
    self.agents = []
    self.applications = []
    self.acceptances = []
    self.gsize = 0
    self.nowpay = 0
    self.worth = 0

