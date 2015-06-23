import random
from simhumanagent import SimHumanAgent, HumanData
import numpy as np

class Evolver(object):
  # Need a mutation size amount for each item, as well as valid range/values
  # Need a mutation amount parameter
  switch_prob = 0.25  # probability that next gene will be from other parent
  keep_top_n = 2
  kill_bottom_n = 4
  
  dispo_id_counter = 100000
  
  def __init__(self, humandata):
    # Requires the simhumanagent generator
    self.humandata = humandata
  
  @classmethod
  def get_new_dispo_id(cls):
    cls.dispo_id_counter += 1
    return cls.dispo_id_counter
  
  def genagents(self, configuration, n=16, prevagents=None):
    # Generates a society of agents, possibly based on a previous group of agents
    
    newagents = []
    
    if prevagents:
      # Sort agents
      fitness = [agent.finalpay for agent in prevagents]
      sortpays, sortagents = zip(*sorted(zip(fitness, prevagents), reverse=True))
      
      # Keep top n
      newagents.extend(sortagents[:Evolver.keep_top_n])
      
      # Discard the bottom n
      if Evolver.kill_bottom_n:
        sortagents = sortagents[:-Evolver.kill_bottom_n]
        sortpays = sortpays[:-Evolver.kill_bottom_n]
      
      # For the remaining 16-top_n agents, breed the 16-bottom_n agents,
      # weighted by fitness
      paytotal = float(sum(sortpays))
      payweights = np.array(sortpays)/paytotal
      choiceidx1 = np.random.choice(range(len(sortagents)), size=(16-Evolver.keep_top_n), p=payweights)
      choiceidx2 = np.random.choice(range(len(sortagents)), size=(16-Evolver.keep_top_n), p=payweights)
      
      #newagents.extend([sortagents[i] for i in choiceidx])
      newagents.extend([self.breed(sortagents[i], sortagents[j]) 
                        for i,j in zip(choiceidx1, choiceidx2)])
      
      for i,agent in enumerate(newagents):
        agent.id = i
      
    else:
      # Generate n agents from our HumanData
      # need a config!
      newagents = [self.humandata.gen_agent(configuration) for i in range(n)]
    
    return newagents
  
  def breed(self, agent1, agent2):
    a1tup = agent1.to_tuple()
    a2tup = agent2.to_tuple()
    ngenes = len(a1tup)
    newtup = [0]*ngenes
    
    curparent = random.random() > 0.5
    for i, gtup in enumerate(zip(a1tup, a2tup)):
      newtup[i] = gtup[curparent]
      if random.random() < Evolver.switch_prob:
        curparent = not curparent
    
    # Optionally, perturb the tuple now
    #newtup = self.perturb_tuple(newtup, newid=False)
    
    # Create new simhumanagent
    # from_tuple
    newid = Evolver.get_new_dispo_id()
    newagent = SimHumanAgent(agent1.cfg, {'uuid':newid})
    newagent.from_tuple(tuple(newtup))
    return newagent
  
  def perturb_agent(self, agent):
    atuple = agent.to_tuple()
    newtuple = self.perturb_tuple(atuple)
    agent.from_tuple(newtuple)
    # Change agent's aid here also?
    return agent
  
  def perturb_tuple(self, atuple, newid=True):
    # Ensure that we set the first element of the tuple to a new id value
    raise NotImplementedError