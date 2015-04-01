#
# simserver.py - master server that handles multiple rounds of team
#                formation with human and simulated agents, and logs to
#                an SQLite3 database
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
from configuration import Configuration, MultiConfig
from simhumanagent import *


def heartbeat_thread():
  while True:
    time.sleep(60)
    print ".",

  
if __name__ == '__main__':
  alt_options = ['single', 'auto']
  
  dblog = DBLogger('simlog.db')
  Configuration._dblog = dblog
  dblog.start_batch_insert_thread()
  
  DYNAMIC = True   # Temporary; should be replaced with command-line or configuration.py option
  KEEP_GRAPH = True
  
  if len(sys.argv) == 1 or sys.argv[1] not in alt_options:      ## MAIN SETTING:  Run a series of sims until time expires.
    allconfs = MultiConfig()
    if len(sys.argv) > 1:
      outfile = sys.argv[1]
    else:
      outfile = None
    
    cw = ClientWaiter()
    conns = cw.getclients()

    ## Log this session's configuration
    u_rounds = 0 if not Configuration._do_ultimatum else Configuration.ultimatum_niter
    dblog.log_config(u_rounds, Configuration._do_intro_sim, Configuration.do_publicgoods,
                     Configuration.hide_publicgoods, Configuration.pubgoods_mult, Configuration.do_ratings,
                     Configuration._time_limit-Configuration._margin_time, len(conns),
                     Configuration.show_other_team_members, Configuration.keep_teams,
                     DYNAMIC, KEEP_GRAPH,
                     Configuration.show_global_ratings, Configuration.show_nhistory)
    
    # Load in sim human data, if requested
    if configuration.simhumans:
      configuration.hdata = humandata(configuration.simhuman_file)

    # Start the heartbeat
    if Configuration._verbose > 4:
      hthread = threading.Thread(target=heartbeat_thread)
      hthread.daemon = True
      hthread.start()
    
    # Start the timer
    starttime = time.time()
    
    ## BEGIN INTRO SIMULATION
    ## Start with a well-defined simulation (like WS4 with no rewire) to make sure that humans play each other, and play a reasonable number of AIs
    
    # Standard starter configuration
    std = standardconfig = Configuration()
    if DYNAMIC:
      std.groups_can_merge = False
      std.expel_agents = False
      std.fully_connect_groups = True
      #std.n = 16   # Get this from configuration class
      #std.connections= 2
      std.prob_rewire = 0
      std.graph_type = 'random_cycle4_zip'
      std.strategy = 'random'
      std.ndumb = 0
    else:
      std.groups_can_merge = False
      std.expel_agents = False
      std.fully_connect_groups = False
      #std.n = 16   # Get this from configuration class
      std.connections= 6
      std.prob_rewire = 0
      std.graph_type = 'complete_graph' #'connected_watts_strogatz_graph'
      std.nskills = 4
      std.strategy = 'random'
      std.ndumb = 0
    
    std.simnumber = 0
    std.nhumans = len(conns)
    std._conns = conns
    
    gm = GraphManager(std)
    gm.setup()
    sim = simulation()
    sim.setup(gm.G, std)
    
    pglog = {a.id:[] for a in sim.agents}
    
    # Init video only once!
    for a in sim.humans:
      a.initvideo()
    
    atypes = sorted([(a.id,'human' if a.type == 'human' else a.disposition) for a in sim.agents])
    dblog.log_agentconfig(atypes)
    
    ## GIVE INTRO SURVEY HERE
    mythreads = []
    for a in sim.humans:
      t = threading.Thread(target=a.introsurvey)
      mythreads.append(t)
      t.start()
    for t in mythreads:
      t.join()
  
    if Configuration._do_video:
      for a in sim.humans:
        a.startcapture()
  
    if Configuration.do_ratings:
      for a in sim.humans:
        a.initratings(range(Configuration.n))
        a.showratings()
      std.lastratings = {}
  
    ## RUN ULTIMATUM HERE
    if std._do_ultimatum:
      sim.run_ultimatum()
      raw_input("ULTIMATUM DONE. PRESS ENTER TO CONTINUE.")
    
    ## RUN INTRO SIM HERE
    print "Beginning intro simulation"
    if std._do_intro_sim:
      sim.run()
      Gdone = sim.export()
      
      ann = Analyzer()
      ann.load(Gdone, std)
      ann.groupsummary()
      ann.summary()
      ann.dumpsummarydb(dblog)
      if outfile: 
        ann.dumpsummary(outfile)
      if std._draw_graph_after_sim or std._draw_graph:
        ann.drawgraph()
        print "Close plot to end program"
        plt.show()
      
      # update public goods history
      for aid, contribpct in sim.pgsummary.iteritems():
        pglog[aid].append(contribpct)
      #pghistory = {aid:(sum(p)/len(p)) for aid,p in pglog.iteritems()}   # for average contrib
      for a in sim.agents:
        a.updatehistory(pglog)
        
      std.simnumber += 1
    
    Agent.agentid=0
    ## END INTRO SIMULATION
    
    
    if KEEP_GRAPH:
      if std.social_sim_agents and std.keep_teams:   ## TESTING
        std.expel_agents = True     # only on 2nd and future sims; not necessary in first game.
      
      cfg = std     # Grab the standard config 
      #G = Gdone     # Grab the graph (assumes we did the intro sim)
      #sim = simulation()   # Keep the intro simulation
      sim.reset()   # Reset after the intro sim
      
      i = 1
      lastflush = time.time()
      while True:   # Run sims ~forever~
        if cfg.reset_graph_iters and cfg.simnumber and not cfg.simnumber % cfg.reset_graph_iters:
          # Reset agents, graph, everything.
          # Only for automated simulations
          cfg.simnumber = 0
          #for a in sim.agents: # Done by sim.reset
          #  a.reset()
          gm.setup()
          sim.setup(gm.G, cfg)  # This re-inits agent dispositions...
          #sim.reset(gm.G)
          for a in sim.agents:  # Not done by any other reset
            a.pgmem = {}
          dblog.sessionid += 1  # Dangerous, but should be ok for these sims.
          atypes = sorted([(a.id,'human' if a.type == 'human' else a.disposition) for a in sim.agents])
          dblog.log_agentconfig(atypes)
          
        #sim.setup(Gdone, cfg) #?
        #or is there some other way to reset teams without resetting the graph?
        if cfg._verbose > 3:
          cfg.printself()
        
        sim.run(endtime = starttime+cfg._time_limit*60)
        Gdone = sim.export()
        
        ann = Analyzer()
        ann.load(Gdone, cfg)
        if cfg._verbose > 3:
          ann.groupsummary()
          ann.summary()
        ann.dumpsummarydb(dblog)
        if outfile: 
          ann.dumpsummary(outfile)
        if cfg._draw_graph_after_sim or cfg._draw_graph:
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
        
        if tnow - lastflush > 5.0:
          print "Database flush!"
          dblog.flush_inserts()
          lastflush = tnow
        
        if cfg._verbose > 0:
          print "Sim", cfg.simnumber, "done;", elapsed, "min elapsed"
      
        # if near time limit - quit
        if time.time() > starttime + (cfg._time_limit-cfg._margin_time)*60:
          print "OUT OF TIME!"
          break
        
        Agent.agentid=0
        sim.reset()
        cfg.simnumber += 1
        
        
      if Configuration._do_video:
        for a in sim.humans:
          a.endcapture()  
      
      if Configuration.do_ratings:
        for a in sim.humans:
          a.disableratings()
        
        
      ## END IF DYNAMIC
    
    else:
      ## RUN MULTIPLE CONFIGURATIONS HERE
      # Get all configurations we want to run
      confs = [conf for conf in allconfs.itersims()]
      #print [c.printself() for c in confs[0:10]]
      random.shuffle(confs)
      
      for i, conf in enumerate(confs):
        conf.simnumber = i+1
      
      #for conf in allconfs.itersims():
      for i,cfg in enumerate(confs):
        
        cfg.nhumans = len(conns)
        cfg._conns = conns
        
        gm = GraphManager(cfg)
        try:
          gm.setup()
        except Exception as e:      ### TEMPORARY general catch
          print "Bad configuration; moving on"
          continue
        sim = simulation()
        sim.setup(gm.G, cfg)
        cfg.printself()
        
        sim.run(endtime = starttime+cfg._time_limit*60)
        Gdone = sim.export()
        
        ann = Analyzer()
        ann.load(Gdone, cfg)
        ann.groupsummary()
        ann.summary()
        ann.dumpsummarydb(dblog)
        if outfile: 
          ann.dumpsummary(outfile)
        if cfg._draw_graph_after_sim or cfg._draw_graph:
          ann.drawgraph()
          print "Close plot to end program"
          plt.show()
        
        Agent.agentid=0
        
        tnow = time.time()
        elapsed = (tnow - starttime)/60
        print "Elapsed time:", round(elapsed,2)
        
        # if near time limit - quit
        if time.time() > starttime + (cfg._time_limit-cfg._margin_time)*60:
          print "OUT OF TIME!"
          break
        
      if Configuration._do_video:
        for a in sim.humans:
          a.endcapture()  
      
      if Configuration.do_ratings:
        for a in sim.humans:
          a.disableratings()
          
      ## END MULTICONFIG ELSE
      
    ## END BIG IF STATEMENT
    
    ## GIVE EXIT SURVEY HERE
    mythreads = []
    for a in sim.humans:
      t = threading.Thread(target=a.exitsurvey)
      mythreads.append(t)
      t.start()
    for t in mythreads:
      t.join()
    
    # Collect final pay from the human agents
    paydata = []
    for a in sim.humans:
      paydata.append( (a.id, a.finalpay) )
    dblog.log_finalpay(paydata)
    
    #if Configuration.do_ratings:
    #  for a in sim.humans:
    #    a.hideratings()
    
    dblog.log_sessionend()
    k=raw_input('END OF EXPERIMENT. Press Enter to terminate server.')
      
  elif sys.argv[1] == 'single':    # Run a single ... exit survey?
    cfg = Configuration()
    
    cw = ClientWaiter()
    conns = cw.getclients()
    cfg.nhumans = len(conns)
    cfg._conns = conns
    
    gm = GraphManager(cfg)
    gm.setup()
    sim = simulation()
    sim.setup(gm.G, cfg)
    
    
    #sim.run_ultimatum()
    
    ## TEST INTRO/EXIT SURVEYS HERE
    #mythreads = []
    #for a in sim.humans:
      #t = threading.Thread(target=a.introsurvey)
      #t.start()
      #mythreads.append(t)
    #for t in mythreads:
      #t.join()
      
    mythreads = []
    for a in sim.humans:
      t = threading.Thread(target=a.exitsurvey)
      mythreads.append(t)
      t.start()
    for t in mythreads:
      t.join()
    ## END TEST
    
    sim.run()
    Gdone = sim.export()
    
    ann = Analyzer()
    ann.load(Gdone, cfg)
    ann.groupsummary()
    ann.summary()
    ann.drawgraph()
    print "Close plot to end program"
    plt.show()
  
  elif sys.argv[1] == 'auto':     ## Automated option: run sims without humans and log to a file
    allconfs = MultiConfig()
    outfile = sys.argv[2]
    
    confs = [conf for conf in allconfs.itersims()]
    random.shuffle(confs)
    
    #for conf in allconfs.itersims():
    for conf in confs:
      conf.printself()
      gm = GraphManager(conf)
      gm.setup()
      sim = simulation()
      if sim.setup(gm.G, conf):
        sim.run()
      Gdone = sim.export()
      ann = Analyzer()
      ann.load(Gdone, conf)
      ann.summary()
      ann.dumpsummary(outfile)
      if conf._pause_after_sim:
        k=raw_input()
      Agent.agentid = 0 
