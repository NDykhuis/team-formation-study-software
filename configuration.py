#
# configuration.py - holds all options and parameters for the simulation
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


import random
import numpy as np
import networkx as nx
import copy
import math

import sqlite3
    
PROTOCOL = 101
##   Setting this PROTOCOL flag will set several configuration options at once, for ease of experimentation
##   If it is not set, the default options in the configuration class will be used
##   PROTOCOL 0:  (non-social)
##     video, no ultimatum, play lottery, and disable ratings
##     70 minutes; 5 minutes margin
##   PROTOCOL 1:  (social, global ratings)
##     video, no ultimatum, play publicgoods and do ratings
##     70 minutes; 5 minutes margin
##   PROTOCOL 2:  (social, private ratings)
##     video, no ultimatum, play publicgoods and do ratings
##     70 minutes; 5 minutes margin
##   PROTOCOL 3:  (social, public ratings, alternate pubgoods multiplier)
##     video, no ultimatum, play publicgoods and do ratings
##     70 minutes; 5 minutes margin
##   PROTOCOL 98:  (testing video)
##     video, no ultimatum, play pubgoods and do ratings
##     10 minutes; 3 minutes margin
##   PROTOCOL 99:  (testing short)
##     no video, no ultimatum, play pubgoods and do ratings
##     1 minute; 3 minutes margin
##   PROTOCOL 100:  (automated)
##     10 minutes of sim agents only simulation; 10 rounds each.
##   PROTOCOL 101:  (sim human agents)
##     10 minutes of sim agents only simulation with humans; 10 rounds each.

class Configuration(object):
  """Stores configuration parameters for the simulation.
  
  Uses the unfortunate convention that a preceding _ means the variable
  will not be output to the database in the configuration dump.
  """
  
  n = 16           # Number of agents
  nhumans = 0      # Number of humans (set by simserver based on how many frontends connect)
  ndumb = 0        # Number of random agents (rather than rational)
  
  simhumans = True # Use experimental data to simulate human subjects
  simhuman_file = 'userdatatable.csv'
  
  exchange_rate = 15.0   # Divide sim-dollars by this to get real dollars
  
  _do_video = False
  _capture_screenshots = False

  _do_intro_sim = True
    
  _do_ultimatum = False
  ultimatum_niter = 2
  dicatator_niter = 1
  
  do_publicgoods = True
  #pubgoods_mult = 1.2
  pubgoods_mult = 25     # Percent the pot is increased
  hide_publicgoods = True
  pg_contribrange = {   # Percent to contribute in pubgoods, low to high
    'nice':(0.7, 1.0),
    'mean':(0.0, 0.25),
    'fair':(0.5, 0.8),
    'random':(0.0, 1.0)
  }
  conditional_variance = 0.1
  
  # Alternative pubgoods parameters
  alt_pubgoods = False   # Use alternative version of pubgoods
  ap_min_multiplier = 1.10
  ap_max_multiplier = 2.00
  ap_rating_intercept = 0.25
  ap_rating_slope = 0.50
  ap_multiplier_range = ap_max_multiplier-ap_min_multiplier
  
  def pubgoods_calc(self, pctcontribs, ratings):
    ## Description
    #
    # The multiplier for the Public Good Game is given by the following
    # functions:
    #
    # k(c,b) = b1 + b2/(1 + exp(-b3*c)),         [1]
    #
    # where "c" is percentage contribution, scaled so that the range (0,1)
    # becomes the range (-1.5, 1.5)
    # b1 and b2 are constants, s.t. b1 indicates the minimum value for the 
    # multiplier, and b2 + b1 indicates the maximum value for the multiplier.
    #
    # The coefficient b3 is a linear function of the ratings (from 0 to 4):
    #
    # b3(r,a) = a1 + a2*r;
    avg_pctcontrib = sum(pctcontribs)/len(pctcontribs)
    scale_pctcontrib = (avg_pctcontrib - 0.5)*3
    avg_rating = (sum(ratings)/len(ratings) if len(ratings) else 3) - 1
    rating_multiplier_term = self.ap_rating_intercept + self.ap_rating_slope * avg_rating
    multiplier = self.ap_min_multiplier + (self.ap_multiplier_range)/(1+math.exp(-rating_multiplier_term * scale_pctcontrib))
    return multiplier
  
  show_other_team_members = True
  
  do_ratings = True
  
  show_global_ratings = True
  show_nhistory = 0      # Set to zero to disable
  
  show_skills = False    # show skills to the player
  
  keep_teams = False     # After a simulation, keep the current teams
  
  agent_memory = True   ## TESTING - agents stop applying to groups that have rejected them
  agent_mem_threshold = 1
  agent_mem_decay = 0.5
  
  # Sim agents take real time to make their decisions 
  delay_sim_agents = True   ## SHOULD BE TRUE
  delay_n_sims = 8          # Add a delay to only the first n agents
  #_agent_delays = {'propose':2.5, 'acceptvote':1.5, 'join':1.0, 'expelvote':1.0, 'conclude':1.0, 'publicgoods':2.5}    # Arbitrary
  _agent_delays = {'propose':4.0, 'acceptvote':5.0, 'join':5.0, 'expelvote':3.0, 'conclude':3.0, 'publicgoods':10.0}    # Based on pilot data
  _agent_delay_dev = {'propose':2.0, 'acceptvote':2.5, 'join':1.5, 'expelvote':1.5, 'conclude':1.0, 'publicgoods':5.0}  # Approx as half the IQR
  
  social_sim_agents = True
  social_learning_rate = 0.66
  
  nsteps = 10      # Max number of iterations
  deaditers = 1     # How many iterations with no change before we stop

  _time_limit = 30    # hard time limit in minutes; sim will be cut off after the current iteration when this time expires
  _margin_time = 3    # start the last sim no later than this many minutes before end
  
  _decision_reminder = 45     # Highlight the submit button after this many seconds
  

  ## Params for automated simulation
  reset_graph_iters = 0     # Reset the graph after n iterations (0 is keep forever)
  _log_teamstatus = True
  percent_conditional = 0

  ## DISPLAY PARAMETERS
  _display_every_step = False
  _pause_every_step = False
  _pause_after_sim = False
  _draw_graph = False            # Controls graphical output
  _pause_graph = False
  _draw_graph_after_sim = False
  _verbose = 5                   # Controls print output (integer 0-n)
  #_output_by = "none"
  #_output_by = "simulation"  
  #_output_by = "agent"
  _output_by = "both"  
  #_all_agents_same = True
  _draw_grid = False
  _print_summary = True
  _print_group_summary = False

  delaytime = 0.25     # delay between iterations in seconds, for watching the sim

  _threaded_sim = True  # Start new threads for each agent when actions can be completed in parallel (turn on for human subjects)

  #skillseed = 12345     # Always init agent skills with this seed. Set to None for random.
  skillseed = None
  #graphseed = 12345
  graphseed = None
  #springseed = 12345
  springseed = None



  ### GRAPH OPTIONS
  ## These configuration options are mostly unused; see the "multiconfig" class, which is designed for running multiple simulations in a row with different parameters
  connections = 5
  max_connections = 8
  prob_rewire = 0.25
  graph_type = 'connected_watts_strogatz_graph'
  # see: http://networkx.github.com/documentation/latest/reference/generators.html
  
  graph_class = 'graph'
  _graph_constructor = nx.Graph
  #graph_class = 'digraph'
  #_graph_constructor = nx.DiGraph
  
  
  groups_can_merge = False
  expel_agents = False
  fully_connect_groups = False
  
  allow_leaving = True
  
  rewire_grid_graph = False
  strengthen_teams = False
  rewire_discontent = False
  
  ## Experimental; not for use
  bias = False
  biasrange = 4.0
  dynamic_graph = False
  weight_learning_rate = 0.25
  weak_threshold = 0.1
  
  
  
  ## TASK PARAMETERS
  
  # The number of types of skills
  # In the breadth-depth task, this approximately controls the size of groups
  nskills = 4
  maxskills = 1
  
  
  simnumber = 0
  _header = []      # Holds the sorted headings

  _taskdict = {}

  _dblog = None
  
  
  def __init__(self):
    self.task = self.nmemtask
    #self.task = self.bdtask
    #self.setupbdtask()
    self._Gptr = None
    self._agentdict = None
  
  def reset(self):
    #self.task = self.bdtask
    #self.setupbdtask()
    pass
  
  # This task rewards groups based only on how many members are on a team
  # Calculates number of members assuming that maxskills == 1
  # Team max size is given by nskills
  def nmemtask(self, skills):
    nmem = sum(skills)
    increward = 5
    npay = min(nmem, self.nskills)
    pay = npay * increward * (npay-1)   # (npay*increward) for each of the first (npay) members
    return float(pay)
  
  # Optimized function to answer the question:
  # How much pay for a given set of skills?
  def multitask(self, skills):
    # This task will payoff only if the team has all of the required skills
    tskills=tuple(skills)
    try:
      return self._taskdict[tskills]
    except KeyError:
      pay = float(max(self.singletask(skills, t[0], t[1]) for t in self.tasks))
      self._taskdict[tskills] = pay
      #payoffs = [self.singletask(skills, t[0], t[1]) for t in self.tasks]
      #pay, task = max(izip(payoffs, xrange(len(payoffs))))
      return pay#, task

  def singletask(self, skills, reqskills, pay):
    # This task will payoff only if the team has all of the required skills
    pay = (sum((n >= m for (n,m) in zip(skills, reqskills))) == self.nskills)*pay
    return pay

  # This task rewards breadth and depth
  def bdtask(self, skills):
    tskills = tuple(skills)
    try: 
      return self._taskdict[tskills]
    except KeyError:
      depth = min(max(skills), self.nskills)-1
      breadth = min(len([s for s in skills if s != 0]), self.nskills)-1
      pay = self.pays[depth] + self.pays[breadth]
      self._taskdict[tskills] = float(pay)
      return pay
  
  # Set up the pay structure for the bd task
  def setupbdtask(self):
    nagents = range(1,self.nskills+1)
    base = 0
    synergy = 5
    paypera = range(base, base+self.nskills*synergy, synergy)
    self.pays = [n*p for n,p in zip(nagents, paypera)]
  
  # This task rewards breadth and depth with different values for each skill
  def bdtask2(self, skills):
    tskills = tuple(skills)
    try: 
      return self._taskdict[tskills]
    except KeyError:
      depth = min(max(skills), self.nskills)-1
      breadth = min(len([s for s in skills if s != 0]), self.nskills)-1
      pay = self.pays[depth]*self.values[skills.index(max(skills))]*(depth+1) + self.pays[breadth]*sum(self.values[idx] for idx in range(self.nskills) if skills[idx] > 0)
      self._taskdict[tskills] = float(pay)
      return pay

  # Set up pay structure for the bdtask2
  def setupbdtask2(self):
    self.setupbdtask()
    self.values = [(n+1) for n in range(self.nskills)]
    #self.values.reverse()   # Skill 0 has the highest pay
    random.shuffle(self.values) # The high-pay task changes each round
    self._taskdict = {}
  
  
  #taskname = "equality_doublesize"
  #task = multitask
  taskname = "breadth_depth"
  task = bdtask
  #taskname = "breadth_depth2"
  #task = bdtask2
  
  _task_map = {
      'equality_doublesize':(multitask, None), 
      'breadth_depth':(bdtask, setupbdtask), 
      'breadth_depth2':(bdtask2, setupbdtask2)}#,
      #'breadth_depth_local':(bdtask_local, setupbdtask_local)}

  # Modify pay for a given task based on the agents in the group
  # (for experimental manipulation, to de-value preferred agents or vice-versa)
  def atask(self, agents):
    # Add together all agent skills
    allskills = sum([a.skills for a in agents])
    
    # Calculate payment for skills based on task
    taskpay = self.task(allskills)
    
    # Calculate adjustments based on the agents in the group
    adjustments = 0
    # Should be based on bias or something
    
    return taskpay + adjustments

  # Utility functions will always be in descending order of importance, with a random tiebreaker and the group at the end
  # Random tiebreaker should be <= 0 if agents should not switch to an equally-good option
  
  # utility_agent:  consider (switching groups)
  # utility_group:  acceptvote
  
  ## RANDOM UTILITY FUNCTIONS
  
  # pay, group size, random (-0.5, 0.5)
  def utility_agent_random(self, myagent):
    acceptances = myagent.acceptances
    nowpay = myagent.nowpay
    task = self.task
    nowgsize = myagent.group.gsize
    #bestgroup = max([( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,   g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    #return bestgroup
    return [( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,   g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]
       
  # pay, random
  def utility_group_random(self, mygroup):
    applications = mygroup.applications
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    #bestagent = max([( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  random.random(),  a ) for a in applications])
    #return bestagent
    return [( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  random.random(),  a ) for a in applications]
    
  # pay, random - but will not accept unless pay > 0
  def utility_groupmerge_random(self, mygroup):
    acceptances = mygroup.acceptances
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    #bestgroup = max([( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  random.random()-1.0,  g ) for g in acceptances])
    #return bestgroup
    return [( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  random.random()-1.0,  g ) for g in acceptances]


  ## WEIGHTED UTILITY FUNCTIONS

  # pay, connection weight, random
  # Could also do:
  # pay*connection_weight, random
  def utility_agent_weighted(self, myagent):
    totalweights = {}
    numnbrs = {}
    for nbr, dat in self._Gptr[myagent.id].iteritems():
      g = self._agentdict[nbr].group.id
      totalweights[g] = totalweights.get(g,0.0) + dat['weight']
      numnbrs[g] = numnbrs.get(g,0) + 1
      
    acceptances = myagent.acceptances
    task = self.task
    nowgsize=myagent.group.gsize
    nowpay = myagent.nowpay
    nowweight = totalweights.get(myagent.group.id, 0.0)
    nownbrs = numnbrs.get(myagent.group.id, 0)
    nowavg = nowweight/max(nownbrs, 1)
    
    # This uses total weight:
    #bestgroup = max([( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0) - nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    #if myagent.id == 84:
    #  print "Agent", myagent.id, "\nUtility:\n", '\n'.join([str(( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1),  g.gsize-nowgsize,   random.random()-0.5,   g.id )) for g in acceptances])
    
    #return bestgroup
    
    # Average weight
    #return [( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowavg,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]
    
    # Total weight
    return [( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]

  def utility_group_weighted(self, mygroup):
    applications = mygroup.applications
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    G = self._Gptr
    
    # for each agent we consider, determine the total weight of the connections to that agent
    totalweights = {}
    numnbrs = {}
    for u,v in nx.edge_boundary(G, [a.id for a in mygroup.agents], [a.id for a in applications]):
      totalweights[v] = totalweights.get(v, 0.0) + G[u][v]['weight']
      numnbrs[v] = numnbrs.get(v,0) + 1
    
    # This uses total weight:
    #bestagent = max([( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights[a.id],  random.random(),  a ) for a in applications])
    
    # This uses average weight:
    #bestagent = max([( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a ) for a in applications])
    
    #print "Group", mygroup.id, "\nUtility:\n", '\n'.join([str(( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a.id )) for a in applications])
    
    #return bestagent
    
    # Average weight
    #return [( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights.get(a.id, 0.0)/numnbrs.get(a.id, 1),  random.random(),  a ) for a in applications]
    
    # Total weight
    # 0.99 requires that a group have >= 1 connection strength with a prospective agent
    return [( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights.get(a.id, 0.0) - 0.99,  random.random(),  a ) for a in applications]
    
  def utility_groupmerge_weighted(self, mygroup):
    acceptances = mygroup.acceptances
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    G = self._Gptr
    
    totalweights = {}
    numnbrs = {}
    
    #print [a.id for g in acceptances for a in g.agents]
    
    allnbrs = [a.id for a in g.agents for g in acceptances]
    #for u,v in nx.edge_boundary(G, [a.id for a in mygroup.agents], set(sum([a.id for a in g.agents] for g in acceptances))):
    #set(itertools.chain.from_iterable([a.id for a in g.agents] for g in acceptances))
    for u,v in nx.edge_boundary(G, [a.id for a in mygroup.agents], allnbrs):
      nbrgroup = self._agentdict[v].group.id
      totalweights[nbrgroup] = totalweights.get(nbrgroup, 0.0) + G[u][v]['weight']
      numnbrs[nbrgroup] = numnbrs.get(nbrgroup,0) + 1
    
    # This uses total weight:
    #bestgroup = max([( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalweights[g.id],  random.random()-1.0,  g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalweights[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances])
    
    #return bestgroup
    
    # Average weight
    #return [( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalweights[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances]
    
    # Total weight
    return [( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalweights.get(g.id, 0.0) - 0.99,  random.random()-1.0,  g ) for g in acceptances]
  
  
  ## BIAS UTILITY FUNCTIONS

  # pay, connection bias, random
  # Could also do:
  # pay*connection_bias, random
  def utility_agent_bias(self, myagent):
    totalbias = {}
    numnbrs = {}
    for nbr, dat in self._Gptr[myagent.id].iteritems():
      g = self._agentdict[nbr].group.id
      totalbias[g] = totalbias.get(g,0.0) + dat['bias']
      numnbrs[g] = numnbrs.get(g,0) + 1
      
    acceptances = myagent.acceptances
    task = self.task
    nowgsize=myagent.group.gsize
    nowpay = myagent.nowpay
    nowbias = totalbias.get(myagent.group.id, 0.0)
    nownbrs = numnbrs.get(myagent.group.id, 0)
    nowavg = nowbias/max(nownbrs, 1)
    
    # This uses total weight:
    #bestgroup = max([( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0) - nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    #if myagent.id == 84:
    #  print "Agent", myagent.id, "\nUtility:\n", '\n'.join([str(( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1),  g.gsize-nowgsize,   random.random()-0.5,   g.id )) for g in acceptances])
    
    #return bestgroup
    return [( task(g.withskills(myagent))/(g.gsize + 1) - nowpay,  totalbias.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowbias,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]

  def utility_group_bias(self, mygroup):
    applications = mygroup.applications
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    G = self._Gptr
    
    # for each agent we consider, determine the total weight of the connections to that agent
    totalbias = {}
    numnbrs = {}
    for u,v in nx.edge_boundary(G, [a.id for a in mygroup.agents], [a.id for a in applications]):
      totalbias[v] = totalbias.get(v, 0.0) + G[u][v]['bias']
      numnbrs[v] = numnbrs.get(v,0) + 1
    
    # This uses total weight:
    #bestagent = max([( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights[a.id],  random.random(),  a ) for a in applications])
    
    # This uses average weight:
    #bestagent = max([( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a ) for a in applications])
    
    #print "Group", mygroup.id, "\nUtility:\n", '\n'.join([str(( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a.id )) for a in applications])
    
    #return bestagent
    return [( task(mygroup.withskills(a))/(nowgsize + a.gsize) - nowpay,  totalbias[a.id]/numnbrs[a.id],  random.random(),  a ) for a in applications]
    
  def utility_groupmerge_bias(self, mygroup):
    acceptances = mygroup.acceptances
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    G = self._Gptr
    
    totalbias = {}
    numnbrs = {}
    for u,v in nx.edge_boundary(G, [a.id for a in mygroup.agents], set(sum([a.id for a in g.agents] for g in acceptances))):
      nbrgroup = self._agentdict[v].group.id
      totalbias[nbrgroup] = totalbias.get(nbrgroup, 0.0) + G[u][v]['bias']
      numnbrs[nbrgroup] = numnbrs.get(nbrgroup,0) + 1
    
    # This uses total weight:
    #bestgroup = max([( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalweights[g.id],  random.random()-1.0,  g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalweights[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances])
    
    #return bestgroup
    return [( task(mygroup.withskills(g))/(nowgsize + g.gsize) - nowpay,  totalbias[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances]
    
    
  strategy = 'random'
  utility_agent = utility_agent_random
  utility_group = utility_group_random
  utility_groupmerge = utility_groupmerge_random
  
  #strategy = 'bias'
  #utility_agent = utility_agent_bias
  #utility_group = utility_group_bias
  #utility_groupmerge = utility_groupmerge_bias
  
  # Using average weight in all of these functions and leaving all weights at 1 should give identical results to the random strategy
  #strategy = 'weighted'
  #utility_agent = utility_agent_weighted
  #utility_group = utility_group_weighted
  #utility_groupmerge = utility_groupmerge_weighted
  
  _utility_map = {
      'random':(utility_agent_random, utility_group_random, utility_groupmerge_random), 
      'bias':(utility_agent_bias, utility_group_bias, utility_groupmerge_bias),
      'weighted':(utility_agent_weighted, utility_group_weighted, utility_groupmerge_weighted)}
  
  def setutility(self, strategy):
    self.strategy = strategy
    self.utility_agent, self.utility_group, self.utility_groupmerge = Configuration._utility_map[self.strategy]
  
  #learning_rate = 0.25

  # Accept if we find a positive dimension before we find a negative dimension
  # (each dimension strictly dominates the one beneath)
  def utility_tiebreaker_deterministic(self, utility):
    #print utility
    bestu = max(utility)
    for u in bestu:
      if u > 0:
        best = bestu[-1]; break
      if u < 0:
        best = None; break
      # if u == 0: continue
    return best

  def utility_tiebreaker_normalized(self, utility):
    # Normalize utility by dividing each dim by the total
    nutility = len(utility[0])-2    # number of dimensions of utility
    nputil = np.array([u[:-2] for u in utility])  # strip off group id and random term (we hope)
    umax = np.max(nputil, 0)
    umax[umax <= 0] = 1
    unorm = nputil/umax
    #print unorm
    uweights = np.array([1.0/2**n for n in range(nutility)]) # Assume each following dimension is half as important as the previous
    usum = (unorm*uweights).sum(1)
    #print usum
    goods = np.array([(u,idx) for idx, u in enumerate(usum) if u > 0])
    if len(goods):
      weights = goods[:,0]/goods[:,0].sum()
      bestidx = int(np.random.choice(goods[:,1], p = weights))
      #print goods[:,1], weights, bestidx
      best = utility[bestidx][-1]
      return best
    else:
      return None
  
  utility_tiebreak = 'deterministic'
  utility_tiebreaker = utility_tiebreaker_deterministic
  #utility_tiebreak = 'normalized'
  #utility_tiebreaker = utility_tiebreaker_normalized
  _tiebreak_map = {'deterministic':utility_tiebreaker_deterministic, 'normalized':utility_tiebreaker_normalized}

  def settiebreaker(self, utility_tiebreak):
    self.utility_tiebreak = utility_tiebreak
    self.utility_tiebreaker = Configuration._tiebreak_map[self.utility_tiebreak]
  
  def printself(self):
    for k,v in vars(self).iteritems():
      if k[0] != '_':
        print k, v
      
  def outputcfg(self, showhidden=False):
    cfg = {}
    vard = dict(vars(Configuration))
    vard.update(vars(self))
    for k,v in vard.iteritems():
      dtype = type(v).__name__
      if dtype!='instancemethod' and dtype != 'function' and (showhidden or k[0] != "_"):
        cfg[k] = v
    return cfg

# Return a list, or convert a single element to a list
def trylist(L):
  try:
    return list(L)
  except TypeError:
    return [L]





##   PROTOCOL 0:  (non-social)
##     video, no ultimatum, play lottery, and no ratings
##     45 minutes; 5 minutes margin
##   PROTOCOL 1:  (social)
##     video, no ultimatum, play publicgoods and do ratings
##     45 minutes; 5 minutes margin
##   PROTOCOL 99:  (testing)
##     no video, no ultimatum, play pubgoods and do ratings
##     10 minutes; 3 minutes margin
if PROTOCOL == 0:
  Configuration._do_video = True
  Configuration._do_intro_sim = True
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = True
  Configuration.do_ratings = True
  Configuration.delay_sim_agents = True
  Configuration._time_limit = 70
  Configuration._margin_time = 5
elif PROTOCOL == 1:
  Configuration._do_video = True
  Configuration._do_intro_sim = True
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.show_global_ratings = True
  Configuration.do_ratings = True
  Configuration.delay_sim_agents = True
  Configuration._time_limit = 70
  Configuration._margin_time = 5
elif PROTOCOL == 2:
  Configuration._do_video = True
  Configuration._do_intro_sim = True
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.show_global_ratings = False
  Configuration.do_ratings = True
  Configuration.delay_sim_agents = True
  Configuration._time_limit = 70
  Configuration._margin_time = 5
elif PROTOCOL == 3:
  Configuration._do_video = True
  Configuration._do_intro_sim = True
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.show_global_ratings = True
  Configuration.do_ratings = True
  Configuration.delay_sim_agents = True
  Configuration._time_limit = 70
  Configuration._margin_time = 5
  Configuration.alt_pubgoods = True
elif PROTOCOL == 98:
  Configuration._do_video = True
  Configuration._do_intro_sim = True
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.do_ratings = True
  Configuration._time_limit = 10
  Configuration._margin_time = 3
  Configuration.delay_sim_agents = False
elif PROTOCOL == 99:
  Configuration._do_video = False
  Configuration._do_intro_sim = True
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.do_ratings = True
  Configuration._time_limit = 10
  Configuration._margin_time = 3
  Configuration.delay_sim_agents = False
elif PROTOCOL == 100:
  Configuration._do_video = False
  Configuration._do_intro_sim = False
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.do_ratings = True
  Configuration._time_limit = 10
  Configuration._margin_time = 0
  Configuration.delay_sim_agents = False
  Configuration._threaded_sim = False
  Configuration.reset_graph_iters = 20
  Configuration._log_teamstatus = False
  #Configuration.percent_conditional = 0.5
  Configuration.nsteps = 10
  Configuration.n = 16
elif PROTOCOL == 101:
  Configuration._do_video = False
  Configuration._do_intro_sim = False
  Configuration._do_ultimatum = False
  Configuration.do_publicgoods = True
  Configuration.hide_publicgoods = False
  Configuration.do_ratings = True
  Configuration._time_limit = 10
  Configuration._margin_time = 0
  Configuration.delay_sim_agents = False
  Configuration._threaded_sim = False
  Configuration.reset_graph_iters = 10
  Configuration._log_teamstatus = False
  Configuration.simhumans = True # Use experimental data to simulate human subjects
  
class MultiConfig(Configuration):
  reps = 1  # Number of reps for each configuration
  groups_can_merge = [False]
  expel_agents = [False]
  fully_connect_groups = [False]
  #n = [150, 500, 1000]
  #n = [500]
  n = [Configuration.n]
  #connections = [4, 6, 8, 10, 12]
  connections= [4, 6]
  prob_rewire = [0.1, 0.2]     # For watts-strogatz and grid rewire
  graph_type = ['connected_watts_strogatz_graph']#, "barabasi_albert_graph", "erdos_renyi_graph"]#, "complete_graph"]
  #, 'wheel_graph', 'star_graph', 'cycle_graph', 'path_graph']
  rewire_grid_graph = [True]
  _k_graph_max_n = 600  #  Don't run complete graphs with more than this number of agents (takes a long time)
  #strategy = ['worth', 'closest']
  strategy = ['random']   # random, weighted, bias
  #ndumb = [1,2,5,0.1,0.25,0.5,0.75,0.9]
  ndumb = [0,2] #[0,0.1,0.25]
  
  def __iter__(self):
    return self
  
  def next(self):
    pass
    
  def itersims(self):
    curr = Configuration()
    for fc in trylist(self.fully_connect_groups):
      curr.fully_connect_groups = fc
      for ex in trylist(self.expel_agents):
        curr.expel_agents = ex
        for gm in trylist(self.groups_can_merge):
          curr.groups_can_merge = gm
          for g in trylist(self.graph_type):
            curr.graph_type = g
            if fc == True and curr.graph_type == 'complete_graph': continue
            for n in trylist(self.n):
              curr.n = n
              if n > self._k_graph_max_n and g == 'complete_graph':
                continue
              for c in trylist(self.connections):
                curr.connections = c
                if c != trylist(self.connections)[0] and curr.graph_type == 'complete_graph': continue
                for p in trylist(self.prob_rewire):
                  curr.prob_rewire = p
                  #curr.num_edges = int((curr.n*(curr.n-1))/2 * p)
                  for st in trylist(self.strategy):
                    #curr.strategy = st   ### TEMPORARY
                    #curr.setutility(st)
                    for nd in trylist(self.ndumb):
                      curr.ndumb = nd
                      for m in trylist(self.maxskills):
                        curr.maxskills = m
                        if g == 'grid_graph':
                          curr.connections = 4
                          for rw in trylist(self.rewire_grid_graph):
                            curr.rewire_grid_graph = rw
                            for r in range(self.reps):
                              curr.simnumber += 1
                              yield copy.copy(curr)
                        else:
                          for r in range(self.reps):
                            curr.simnumber += 1
                            yield copy.copy(curr)

class RepliConfig(Configuration):
  reps = 10   # Number of replications of each setup
  
  def __init__(self, dbfile, humandata):
    super(RepliConfig, self).__init__()
    
    self.dbfile = dbfile
    self.humandata = humandata
    
    conn = sqlite3.connect(self.dbfile)
    
    ## READ IN DATA HERE
    ses_data = {}
    
    # Get a list of which sessions completed successfully
    sessions = conn.execute("SELECT * FROM sessions")
    for sessionid, start, end in sessions:
      if end != -1:
        ses_data[sessionid] = True
    
    # Get data on session configurations
    sesdat = conn.execute("SELECT * FROM session_config")
    for row in sesdat:
      if row[0] not in ses_data:
        continue    # Bad session, don't try to import it
      c = Configuration()
      (c.sessionid, _, c._do_intro_sim, c.do_publicgoods, c.hide_publicgoods,
       c.pubgoods_mult, c.do_ratings, c._time_limit, _nhumans, 
       c.show_other_team_members, c.keep_teams, _DYNAMIC, _KEEP_GRAPH,
       c.show_global_ratings, c.show_nhistory) = row
      c._humandata = humandata
      ses_data[c.sessionid] = c
    
    # Get data on network
    ## BUG: We do not have complete data on the network in neighbors.
    netdat = conn.execute("SELECT * FROM neighbors WHERE simnum = 0")
    for row in netdat:
      sessionid = row[2]
      if sessionid not in ses_data:
        continue
      
      ses_cfg = ses_data[sessionid]
      try:
        G = ses_cfg._Gptr
        if G is None:
          raise AttributeError()
      except AttributeError:
        G = ses_cfg._Gptr = nx.Graph()
      
      G.add_edge(row[4], row[5], weight=1.0, bias=0.0)

    ## TEMPORARY: use the order of teams in the teamstatus table to 
    ##            reconstruct the network
    netdat2 = conn.execute("SELECT * FROM teamstatus WHERE simnum = 0 AND " +
                           "internum = 0 AND eventtype = 'acceptvote'")
    for row in netdat2:
      sessionid = row[2]
      if sessionid not in ses_data:
        continue
      ses_cfg = ses_data[sessionid]
      G = ses_cfg._Gptr
      G.add_edge(row[7], row[8], weight=1.0, bias=0.0)
                            

    # Get data on agent dispositions
    aconfdat = conn.execute("SELECT * from agent_config")
    for row in aconfdat:
      sessionid = row[1]
      agentid = row[2]
      if sessionid not in ses_data:
        continue
      
      G = ses_data[sessionid]._Gptr
      dat = G.node[agentid]
      
      # Initialize agent data
      dat['id'] = agentid
      dat['group'] = agentid     # Agent is its own group
      dat['switches'] = 0
      dat['nowpay'] = 0
      dat['acceptances'] = []
      dat['worth'] = 5
    
      # Set skills
      #lev = random.randint(1, min(cfg.nskills, cfg.maxskills))
      #skills = [1]*lev + [0]*(cfg.nskills-lev)
      #random.shuffle(skills)
      skills = [1] + [0]*(Configuration.nskills-1)
      dat['skills'] = skills
      
      try:
        dispos = ses_data[sessionid].dispositions
      except AttributeError:
        dispos = ses_data[sessionid].dispositions = {}
      
      if row[3] == 'human':
        #dispos[agentid] = 'human.'+str(sessionid)+'.'+str(agentid)
        dispos[agentid] = 'human.{:02d}.{:d}'.format(sessionid, agentid)
      else:
        dispos[agentid] = row[3]
        
    #conn.commit()
    conn.close()
    
    self.ses_data = ses_data
    
  
  def __iter__(self):
    return self
  
  def next(self):
    pass
  
  def itersims(self):
    from simulation import simulation
    for sessionid, currcfg in self.ses_data.iteritems():
      sim = simulation()
      #Debug
      G = currcfg._Gptr
      sim.replicate(currcfg._Gptr, currcfg)
      for _ in range(self.reps):
        yield sim, currcfg
        ## Will need something more subtle than copy; need to actually reset 
        ## the sim and config after a run
        
  
  