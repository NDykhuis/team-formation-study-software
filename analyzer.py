#
# analyzer.py - computes summary statistics on a completed simulation
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


import matplotlib.pyplot as plt
import colorsys
import networkx as nx
import fcntl
import datetime
import numpy as np

from configuration import *

class analyzer:
  def __init__(self):
    self.data = None
    pass
  
  def load(self, G, cfg):
    self.G = G
    self.cfg = cfg
    
    self.gengroups()
    self.analyze()
    
  def gengroups(self):
    groupagents = {}
    groupnowpay = {}
    groupskills = {}
    
    for n,dat in self.G.nodes_iter(data=True):
      g=dat['group']
      try:
        groupagents[g].append(n)
      except KeyError:
        groupagents[g]=[n]
      
      if g not in groupskills:
        groupskills[g] = [0]*self.cfg.nskills
      
      for i in range(self.cfg.nskills):
        groupskills[g][i] += dat['skills'][i]
      
    for g, skills in groupskills.iteritems():
      groupnowpay[g] = self.cfg.task(skills)# / len(groupagents[g])
      
    self.groupdat = {'agents':groupagents, 'nowpay':groupnowpay, 'skills':groupskills}
   
  def drawgraph(self):
    G = self.G
    cfg = self.cfg
    
    plt.ioff()
    
    if 'layout' in G.graph and cfg.springseed is not None:
      Glayout = G.graph['layout']
    else:
      if cfg.springseed is not None:
        currstate = np.random.get_state()
        np.random.seed(cfg.springseed)
      
      if cfg.graph_type in ['wheel_graph', 'star_graph', 'cycle_graph', 'path_graph', 'complete_graph']:
        Glayout = nx.circular_layout(G)
      else:
        pos = None
        if 'layout' in G.graph:
          pos = G.graph['layout']
        #Glayout = nx.spring_layout(G, weight=None)
        Glayout = nx.spring_layout(G, pos=pos)
        #Glayout = nx.graphviz_layout(G)
        
      if cfg.springseed is not None:
        np.random.set_state(currstate)
    
      
    agentids, agentdats = zip(*G.nodes(data=True))
    
    agentgroups = {}.fromkeys( dat['group'] for dat in agentdats )
    maxpay = max(max(dat['nowpay'] for dat in agentdats ), 1.0)
    
    hueval = [x*1.0/len(agentgroups) for x in range(len(agentgroups))]
  
    # Hue is based on group, value is based on % of max pay
    grouphues = dict(zip(agentgroups.keys(), hueval))
    ncolors = [colorsys.hsv_to_rgb(grouphues[dat['group']], 1, float(dat['nowpay'])/float(maxpay)) for dat in agentdats]
    
    # Weights
    weights = [dat['weight'] for u,v,dat in G.edges(data=True)]
    maxweight = float(max(weights))
    minweight = float(min(weights))
    maxwidth = 4.0
    if maxweight == minweight:   # Handle graphs where all weights are the same.
      widths = 1.0
    else:
      widthconv = maxwidth / maxweight
      widths = [abs(w) * widthconv + 0.25 for w in weights]
    colors = ['red', 'black']
    ecolors = [colors[w >= 0] for w in weights]
    #print sum(w >= 0 for w in weights), len(weights)
    
    ## SOME DEBUG OUTPUT
    print G.size(), nx.number_connected_components(G.to_undirected())
    
    plt.figure(1)
    plt.clf()
    if cfg.graph_type == 'grid_graph' and cfg._draw_grid:
      self.drawgrid(colors)
    else:
      nx.draw(G, pos=Glayout, node_color=ncolors, font_color='w', width=widths, edge_color=ecolors)
    
    plt.draw()

  def drawgrid(self, colors):
    dim = int(math.ceil(math.sqrt(self.cfg.n)))
    
    colors.extend([np.zeros(3) for i in range(dim*dim - len(colors))])
    colors = np.array(colors)
    colors = colors.reshape((dim, dim, 3))
    
    plt.imshow(colors, interpolation='none')
    

  def analyze(self):
    G = self.G
    cfg = self.cfg
    
    if cfg._dblog is not None:
      cfg.sessionid = cfg._dblog.sessionid
    
    apays = [dat['nowpay'] for n,dat in G.nodes_iter(data=True)]
    successes = [pay for pay in apays if pay > 0]
    
    data = {}
    data['Iterations'] = G.graph['iterations']
    data['Start time'] = G.graph['start_time']
    data['End time'] = G.graph['end_time']
    data['Elapsed time'] = G.graph['elapsed_time']
    
    data['Num groups'] = len(self.groupdat['nowpay'])
    data['Num successful groups'] = len([pay for pay in self.groupdat['nowpay'].itervalues() if pay > 0])
    data['Num successful agents'] = len(successes)
    data['Global wealth'] = sum(apays)
    data['Average earnings'] = sum(apays) / len(apays)
    data['Average earnings nonzero'] = sum(successes) / max(len(successes),1.0)
    data['Percent successful'] = len(successes) / float(len(apays))
    
    skills = [0]*cfg.nskills
    for n, dat in G.nodes_iter(data=True):
      askills = dat['skills']
      for i in range(len(skills)):
          skills[i] += askills[i]
    data["Total skills"] = skills
    
    breadth = 0
    depth = 0
    nskills = len(self.groupdat['skills'].itervalues().next())
    for gs in self.groupdat['skills'].itervalues():
      if max(gs) >= nskills:
        depth += 1
      if len([s for s in gs if s > 0]) >= nskills:
        breadth += 1
    
    data['Percent breadth groups'] = float(breadth)/len(self.groupdat['skills'])
    data['Percent depth groups'] = float(depth)/len(self.groupdat['skills'])
    
    def gini(payoffs):
      # from http://www.heckler.com.br/blog/2010/06/15/gini-coeficient-having-fun-in-both-sql-and-python/
      paysum = sum(payoffs)
      payprod = sum((i+1)*pay for i, pay in enumerate(sorted(payoffs, reverse=True)))
      N = len(payoffs)
      try:
        u = paysum / N
        G = (N+1.0)/(N-1.0) - (payprod/(N*(N-1.0)*u))*2.0
      except ZeroDivisionError:
        G = 0
      return G
    
    if len(successes):
      data['Gini global'] = gini(apays)
      data['Gini nonzero'] = gini(successes)
    else:
      data['Gini global'] = 0
      data['Gini nonzero'] = 0
      
    data["Switches"] = sum(dat['switches'] for n,dat in G.nodes_iter(data=True))/float(cfg.n)
    data["Number of edges"] = len(self.G.edges())
    data["Singletons"] = len([1 for agents in self.groupdat['agents'].itervalues() if len(agents) == 1])
    #data["Singleton_worth"] = sum(g.worth for g in groups if g.gsize == 1)
    
    hpays = [dat['nowpay'] for n,dat in G.nodes_iter(data=True) if dat['type'] == 'human']
    dpays = [dat['nowpay'] for n,dat in G.nodes_iter(data=True) if dat['type'] == 'dumb']
    gpays = [dat['nowpay'] for n,dat in G.nodes_iter(data=True) if dat['type'] == 'greedy']
    data["Average human"] = sum(hpays)/max(len(hpays), 1)
    data["Average dumb"] = sum(dpays)/max(len(dpays), 1)
    data["Average greedy"] = sum(gpays)/max(len(gpays), 1)
    data["Proportion dumb"] = len(dpays)/float(len(apays))
    
    self.data = data
  
  def summary(self):
    for var, val in sorted(self.data.items()):
      print str(var)+":", val
  
  def groupsummary(self):
    for g, skills in self.groupdat['skills'].iteritems():
      print "Group", g
      print "  Agents:", self.groupdat['agents'][g]
      print "  Skills:", skills
      print "  Earns: ", self.groupdat['nowpay'][g]

  def dumpsummarydb(self, dblog):
    data = self.data
    
    dbdata = [self.cfg.simnumber, data['Start time'], data['End time'], data['Elapsed time'], data['Iterations'], data['Num groups'], data['Singletons'], data['Switches'], data['Average earnings'], data['Average human'], data['Average dumb'], data['Average greedy']]
    
    dblog.log_summary(dbdata)
    
      
    # Generate general data here
    configd = self.cfg.outputcfg()
    outdata = {'timestamp': str(datetime.datetime.now())}
    outdata.update(self.data)
    outdata.update(configd)
    outdata.pop('tasks', None)
    dblog.log_summary_gen(self.cfg.simnumber, outdata)
    

  def dumpsummary(self, filename):
    cfg = self.cfg
    
    with open(filename, 'a') as f:
      #fcntl.flock(f, fcntl.LOCK_EX) ## Does not work over NFS
      fcntl.lockf(f.fileno(), fcntl.LOCK_EX)
      
      configd = cfg.outputcfg()
      
      # Generate line of csv data
      outline = {'timestamp': str(datetime.datetime.now())}
      #outline =  join res and configd and date
      outline.update(self.data)
      outline.update(configd)
      outline.pop('tasks', None)
      
      sortheader = sorted(outline.keys())
      
      if cfg.simnumber == 1:
          Configuration._header = sortheader
      elif Configuration._header != sortheader:
          print "Header mismatch!"
          print "cfg: ", Configuration._header
          print "now: ", sortheader
          sys.exit(1)
      
      # add header if empty; otherwise, append
      if f.tell() == 0:
        print "Writing header"
        header = [k for k in sortheader]
        header = "\t".join(header)+"\n"
        f.write(header)
        # date, config, results
      
      # Then, output the line of csv data
      f.write("\t".join(str(outline[k]) for k in sortheader)+"\n")
      
      #fcntl.flock(f, fcntl.LOCK_UN)  ## Does not work over NFS
      fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
