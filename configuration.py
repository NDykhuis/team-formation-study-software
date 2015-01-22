import random
import numpy as np
import networkx as nx
import copy

PROTOCOL = 99
##   Setting this PROTOCOL flag will set several configuration options at once, for ease of experimentation
##   If it is not set, the default options in the configuration class will be used
##   PROTOCOL 0:  (non-social)
##     video, no ultimatum, play lottery, and disable ratings
##     35 minutes; 5 minutes margin
##   PROTOCOL 1:  (social)
##     video, no ultimatum, play publicgoods and do ratings
##     35 minutes; 5 minutes margin
##   PROTOCOL 98:  (testing video)
##     video, no ultimatum, play pubgoods and do ratings
##     10 minutes; 3 minutes margin
##   PROTOCOL 99:  (testing short)
##     no video, no ultimatum, play pubgoods and do ratings
##     1 minute; 3 minutes margin

class configuration(object):
  
  n = 16           # Number of agents
  nhumans = 0      # Number of humans (set by simserver based on how many frontends connect)
  ndumb = 0        # Number of random agents (rather than rational)
  
  exchange_rate = 5.0   # Divide sim-dollars by this to get real dollars
  
  _do_video = False
  _capture_screenshots = False

  _do_intro_sim = True
    
  _do_ultimatum = False
  ultimatum_niter = 2
  dicatator_niter = 1
  
  _do_publicgoods = True
  #pubgoods_mult = 1.2
  pubgoods_mult = 50     # Percent the pot is increased
  _hide_publicgoods = True
  pg_contribrange = {   # Percent to contribute in pubgoods, low to high
    'nice':(0.7, 1.0),
    'mean':(0.0, 0.25),
    'fair':(0.5, 0.8),
    'random':(0.0, 1.0)
  }
  
  
  persistent_pubgoods = True
  ppg_startpay = 10
  
  
  _show_other_team_members = True
  
  _do_ratings = True
  
  show_global_ratings = True
  show_nhistory = 5      # Set to zero to disable
  
  show_skills = False    # show skills to the player
  
  keep_teams = False     # After a simulation, keep the current teams
  
  agent_memory = True   ## TESTING - agents stop applying to groups that have rejected them
  agent_mem_threshold = 1
  agent_mem_decay = 0.5
  
  # Sim agents take real time to make their decisions 
  delay_sim_agents = True   ## SHOULD BE TRUE
  delay_n_sims = 6          # Add a delay to only the first n agents
  #_agent_delays = {'propose':2.5, 'acceptvote':1.5, 'join':1.0, 'expelvote':1.0, 'conclude':1.0, 'publicgoods':2.5}    # Arbitrary
  _agent_delays = {'propose':4.0, 'acceptvote':5.0, 'join':5.0, 'expelvote':3.0, 'conclude':3.0, 'publicgoods':10.0}    # Based on pilot data
  _agent_delay_dev = {'propose':2.0, 'acceptvote':2.5, 'join':1.5, 'expelvote':1.5, 'conclude':1.0, 'publicgoods':5.0}  # Approx as half the IQR
  
  social_sim_agents = True
  social_learning_rate = 0.66
  
  nsteps = 10      # Max number of iterations
  deaditers = 1     # How many iterations with no change before we stop

  _time_limit = 30    # hard time limit in minutes; sim will be cut off after the current iteration when this time expires
  _margin_time = 3    # start the last sim no later than this many minutes before end



  ## DISPLAY PARAMETERS
  _display_every_step = False
  _pause_every_step = False
  _pause_after_sim = False
  _draw_graph = False            # Controls graphical output
  _pause_graph = False
  _draw_graph_after_sim = False
  _verbose = 4                   # Controls print output (integer 0-n)
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
    self.task = self.ppgtask
    #self.task = self.bdtask
    #self.setupbdtask()
  
  def reset(self):
    #self.task = self.bdtask
    #self.setupbdtask()
    pass
  
  # This task returns the total possible contribution of everyone in the group
  def ppgtask(self, agents):
    print [a.totalpay for a in agents], sum([a.totalpay for a in agents])
    return sum(a.totalpay for a in agents)
  
  # This task rewards groups based only on how many members are on a team
  # Calculates number of members assuming that maxskills == 1
  # Team max size is given by nskills
  def nmemtask(self, agents):
    nmem = len(agents)
    increward = 5
    npay = min(nmem, self.nskills)
    pay = npay * increward * (npay-1)   # (npay*increward) for each of the first (npay) members
    return float(pay)/nmem
  
  # Optimized function to answer the question:
  # How much pay for a given set of skills?
  def multitask(self, agents):
    # This task will payoff only if the team has all of the required skills
    skills = sum(np.array(a.skills) for a in agents)
    tskills=tuple(skills)
    try:
      return self._taskdict[tskills]
    except KeyError:
      pay = float(max(self.singletask(skills, t[0], t[1]) for t in self.tasks))/len(agents)
      self._taskdict[tskills] = pay
      #payoffs = [self.singletask(skills, t[0], t[1]) for t in self.tasks]
      #pay, task = max(izip(payoffs, xrange(len(payoffs))))
      return pay#, task

  def singletask(self, skills, reqskills, pay):
    # This task will payoff only if the team has all of the required skills
    pay = (sum((n >= m for (n,m) in zip(skills, reqskills))) == self.nskills)*pay
    return pay

  # This task rewards breadth and depth
  def bdtask(self, agents):
    skills = sum(np.array(a.skills) for a in agents)
    tskills = tuple(skills)
    try: 
      return self._taskdict[tskills]
    except KeyError:
      depth = min(max(skills), self.nskills)-1
      breadth = min(len([s for s in skills if s != 0]), self.nskills)-1
      pay = (self.pays[depth] + self.pays[breadth])/len(agents)
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
    skills = sum(np.array(a.skills) for a in agents)
    tskills = tuple(skills)
    try: 
      return self._taskdict[tskills]
    except KeyError:
      depth = min(max(skills), self.nskills)-1
      breadth = min(len([s for s in skills if s != 0]), self.nskills)-1
      pay = self.pays[depth]*self.values[skills.index(max(skills))]*(depth+1) + self.pays[breadth]*sum(self.values[idx] for idx in range(self.nskills) if skills[idx] > 0)
      pay /= len(self.agents)
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
    #bestgroup = max([( task(g.withagent(myagent))/(g.gsize + 1) - nowpay,   g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    #return bestgroup
    return [( task(g.withagent(myagent)) - nowpay,   g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]
       
  # pay, random
  def utility_group_random(self, mygroup):
    applications = mygroup.applications
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    #bestagent = max([( task(mygroup.withagent(a))/(nowgsize + a.gsize) - nowpay,  random.random(),  a ) for a in applications])
    #return bestagent
    return [( task(mygroup.withagent(a)) - nowpay,  random.random(),  a ) for a in applications]
    
  # pay, random - but will not accept unless pay > 0
  def utility_groupmerge_random(self, mygroup):
    acceptances = mygroup.acceptances
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    #bestgroup = max([( task(mygroup.withagent(g))/(nowgsize + g.gsize) - nowpay,  random.random()-1.0,  g ) for g in acceptances])
    #return bestgroup
    return [( task(mygroup.withagent(g)) - nowpay,  random.random()-1.0,  g ) for g in acceptances]


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
    #bestgroup = max([( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0) - nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    #if myagent.id == 84:
    #  print "Agent", myagent.id, "\nUtility:\n", '\n'.join([str(( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1),  g.gsize-nowgsize,   random.random()-0.5,   g.id )) for g in acceptances])
    
    #return bestgroup
    
    # Average weight
    #return [( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowavg,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]
    
    # Total weight
    return [( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]

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
    #bestagent = max([( task(mygroup.withagent(a)) - nowpay,  totalweights[a.id],  random.random(),  a ) for a in applications])
    
    # This uses average weight:
    #bestagent = max([( task(mygroup.withagent(a)) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a ) for a in applications])
    
    #print "Group", mygroup.id, "\nUtility:\n", '\n'.join([str(( task(mygroup.withagent(a)) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a.id )) for a in applications])
    
    #return bestagent
    
    # Average weight
    #return [( task(mygroup.withagent(a)) - nowpay,  totalweights.get(a.id, 0.0)/numnbrs.get(a.id, 1),  random.random(),  a ) for a in applications]
    
    # Total weight
    # 0.99 requires that a group have >= 1 connection strength with a prospective agent
    return [( task(mygroup.withagent(a)) - nowpay,  totalweights.get(a.id, 0.0) - 0.99,  random.random(),  a ) for a in applications]
    
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
    #bestgroup = max([( task(mygroup.withagent(g)) - nowpay,  totalweights[g.id],  random.random()-1.0,  g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(mygroup.withagent(g)) - nowpay,  totalweights[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances])
    
    #return bestgroup
    
    # Average weight
    #return [( task(mygroup.withagent(g)) - nowpay,  totalweights[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances]
    
    # Total weight
    return [( task(mygroup.withagent(g)) - nowpay,  totalweights.get(g.id, 0.0) - 0.99,  random.random()-1.0,  g ) for g in acceptances]
  
  
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
    #bestgroup = max([( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0) - nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances])
    
    #if myagent.id == 84:
    #  print "Agent", myagent.id, "\nUtility:\n", '\n'.join([str(( task(g.withagent(myagent)) - nowpay,  totalweights.get(g.id, 0.0)/numnbrs.get(g.id,1),  g.gsize-nowgsize,   random.random()-0.5,   g.id )) for g in acceptances])
    
    #return bestgroup
    return [( task(g.withagent(myagent)) - nowpay,  totalbias.get(g.id, 0.0)/numnbrs.get(g.id,1)-nowweight,  g.gsize-nowgsize,   random.random()-0.5,   g ) for g in acceptances]

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
    #bestagent = max([( task(mygroup.withagent(a)) - nowpay,  totalweights[a.id],  random.random(),  a ) for a in applications])
    
    # This uses average weight:
    #bestagent = max([( task(mygroup.withagent(a)) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a ) for a in applications])
    
    #print "Group", mygroup.id, "\nUtility:\n", '\n'.join([str(( task(mygroup.withagent(a)) - nowpay,  totalweights[a.id]/numnbrs[a.id],  random.random(),  a.id )) for a in applications])
    
    #return bestagent
    return [( task(mygroup.withagent(a)) - nowpay,  totalbias[a.id]/numnbrs[a.id],  random.random(),  a ) for a in applications]
    
  def utility_groupmerge_bias(self, mygroup):
    acceptances = mygroup.acceptances
    nowpay = mygroup.nowpay
    task = self.task
    nowgsize = mygroup.gsize
    
    totalbias = {}
    numnbrs = {}
    for u,v in nx.edge_boundary(G, [a.id for a in mygroup.agents], set(sum([a.id for a in g.agents] for g in acceptances))):
      nbrgroup = self._agentdict[v].group.id
      totalbias[nbrgroup] = totalbias.get(nbrgroup, 0.0) + G[u][v]['bias']
      numnbrs[nbrgroup] = numnbrs.get(nbrgroup,0) + 1
    
    # This uses total weight:
    #bestgroup = max([( task(mygroup.withagent(g)) - nowpay,  totalweights[g.id],  random.random()-1.0,  g ) for g in acceptances])
    
    # This uses average weight:
    #bestgroup = max([( task(mygroup.withagent(g)) - nowpay,  totalweights[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances])
    
    #return bestgroup
    return [( task(mygroup.withagent(g)) - nowpay,  totalbias[g.id]/numnbrs[g.id],  random.random()-1.0,  g.id ) for g in acceptances]
    
    
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
    self.utility_agent, self.utility_group, self.utility_groupmerge = configuration._utility_map[self.strategy]
  
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
    self.utility_tiebreaker = configuration._tiebreak_map[self.utility_tiebreak]
  
  def printself(self):
    for k,v in vars(self).iteritems():
      if k[0] != '_':
        print k, v
      
  def outputcfg(self, showhidden=False):
    cfg = {}
    vard = dict(vars(configuration))
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
  configuration._do_video = True
  configuration._do_intro_sim = True
  configuration._do_ultimatum = False
  configuration._do_publicgoods = True
  configuration._hide_publicgoods = True
  configuration._do_ratings = True
  configuration.delay_sim_agents = True
  configuration._time_limit = 45
  configuration._margin_time = 5
elif PROTOCOL == 1:
  configuration._do_video = True
  configuration._do_intro_sim = True
  configuration._do_ultimatum = False
  configuration._do_publicgoods = True
  configuration._hide_publicgoods = False
  configuration._do_ratings = True
  configuration.delay_sim_agents = True
  configuration._time_limit = 45
  configuration._margin_time = 5
elif PROTOCOL == 98:
  configuration._do_video = True
  configuration._do_intro_sim = True
  configuration._do_ultimatum = False
  configuration._do_publicgoods = True
  configuration._hide_publicgoods = False
  configuration._do_ratings = True
  configuration._time_limit = 10
  configuration._margin_time = 3
  configuration.delay_sim_agents = False
elif PROTOCOL == 99:
  configuration._do_video = False
  configuration._do_intro_sim = True
  configuration._do_ultimatum = False
  configuration._do_publicgoods = True
  configuration._hide_publicgoods = False
  configuration._do_ratings = True
  configuration._time_limit = 10
  configuration._margin_time = 3
  configuration.delay_sim_agents = False




class multiconfig(configuration):
  reps = 1  # Number of reps for each configuration
  groups_can_merge = [False]
  expel_agents = [False]
  fully_connect_groups = [False]
  #n = [150, 500, 1000]
  #n = [500]
  n = [configuration.n]
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
    curr = configuration()
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
