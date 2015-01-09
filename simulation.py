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

from configuration import *
from graph import *
from analyzer import *
from agentgroup import *
from clientwaiter import *    
from humanagent import *
from simagent import *
from db_logger import *

 

class simulation:
  def __init__(self):
    pass

  def setup(self, graph, config):
    self.cfg = config
    self.G = graph.copy()
    self.cfg._Gptr = self.G
    self.initgraph()
    self.initagents()
    self.initgroups()
    self.initbias()
    self.init_ultimatum()
    self.cfg._agentdict = self.agentdict
    self.cfg._groupdict = self.groupdict
    #self.cfg._dblog = dblog
    return True
  
  def init_ultimatum(self):
    sims = [a for a in self.agents if not a.type == 'human']
    
    # Divide up sims between nice, mean, fair, and random
    # For now, do this randomly?
    dispositions = ['nice', 'mean', 'fair', 'random']
    dstart = random.randint(0,3)
    for i,s in enumerate(sims):
      #disposition = random.choice(dispositions)            # Randomly assign dispostions
      disposition = dispositions[(i+dstart) % len(dispositions)]     # Assign dispositions in order, repeating
      if disposition == 'nice':
        s.ultimatum_init('normal',7,1)
      elif disposition == 'mean':
        s.ultimatum_init('normal',3,1)
      elif disposition == 'fair':
        s.ultimatum_init('normal',5,1)
      elif disposition == 'random':
        s.ultimatum_init('uniform',1,9)
      s.disposition = disposition
    
  
  def run_ultimatum(self):
    # For each (human) agent, play x rounds of UG with each of its neighbors
    # (and for agents neighboring human agents)
    # (so each human should play each role x times with each neighbor)
    humans = self.humans
    sims = [a for a in self.agents if not a.type == 'human']
    
    if not humans:
      return
  
    for h in humans:
      h.ultimatum_init()
    
    human_nodes = [h.id for h in humans]
    halfjobs = self.G.edges(human_nodes)
    print halfjobs
    jobs = halfjobs + [(v,u) for u,v in halfjobs]
    random.shuffle(jobs)
    
    self.idnodes = dict( (a.id, a) for a in self.agents )
    
    free = self.free = [True]*self.cfg.n
    self.cv = threading.Condition()
    #self.semlock = threading.Semaphore(len(human_nodes))
    #self.ready = threading.Event()
    threads = []
    self.cv.acquire()
    print 'cv acquired'
    print "Jobs to start:", jobs
    while len(jobs):
      ## WAIT for notification
      #self.semlock.acquire()
      #self.ready.clear()
      newjobs = []
      for u,v in jobs:
        if free[u] and free[v]:
          #jobs.remove((u,v))
          free[u] = False
          free[v] = False
          # IN NEW THREAD:
          t = threading.Thread(target=self.ultimatum_thread, args=(u,v))
          t.daemon = True
          print 'starting thread between',u,'and',v
          threads.append(t)
          t.start()
        else:
          newjobs.append( (u,v) )  # This seems stupid, but at least we don't modify jobs while looping
      if len(jobs) != len(newjobs):
        print "Jobs remaining:", newjobs
      jobs = newjobs
      #print 'waiting on notify'
      self.cv.wait(5.0)
      #print 'wait is done'
      #self.semlock.release()
      #self.cv.release()
    self.cv.release()
    
    ## Need to wait until all threads are done!!
    print "Waiting until all games are done."
    active_threads = True
    while active_threads:
      active_threads = False
      for t in threads:
        active_threads = active_threads or t.is_alive()
      time.sleep(1.0)
      
    for h in humans:
      h.u_review()
       
  def ultimatum_thread(self, giver_id, receiver_id):
    print "Running", self.cfg.ultimatum_niter,"ultimatums between", (giver_id, receiver_id)
    for i in range(self.cfg.ultimatum_niter):
      self.ultimatum(giver_id, receiver_id)
    print (giver_id, receiver_id),'ULTIMATUMS DONE'
    #print (giver_id, receiver_id),'acquiring cv'
    self.cv.acquire()
    self.free[giver_id] = True
    self.free[receiver_id] = True
    ## NOTIFY
    #print (giver_id, receiver_id),'cv acquired'
    #print (giver_id,receiver_id),'notifying'
    self.cv.notify()
    #print (giver_id,receiver_id),'notified'
    self.cv.release()
    #print (giver_id,receiver_id),'released'
    #self.semlock.release()
    #self.ready.set()
    
  def ultimatum(self, giver_id, receiver_id):
    c1 = self.idnodes[giver_id]
    c2 = self.idnodes[receiver_id]
    
    stime = time.time()
    
    c1.ultimatum(c2.id)
    c2.ultimatum(c1.id)
    
    c2.wait_offer(c1.id)
    amount = c1.ask_for_offer(c2.id)
    
    print c2.id,"now deciding"
    c1.wait_decide(c2.id)
    print "decide_offer"
    result = c2.decide_offer(c1.id, amount)
    print c2.id, "accepts?", result
    
    c1.show_conclusion_u(c2.id, amount, result, 0)
    c2.show_conclusion_u(c1.id, amount, result, 1)
    
    etime = time.time()
  
    self.cfg._dblog.log_ultimatum(giver_id, receiver_id, amount, result, stime, etime)
  
  
  def run(self, endtime=0):
    cfg = self.cfg
    n = cfg.n
    agents = self.agents
    groups = self.groups
    
    lastteams = [0]*n
    iters = 0
    deaditers = 0 
    enditer = cfg.nsteps
    
    emptygroups = []
    
    # Hide ratings during instructions screen  (now handled by humanagent class)
    #if cfg._do_ratings:
    #  for a in self.humans:
    #    a.hideratings()     
    
    ### PARALLEL
    if cfg._threaded_sim and self.humans:
      mythreads = []
      for a in self.humans:
        ## Should only start threads for the human agents
        t = threading.Thread(target=a.instructions)
        mythreads.append(t)
        t.start()
      for t in mythreads:
        t.join()
    elif self.humans:
      for a in self.humans:
        a.instructions()
    
    #print "Instructions done; press ENTER"  ##TEMP HACK!!!
    #raw_input()
    
    # Show ratings after instructions screen  (now handled by humanagent class)
    if cfg._do_ratings:
      for a in self.humans:
        a.showratings()
    
    if cfg._verbose > 7:
      cfg.printself()
    
    for a in self.humans:
      cfg._dblog.log_topo(self.cfg.simnumber, a)
    
    print "Beginning run!"
    trunstart = time.time()
    
    try:
     for iternum in xrange(cfg.nsteps):
      tstart = time.time()
      
      self.cfg.iternum = iternum
      
      ### PARALLEL - apply
      if cfg._threaded_sim:
        mythreads = []
        for a in random.sample(agents, n):
          ## Should only start threads for the human agents
          if a.slow:
            t = threading.Thread(target=a.propose)
            mythreads.append(t)
            t.start()
          else:
            a.propose()
        for t in mythreads:
          t.join()
      else:
        for a in random.sample(agents, n):
          a.propose()
      
      ### PARALLELIZE
      if cfg.groups_can_merge:
        for g in random.sample(groups, n):
          if len(g.agents) > 1: # or len(g.applications):
            g.propose()
      
      ### PARALLEL - acceptvote
      if cfg._threaded_sim:
        mythreads = []
        for g in random.sample(groups, n):
          ## Should only start threads for the human agents
          if len(g.agents):
            g.update()
            if g.slow:
              t = threading.Thread(target=g.consider)
              mythreads.append(t)
              t.start()
            else:
              g.consider()
        for t in mythreads:
          t.join()
      else:
        for g in random.sample(groups, n):
          if len(g.agents): # or len(g.applications):
            g.consider()
      
      ### SERIAL - group merge
      if cfg.groups_can_merge:
        for g in random.sample(groups, n):
          if len(g.agents): # or len(g.applications):
            g.considermerge()
      
      ### SERIAL - join
      for a in random.sample(agents, n):
        if len(a.acceptances):
          a.consider()
      
      ### SERIAL - expel agents
      expelee = None
      if cfg.expel_agents:
        emptygroups = [g for g in groups if not len(g.agents)]
        for g in random.sample(groups, n):
          if len(g.agents) > 1:
            expelee = g.expel_agent()
            if expelee is not None:
              newgroup = emptygroups.pop()
              expelee.switchgroup(newgroup)

      ### PARALLEL - postprocess_iter
      if cfg._threaded_sim:
        mythreads = []
        for a in random.sample(agents, n):
          ## Should only start threads for the human agents
          if a.slow:
            t = threading.Thread(target=a.postprocess_iter)
            mythreads.append(t)
            t.start()
          else:
            a.postprocess_iter()
        for t in mythreads:
          t.join()
      else:
        for a in random.sample(agents, n):
          a.postprocess_iter()

      tend = time.time()

      if cfg._draw_graph:
        G = cfg._Gptr
        if not cfg._pause_graph:
          plt.ion()
        plt.clf()
        ncolors = [G.graph['teamcolors'][a.group.id] for a in agents]
        
        weights = [dat['weight'] for u,v,dat in G.edges(data=True)]
        maxweight, minweight = float(max(weights)), float(min(weights))
        maxwidth = 4.0
        if maxweight == minweight:   # Handle graphs where all weights are the same.
          widths = 1.0
        else:
          widthconv = maxwidth / maxweight
          widths = [abs(w) * widthconv + 1.0 for w in weights]
        colors = ['red', 'black']
        ecolors = [colors[w >= 0] for w in weights]
        
        nx.draw(G,pos = G.graph['layout'], node_color=ncolors, font_color='w', width=widths, edge_color=ecolors)
        plt.draw()
        if cfg._pause_graph:
          plt.show()        

      if cfg._pause_every_step:
        k = raw_input()
        while len(k) > 1:
          print eval(k)
          k = raw_input()
      
      # Check if anything has changed
      teams = [a.group.id for a in agents]
      print lastteams
      print teams
      if teams == lastteams:
        deaditers += 1
        print "DEADITERS:", deaditers
      else:
        deaditers = 0
      
      if cfg._verbose > 2:
        print "Iteration", iternum, "complete in", round(tend-tstart, 2), "seconds"
      
      cfg._dblog.log_simtime(cfg.simnumber, iternum, tstart, tend)
      
      
      ## TERMINATE SIM CONDITIONS
      if deaditers > cfg.deaditers: # or iternum > cfg.nsteps:
        print "ENDING SIM: REACHED CONVERGENCE"# OR OUT OF STEPS"
        enditer = iternum
        break
      else:
        lastteams = teams
        iters += 1
      
      if endtime and time.time() > endtime:
        print "ENDING SIM: OUT OF TIME"
        enditer = iternum
        break
        
      if cfg._draw_graph:
        time.sleep(cfg.delaytime)
     
     else:
       print "ENDING SIM: OUT OF STEPS"
       enditer = iternum
        
    except KeyboardInterrupt:
      print "Simulation early termination due to user interrupt!"
      print "Summarizing results up to this point"
      time.sleep(1)

    #trunend = time.time()
    
    
    # Calculate average pay for agent of each skill configuration
    # (used when agents compare their pay to global pay)
    globalpay = {}
    for a in agents:
      a.update()
      try:
        globalpay[tuple(a.skills)].append(a.nowpay)
      except KeyError:
        globalpay[tuple(a.skills)] = [a.nowpay]
    for s, pay in globalpay.iteritems():
      globalpay[s] = sum(globalpay[s])/len(globalpay[s])
    
    tpubstart = time.time()
    if not cfg._do_publicgoods:
      if self.humans:
        for a in self.humans:
          a.postprocess()
      
      if cfg.dynamic_graph:
        for a in agents:
          a.postprocess(globalpay)
        
        for g in groups:
          g.postprocess()
    else:
      ## PUBLIC GOODS GAME
      if self.humans:
        for g in groups:
          if len(g.agents):
            g.update()
        
        ## Acquire public goods contributions
        pgdict = {}     # Stores agent contribution choices
        if cfg._threaded_sim:
          mythreads = []
          for a in self.agents:
            if len(a.group.agents) == 1:
              t = threading.Thread(target=a.postprocess())
              mythreads.append(t)
              t.start()
            elif a.slow:
              t = threading.Thread(target=a.publicgoods, args=(pgdict,))
              mythreads.append(t)
              t.start()
            else:
              #contrib, keep = a.publicgoods()
              a.publicgoods(pgdict)
            #pgdict[a] = (contrib, keep)    # This will get added by the publicgoods threads
          for t in mythreads:
            t.join()
        else:
          for a in self.agents:
            if len(a.group.agents) == 1: 
              a.postprocess()
            #contrib, keep = a.publicgoods()
            #pgdict[a] = (contrib, keep)    # This will get added by the publicgoods threads
            else:
              a.publicgoods(pgdict)
        
        ## Distribute money back to agents
        mythreads = []
        for g in groups:
          if len(g.agents) <= 1: 
          #  for a in g.agents:
          #    a.postprocess()
            continue
          teampays = {a.id:pgdict[a][0] for a in g.agents}
          sharedpay = sum(teampays.values())*(1.0+cfg.pubgoods_mult*0.01)/float(len(g.agents))
          for a in g.agents:
            apay = pgdict[a][1] + sharedpay
            if a.type == 'human':
              a.showratings()
            if a.slow and cfg._threaded_sim:
              t = threading.Thread(target=a.publicgoods_postprocess, args=(apay, teampays))
              mythreads.append(t)
              t.start()
            else:
              a.publicgoods_postprocess(apay, teampays)
            a.nowpay = apay
        if cfg._threaded_sim:
          for t in mythreads:
            t.join()
    
    trunend = time.time()
    
    # Log time spent in public goods
    # Total sim time is logged in tfsummary/tfdata
    cfg._dblog.log_simtime(cfg.simnumber, -1, tpubstart, trunend)
  
    del self.cfg.iternum

    self.G.graph['iterations'] = iternum+1
    self.G.graph['start_time'] = trunstart
    self.G.graph['end_time'] = trunstart
    self.G.graph['elapsed_time'] = trunend - trunstart
    
    cfg._dblog.log_conclusion(groups, self.cfg.simnumber)
    #cfg._dblog.log_simtime(cfg.simnumber, -1, trunstart, trunend)
    
    
  
  def reset(self, Gdone=None):
    if Gdone is None:
      self.G = self.export()  # Reset G with the new agent values
    else:
      self.G = Gdone
    self.cfg._Gptr = self.G
    for a in self.agents:
      a.reset()
    self.initgroups()
    self.cfg.reset()
    
  def initgraph(self):
    pass
    
  def makesimagents(self, nodes):
    cfg = self.cfg
    n = len(nodes)
    if cfg.ndumb < 1 and cfg.ndumb > 0:
      ndumb = int(n * cfg.ndumb)
    else:
      ndumb = cfg.ndumb
    
    scramblenodes = random.sample(nodes, n)
    dumbnodes = scramblenodes[0:ndumb]
    simnodes = scramblenodes[ndumb:]
    
    return [dumbagent(cfg,adat=dat) for nid, dat in dumbnodes] + [simagent(cfg,adat=dat) for nid,dat in simnodes]
    
  def initagents(self):
    cfg = self.cfg
    n = cfg.n
    
    if cfg.nhumans > 0:
      allnodes = self.G.nodes(data=True)
      #random.shuffle(allnodes)
      humanodes = allnodes[0:cfg.nhumans]
      simnodes = allnodes[cfg.nhumans:]
      #humannodes = random.sample(allnodes, cfg.nhumans)
      self.humans = [humanagent(cfg,conn,adat=dat) for conn,(nid,dat) in zip(cfg.conns, humanodes)]
      #simagents = [simagent(cfg,adat=dat) for nid,dat in simnodes]
      simagents = self.makesimagents(simnodes)
      agents = self.humans + simagents
    else:
      #agents = [simagent(cfg,adat=dat) for nid,dat in self.G.nodes_iter(data=True)]
      agents = self.makesimagents(self.G.nodes(data=True))
      self.humans = []
    
    agentdict = dict([(a.id, a) for a in agents])
    
    cfg._agentdict = agentdict
    
    for a in agents:
      a.neighbors()
      a.nbrweight()
    
    self.agents = agents
    self.agentdict = agentdict
    
  # Initialize each agent to be its own degenerate group
  def initgroups(self):
    #groups = dict((a.id, group(a.id, self.cfg)) for a in self.agents)
    groups = [group(a.id, self.cfg) for a in self.agents]
    for a, g in izip(self.agents, groups):
      g.addfirst(a)
      a.group = g
      
    self.groups = groups
    self.groupdict = {g.id:g for g in groups}
    
  def initbias(self):
    cfg = self.cfg
    # give each agent biases
    if cfg.bias:        ## TEMPORARY: or True
      if cfg.skillseed is not None:
        currstate = random.getstate()
        random.seed(cfg.skillseed)
      for a in self.agents:
        a.randbiases()
      if cfg.skillseed is not None:
        random.setstate(currstate)
  
  def export(self):
    G = self.G
    for a in self.agents:
      adat = G.node[a.id]
      adat['id'] = a.id
      adat['skills'] = a.skills
      adat['switches'] = a.switches
      adat['group'] = a.group.id
      adat['nowpay'] = a.nowpay
      adat['type'] = ('human' if a.type=='human' else ('dumb' if a.dumb else 'greedy'))
    
    return G
  
