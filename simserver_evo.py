#
# simserver_evo.py - master server that performs evolutionary simulation of 
#                    team formation, with successful agents duplicated and 
#                    unsuccessful agents dropped
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


import time
import random
import sys
import matplotlib.pyplot as plt
import threading

from graph import GraphManager
from analyzer import Analyzer
from agentgroup import Agent
from clientwaiter import ClientWaiter
from db_logger import DBLogger
from simulation import simulation
from configuration import Configuration, MultiConfig, RepliConfig
from simhumanagent import SimHumanAgent, HumanData
from evolver import Evolver

if __name__ == '__main__':
  dblog = DBLogger('simlog.db')
  Configuration._dblog = dblog
  dblog.start_batch_insert_thread()
  
  # Get human players (optional)
  #cw = ClientWaiter()
  #conns = cw.getclients()
  
  
  n_generations = 200
  pause_after_generation = True
  
  
  if len(sys.argv) > 1:
    condition = sys.argv[1]
    if condition == 'private':
      Configuration.show_global_ratings = False
      Configuration.alt_pubgoods = False
    elif condition == 'public':
      Configuration.show_global_ratings = True
      Configuration.alt_pubgoods = False
    elif condition == 'varmult':
      Configuration.show_global_ratings = True
      Configuration.alt_pubgoods = True
      Configuration.pubgoods_mult = -1
  

  #u_rounds = 0 
  #dblog.log_config(u_rounds, Configuration._do_intro_sim, Configuration.do_publicgoods,
                    #Configuration.hide_publicgoods, Configuration.pubgoods_mult, Configuration.do_ratings,
                    #Configuration._time_limit-Configuration._margin_time, len(conns),
                    #Configuration.show_other_team_members, Configuration.keep_teams,
                    #DYNAMIC, KEEP_GRAPH,
                    #Configuration.show_global_ratings, Configuration.show_nhistory)
    
  
  dbfile = 'simlog_EXPR1_latest.db'
  humandata = HumanData(Configuration.simhuman_file)
  #allconfs = RepliConfig(dbfile, humandata)
  outfile = None
  
  evolver = Evolver(humandata)
  
  ## TODO: create a new table in the database for agent configuration
  # done
  
  # Set up a configuration and a simulation
  
  starttime = time.time()
  lastflush = time.time()
  
  lastagents = None
  
  try:
    for i in range(n_generations):
      print "STARTING NEW GENERATION"
      
      # Create the configuration here
      conf = Configuration()    # TEST:  not sure if default is what we want.
      conf.lastratings = {}
      
      # log config?
      u_rounds = 0 
      dblog.log_config(u_rounds, Configuration._do_intro_sim, Configuration.do_publicgoods,
                    Configuration.hide_publicgoods, Configuration.pubgoods_mult, Configuration.do_ratings,
                    Configuration._time_limit-Configuration._margin_time, 0,
                    Configuration.show_other_team_members, Configuration.keep_teams,
                    True, True,
                    Configuration.show_global_ratings, Configuration.show_nhistory)
      
      # Start the new simulation
      gm = GraphManager(conf)
      gm.setup()
      
      # Create agents here
      newagents = evolver.genagents(conf, prevagents=lastagents)
      # This resets final pay
      
      # Print data about the agents
      print "Agents:"
      print ', '.join([str(agent.probdata['uuid']) for agent in newagents])
      
      sim = simulation()
      sim.setup(gm.G, conf, newagents)
      
      # Reset this for each new configuration
      pglog = {a.id:[] for a in sim.agents}
        
      for i in range(conf.reset_graph_iters):
        sim.run(endtime = starttime+conf._time_limit*60)
        Gdone = sim.export()
        
        ann = Analyzer()
        ann.load(Gdone, conf)
        if conf._verbose > 3:
          ann.groupsummary()
          ann.summary()
        ann.dumpsummarydb(dblog)
        if outfile: 
          ann.dumpsummary(outfile)
        if conf._draw_graph_after_sim or conf._draw_graph:
          ann.drawgraph()
          print "Close plot to end program"
          plt.show()
        
        # update public goods history
        for aid, (contrib, total) in sim.pgsummary.iteritems():
          #contribpct = float(contrib)/total
          pglog[aid].append( (contrib, total) )
        #pghistory = {aid:(sum(p)/len(p)) for aid,p in pglog.iteritems()}   # for average contrib
        for a in sim.agents:
          a.updatehistory(pglog)
        
        tnow = time.time()
        elapsed = (tnow - starttime)/60
        #if cfg._verbose > 3:
        #  print "Elapsed time:", round(elapsed,2)
        
        if tnow - lastflush > 2.0:
          print "Database flush!"
          dblog.flush_inserts()
          lastflush = tnow
        
        sim.reset()
        conf.simnumber += 1
    
      print "Generation done!"
      
      ## Collect final pay from the human agents
      paydata = []
      for a in sim.agents:
        paydata.append( (a.id, a.finalpay) )
      dblog.log_finalpay(paydata)
      
      ## Reset agents, graph, everything.
      ## Only for automated simulations
      conf.simnumber = 0
      ##for a in sim.agents: # Done by sim.reset
      ##  a.reset()
      #gm.setup()
      #sim.setup(gm.G, cfg)  # This re-inits agent dispositions...
      ##sim.reset(gm.G)
      atypes = sorted([(a.id,'human.{:02d}.{}'.format(conf.sessionid, a.id) if a.type == 'human' else a.disposition) for a in sim.agents])
      dblog.log_agentconfig(atypes)
      
      # Record agent parameters here
      for agent in sim.agents:
        dblog.log_simhumanagent(agent)
      
      lastagents = sim.agents
      
      # Flush database before starting new session to avoid concurrency issues
      dblog.force_commit()
      dblog.flush_inserts()
      #dblog.log_sessionend()
      #dblog.log_newsession()
      dblog.log_newsession_fast()
      #dblog.sessionid += 1
      
      tnow = time.time()
      elapsed = (tnow - starttime)/60
      print "Elapsed time:", round(elapsed,2)
      
      if conf._pause_after_sim:
        k=raw_input()
      
      ## TODO: In this location, assess fitness, and assign new agents.
  
  except KeyboardInterrupt: # Catch CTRL-C
    print "Caught CTRL-C; cleaning up"
    dblog.flush_inserts()
    print "Done flushing db inserts"
  
  # save tuple data on best agents to a file
  
  k=raw_input('END OF EXPERIMENT. Press Enter to terminate server.')

