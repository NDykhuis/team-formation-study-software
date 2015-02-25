from operator import itemgetter
import numpy as np
import time
from time import strftime
import networkx as nx
import os
import random
import math
import sys
import datetime
from itertools import izip
import fcntl

from graph import *
from analyzer import *
from agentgroup import *
from clientwaiter import *    
from humanagent import *
from simagent import *
from db_logger import *
from simulation import *
from configuration import *



  
if __name__ == '__main__':
  alt_options = ['single', 'auto']
  
  dblog = db_logger('simlog.db')
  configuration._dblog = dblog
  dblog.start_batch_insert_thread()
  
  DYNAMIC = True   # Temporary; should be replaced with command-line or configuration.py option
  KEEP_GRAPH = True
  
  if len(sys.argv) == 1 or sys.argv[1] not in alt_options:      ## MAIN SETTING:  Run a series of sims until time expires.
    allconfs = multiconfig()
    if len(sys.argv) > 1:
      outfile = sys.argv[1]
    else:
      outfile = None
    
    cw = clientwaiter()
    conns = cw.getclients()

    ## Log this session's configuration
    u_rounds = 0 if not configuration._do_ultimatum else configuration.ultimatum_niter
    dblog.log_config(u_rounds, configuration._do_intro_sim, configuration.do_publicgoods,
                     configuration.hide_publicgoods, configuration.pubgoods_mult, configuration.do_ratings,
                     configuration._time_limit-configuration._margin_time, len(conns),
                     configuration.show_other_team_members, configuration.keep_teams,
                     DYNAMIC, KEEP_GRAPH,
                     configuration.show_global_ratings, configuration.show_nhistory)
    
    # Start the timer
    starttime = time.time()
    
    ## BEGIN INTRO SIMULATION
    ## Start with a well-defined simulation (like WS4 with no rewire) to make sure that humans play each other, and play a reasonable number of AIs
    
    # Standard starter configuration
    std = standardconfig = configuration()
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
      std.nskills = 5
      std.strategy = 'random'
      std.ndumb = 0
    
    std.simnumber = 0
    std.nhumans = len(conns)
    std._conns = conns

    gm = graphmanager(std)
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
  
    if configuration._do_video:
      for a in sim.humans:
        a.startcapture()
  
    if configuration.do_ratings:
      for a in sim.humans:
        a.initratings(range(configuration.n))
        a.showratings()
  
    ## RUN ULTIMATUM HERE
    if std._do_ultimatum:
      sim.run_ultimatum()
      raw_input("ULTIMATUM DONE. PRESS ENTER TO CONTINUE.")
    
    ## RUN INTRO SIM HERE
    print "Beginning intro simulation"
    if std._do_intro_sim:
      sim.run()
      Gdone = sim.export()
      
      ann = analyzer()
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
    
    agent.agentid=0
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
        if cfg.reset_graph_iters and not i % cfg.reset_graph_iters:
          # Only for automated simulations
          cfg.simnumber = 0
          sim.setup(G, cfg)
          
        #sim.setup(Gdone, cfg) #?
        #or is there some other way to reset teams without resetting the graph?
        if cfg._verbose > 3:
          cfg.printself()
        
        sim.run(endtime = starttime+cfg._time_limit*60)
        Gdone = sim.export()
        
        ann = analyzer()
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
          print "Sim", cfg.simnumber, "done in", elapsed, "min"
      
        # if near time limit - quit
        if time.time() > starttime + (cfg._time_limit-cfg._margin_time)*60:
          print "OUT OF TIME!"
          break
        
        agent.agentid=0
        sim.reset()
        cfg.simnumber += 1
        
        
      if configuration._do_video:
        for a in sim.humans:
          a.endcapture()  
      
      if configuration.do_ratings:
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
        
        gm = graphmanager(cfg)
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
        
        ann = analyzer()
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
        
        agent.agentid=0
        
        tnow = time.time()
        elapsed = (tnow - starttime)/60
        print "Elapsed time:", round(elapsed,2)
        
        # if near time limit - quit
        if time.time() > starttime + (cfg._time_limit-cfg._margin_time)*60:
          print "OUT OF TIME!"
          break
        
      if configuration._do_video:
        for a in sim.humans:
          a.endcapture()  
      
      if configuration.do_ratings:
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
    
    #if configuration.do_ratings:
    #  for a in sim.humans:
    #    a.hideratings()
    
    dblog.log_sessionend()
    k=raw_input('END OF EXPERIMENT. Press Enter to terminate server.')
  
      
  elif sys.argv[1] == 'single':    # Run a single ... exit survey?
    cfg = configuration()
    
    cw = clientwaiter()
    conns = cw.getclients()
    cfg.nhumans = len(conns)
    cfg._conns = conns
    
    gm = graphmanager(cfg)
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
    
    ann = analyzer()
    ann.load(Gdone, cfg)
    ann.groupsummary()
    ann.summary()
    ann.drawgraph()
    print "Close plot to end program"
    plt.show()
  
  elif sys.argv[1] == 'auto':     ## Automated option: run sims without humans and log to a file
    allconfs = multiconfig()
    outfile = sys.argv[2]
    
    confs = [conf for conf in allconfs.itersims()]
    random.shuffle(confs)
    
    #for conf in allconfs.itersims():
    for conf in confs:
      conf.printself()
      gm = graphmanager(conf)
      gm.setup()
      sim = simulation()
      if sim.setup(gm.G, conf):
        sim.run()
      Gdone = sim.export()
      ann = analyzer()
      ann.load(Gdone, conf)
      ann.summary()
      ann.dumpsummary(outfile)
      if conf._pause_after_sim:
        k=raw_input()
      agent.agentid = 0 
