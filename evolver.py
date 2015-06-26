import random
from simhumanagent import SimHumanAgent, HumanData
import numpy as np
import pprint

class Evolver(object):
  # Need a mutation size amount for each item, as well as valid range/values
  # Need a mutation amount parameter
  switch_prob = 0.2  # probability that next gene will be from other parent
                   # (set to zero to disable crossover)
  keep_top_n = 4
  kill_bottom_n = 0
  reintroduce_n = 1     # Reintroduce n agents from the original data
  do_mutate = True
  mutation_magnitude = 0.5    # multiplier on std dev of random noise 
  prob_mutate = 0.25        # Probability that a given trait will mutate
  range_expansion = 0.0    # move max/min this many pct away from each other
  use_all_history = True    # Select agents from ALL historical data, not just current round
  fitness_history_alpha = 0.33
  # These options will need to go in Configuration soon
  
  dispo_id_counter = 100000
  
  def __init__(self, humandata):
    # Requires the simhumanagent generator
    self.humandata = humandata
    self.fitnesshistory = {}
  
  @classmethod
  def get_new_dispo_id(cls):
    cls.dispo_id_counter += 1
    return cls.dispo_id_counter
  
  def genagents(self, configuration, n=16, prevagents=None):
    # Generates a society of agents, possibly based on a previous group of agents
    
    newagents = []
    
    if prevagents:
      if Evolver.use_all_history:
        # Update fitness history using alpha decay averaging
        for agent in prevagents:
          # Fitness history contains (average_pay, agent_object) tuples
          self.fitnesshistory[agent.disposition] = (
            agent.finalpay if agent not in self.fitnesshistory else
            (1.0-self.fitness_history_alpha)*self.fitnesshistory[agent.disposition] +
            self.fitness_history_alpha*agent.finalpay, agent
          )
        sortpays, sortagents = zip(*sorted(self.fitnesshistory.values(), reverse=True))
        print '\n'.join([str((agent.disposition, round(pay))) for (agent, pay) in zip(sortagents, sortpays)][:20])
        
        # Kill 1/8 of the agents in the history
        medpay = sortpays[7*len(sortpays)/8]
        self.fitnesshistory = {dispo:(pay, agent) 
                               for dispo, (pay, agent) 
                               in self.fitnesshistory.items()
                               if pay > medpay}
        
        print "Number of agents in history:", len(sortagents)
        
      else:
        # Sort agents by final pay
        fitness = [agent.finalpay for agent in prevagents]
        sortpays, sortagents = zip(*sorted(zip(fitness, prevagents), reverse=True))
        print [agent.probdata['uuid'] for agent in sortagents]
        print [round(p) for p in sortpays]
        
      # Keep top n
      newagents.extend(sortagents[:Evolver.keep_top_n])
      
      # Discard the bottom n
      if Evolver.kill_bottom_n:
        sortagents = sortagents[:-Evolver.kill_bottom_n]
        sortpays = sortpays[:-Evolver.kill_bottom_n]
      
      # Reintroduce n agents from the data
      newagents.extend([self.humandata.gen_agent(configuration) for i in range(Evolver.reintroduce_n)])
      
      # For the remaining 16-top_n agents, breed the 16-bottom_n agents,
      # weighted by fitness
      nleft = configuration.n-Evolver.keep_top_n-Evolver.reintroduce_n
      if nleft > 0:
        paytotal = float(sum(sortpays))
        payweights = np.array(sortpays)/paytotal
        choiceidx1 = np.random.choice(range(len(sortagents)), size=(nleft), p=payweights)
        choiceidx2 = np.random.choice(range(len(sortagents)), size=(nleft), p=payweights)
        
        #newagents.extend([sortagents[i] for i in choiceidx])
        newagents.extend([self.breed(sortagents[i], sortagents[j], configuration) 
                          for i,j in zip(choiceidx1, choiceidx2)])
      
      for i,agent in enumerate(newagents):
        agent.id = i
        agent.reset2()
      
    else:
      # Generate n agents from our HumanData
      # need a config!
      newagents = [self.humandata.gen_agent(configuration) for i in range(n)]
      #newagents = [self.humandata.gen_agent(configuration, uuid='vanillapublic') for i in range(n)] #TEMP
    
    for a in newagents:  # Not done by any other reset
        a.finalpay = 0
        a.pgmem = {}
      
    return newagents
  
  def breed(self, agent1, agent2, configuration):
    a1tup = agent1.to_tuple()
    a2tup = agent2.to_tuple()
    ngenes = len(a1tup)
    newtup = [0]*ngenes
    
    curparent = random.random() > 0.5
    for i, gtup in enumerate(zip(a1tup, a2tup)):
      newtup[i] = gtup[curparent]
      if random.random() < Evolver.switch_prob:
        curparent = not curparent
    
    # Optionally, mutate the tuple now
    if Evolver.do_mutate:
      newtup = self.mutate_tuple(newtup, newid=False)
    
    # Create new simhumanagent
    # from_tuple
    newid = Evolver.get_new_dispo_id()
    newagent = SimHumanAgent(configuration, {'uuid':newid})
    newagent.from_tuple(tuple(newtup))
    
    #print "Cross", a1tup[0], a2tup[0]
    #pprint.pprint(zip(a1tup, newagent.to_tuple()))
    #pprint.pprint(zip(a2tup, newagent.to_tuple()))
    
    return newagent
  
  def mutate_agent(self, agent):
    atuple = agent.to_tuple()
    newtuple = self.mutate_tuple(atuple)
    agent.from_tuple(newtuple)
    # Change agent's aid here also?
    return agent
  
  def mutate_tuple(self, atuple, newid=True):
    # Ensure that we set the first element of the tuple to a new id value
    newlist = list(atuple)
    condition = atuple[-1]
    tuple_min = HumanData.tuple_min[condition]
    tuple_max = HumanData.tuple_max[condition]
    tuple_sd = HumanData.tuple_sd[condition]
    for i in range(1,len(atuple)-1):
      if random.random() > Evolver.prob_mutate:
        continue
      # Add some random noise to the value
      newval = atuple[i] + random.gauss(0, tuple_sd[i]*self.mutation_magnitude)
      # Clip the value to range, plus expansion
      halfrange = float(tuple_max[i] - tuple_min[i])/2
      newval = min(tuple_max[i] + halfrange*self.range_expansion, 
                   max(tuple_min[i] - halfrange*self.range_expansion, 
                       newval))
      newlist[i] = newval
    
    if newid:
      newlist[0] = Evolver.get_new_dispo_id()
    
    return tuple(newlist)
