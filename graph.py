#
# graph.py - creates and initializes NetworkX social network graph
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
"""Creates and manages social network graphs with NetworkX.

Can initialize social network graphs from various NetworkX graph generators.
Also assigns agent skills and other data to the nodes and edges
"""

import random
import networkx as nx
import math
import colorsys
import numpy as np
 
class graphmanager:
  """NetworkX social network graph manager.
  
  Creates a graph based on a configuration object, and initializes
  with all necessary data about agent skills, edge weights, etc.
  
  After construction the object, call setup() to create the graph.
  
  Attributes:
    G: the NetworkX graph object
  """
  def __init__(self, cfg):
    self.cfg = cfg
    self.G = None

  def setup(self):
    """Creates the NetworkX graph and initializes agent data."""
    self.initgraph()
    self.initagents()

  def reset(self):
    """Reset agent data from a previous run."""
    for n, dat in self.G.nodes_iter(data=True):
      dat['group'] = n
      dat['switches'] = 0
      dat['nowpay'] = 0
      dat['acceptances'] = []
  
  def initgraph(self):
    """Create a NetworkX graph, based on a configuration object."""
    cfg = self.cfg
    if cfg.graphseed is not None:
      currstate = random.getstate()
      random.seed(cfg.graphseed)
      
    # Generate graph
    G = nx.Graph()
    graph_ok = False
    ntries = 0
    
    while not graph_ok:
      if cfg.graph_type in ['complete_graph', 'wheel_graph', 
                            'cycle_graph', 'path_graph']:
        try:
          func = eval("nx."+cfg.graph_type)
          G = func(cfg.n)
        except nx.exception.NetworkXError as e: 
          print e
          raise
      elif cfg.graph_type == 'random_cycle':
        nodes = range(cfg.n)
        G = nx.Graph()
        hnodes = nodes[:cfg.nhumans]
        snodes = nodes[cfg.nhumans:]
        random.shuffle(hnodes)          # Keep human nodes together
        random.shuffle(snodes)
        nodes = hnodes + snodes
        for i in range(len(nodes)-1):
          G.add_edge(nodes[i], nodes[i+1])
        G.add_edge(nodes[-1], nodes[0])
      elif cfg.graph_type == 'random_cycle4':
        nodes = range(cfg.n)
        G = nx.Graph()
        hnodes = nodes[:cfg.nhumans]
        snodes = nodes[cfg.nhumans:]
        random.shuffle(hnodes)          # Keep human nodes together
        random.shuffle(snodes)
        nodes = hnodes + snodes
        for i in range(len(nodes)-2):   # Add connections between nodes
          G.add_edge(nodes[i], nodes[i+1])
          G.add_edge(nodes[i], nodes[i+2])
        G.add_edge(nodes[-1], nodes[0])
        G.add_edge(nodes[-2], nodes[0])
        G.add_edge(nodes[-1], nodes[1])
      elif cfg.graph_type == 'random_cycle4_zip':
        nodes = range(cfg.n)
        G = nx.Graph()
        hnodes = nodes[:cfg.nhumans]
        snodes = nodes[cfg.nhumans:]
        random.shuffle(hnodes)
        random.shuffle(snodes)
        nodes = []
        # "Zip" the human and sim nodes together (not efficient)
        for h, s in zip(hnodes, snodes): 
          nodes.append(h)
          nodes.append(s)
        nodes += hnodes[(cfg.n-cfg.nhumans):]   # Add the dangling parts
        nodes += snodes[cfg.nhumans:]
        for i in range(len(nodes)-2):   # Add connections between nodes
          G.add_edge(nodes[i], nodes[i+1])
          G.add_edge(nodes[i], nodes[i+2])
        G.add_edge(nodes[-1], nodes[0])
        G.add_edge(nodes[-2], nodes[0])
        G.add_edge(nodes[-1], nodes[1])
      elif cfg.graph_type == 'small world':
        try:
          G = nx.generators.random_graphs.watts_strogatz_graph(
            cfg.n,cfg.connections,cfg.prob_rewire)
        except nx.exception.NetworkXError as e: 
          print e
          raise
      elif cfg.graph_type == 'star_graph':
        G = nx.star_graph(cfg.n-1)
      elif cfg.graph_type == "grid_graph":
        dim = int(math.ceil(math.sqrt(cfg.n)))
        G = nx.grid_graph(dim=[dim, dim])
        G = nx.relabel.convert_node_labels_to_integers(
          G,first_label=0, ordering="sorted")
        G.remove_nodes_from(range(cfg.n, dim*dim))
        
        # Danger - this can lead to disconnected graphs! (with low prob)
        if cfg.rewire_grid_graph:
          # Code from networkx watts_strogatz_graph generator
          nodes = list(range(cfg.n))
          orig_edges = G.edges()[:]
          for e in orig_edges:
            if random.random() < cfg.prob_rewire:
              node = random.choice( (0, 1) )
              other_node = 1-node
              u, v = e[node], e[other_node]
              w = random.choice(nodes)
              # Enforce no self-loops or multiple edges
              while w == u or G.has_edge(u, w): 
                w = random.choice(nodes)
              G.remove_edge(u, v)  
              G.add_edge(u, w)
      elif cfg.graph_type in ["watts_strogatz_graph", 
                              "newman_watts_strogatz_graph", 
                              "connected_watts_strogatz_graph"]:
        try:
          func = eval("nx."+cfg.graph_type)
          G = func(cfg.n, cfg.connections, cfg.prob_rewire)
        except nx.exception.NetworkXError as e: 
          print e
          raise
      elif cfg.graph_type in ["erdos_renyi_graph", "binomial_graph", 
                              "gnp_random_graph", "fast_gnp_random_graph"]:
        try:
          func = eval("nx."+cfg.graph_type)
          
          target_edge_count = cfg.connections/2 * cfg.n
          complete_edge_count = cfg.n*(cfg.n-1)/2
          prob_edge = float(target_edge_count) / complete_edge_count
          
          G = nx.gnm_random_graph(cfg.n, target_edge_count)

        except nx.exception.NetworkXError as e: 
          print e
          raise
      elif cfg.graph_type in ["gnm_random_graph", "dense_gnm_random_graph"]:
        try:
          func = eval("nx."+cfg.graph_type)
          G = func(cfg.n, cfg.num_edges)
        except nx.exception.NetworkXError as e: 
          print e
          raise
      elif cfg.graph_type == "barabasi_albert_graph":
        try:
          func = eval("nx."+cfg.graph_type)
          
          # Calibrate number of edges to match the watts-strogatz 
          # as closely as possible
          num_edges = target_edge_count = cfg.connections/2 * cfg.n
          conns = 0.5*(cfg.n-math.sqrt(cfg.n**2-4*num_edges))
          conns = int(round(conns, 0))
          
          G = func(cfg.n, conns)
        except nx.exception.NetworkXError as e: 
          print e
          raise
      elif cfg.graph_type == "powerlaw_cluster_graph":
        try:
          func = eval("nx."+cfg.graph_type)
          G = func(cfg.n, cfg.connections, cfg.prob_rewire)
        except nx.exception.NetworkXError as e: 
          print e
          raise
      
      # Check if graph is ok
      graph_ok = True
      
      # Ensure that each human has at least one human neighbor
      nhumans = cfg.nhumans
      if nhumans > 1:
        hids = range(nhumans)
        for i in range(nhumans):
          nbrs = G[i].keys()
          human_nbrs = [n for n in nbrs if n in hids]
          if not len(human_nbrs):
            others = [n for n in hids if n != i]
            G.remove_edge(i, random.choice(nbrs))
            G.add_edge(i, random.choice(others))


      # Ensure graph is connected
      graph_ok = graph_ok and nx.is_connected(G)
      
      # Ensure that humans (or everyone) have reasonable number of edges
      if not cfg.graph_type == 'complete_graph':
        degrees = [d for d in G.degree().values() if d > cfg.max_connections]
        if len(degrees):
          print "Too many edges:", degrees
        graph_ok = graph_ok and not len(degrees)
      
      ntries += 1
      if ntries > 200:
        err = "Could not create valid graph; maximum number of tries exceeded"
        raise nx.NetworkXError(err)

    if cfg.graphseed is not None:
      random.setstate(currstate)

    ### DIGRAPH
    #G = nx.DiGraph(G)
    if cfg.graph_class == 'digraph':
      G = nx.DiGraph(G)
    #G = cfg._graph_constructor(G)

    if cfg._draw_graph or cfg.dynamic_graph:
      if cfg.springseed is not None:
        currstate = np.random.get_state()
        np.random.seed(cfg.springseed)
        
      if cfg.graph_type in ['wheel_graph', 'star_graph', 'cycle_graph', 
                            'path_graph', 'complete_graph']:
        Glayout = nx.circular_layout(G)
      else:
        Glayout = nx.spring_layout(G, weight=None)
        
      if cfg.springseed is not None:
        np.random.set_state(currstate)
      
      HSV_tuples = [(x*1.0/cfg.n, 1, 0.6) for x in range(cfg.n)]
      teamcolors = [colorsys.hsv_to_rgb(*t) for t in HSV_tuples]
      random.shuffle(teamcolors)
      
      G.graph['layout'] = Glayout
      G.graph['teamcolors'] = teamcolors

    #print G.nodes()
    cfg._Gptr = G
    
    self.G = G
    
  def initagents(self):
    """Initialize agents and edges with skills and attributes."""
    cfg = self.cfg
    n = cfg.n
    G = self.G
    
    if cfg.skillseed is not None:
      currstate = random.getstate()
      random.seed(cfg.skillseed)
    
    for n, dat in G.nodes_iter(data=True):
      # Set attributes of the agent
      dat['id'] = n
      dat['group'] = n      # Agent is its own group
      dat['switches'] = 0
      dat['nowpay'] = 0
    
      # Set skills
      lev = random.randint(1, min(cfg.nskills, cfg.maxskills))
      skills = [1]*lev + [0]*(cfg.nskills-lev)
      random.shuffle(skills)
      dat['skills'] = skills
    
      dat['acceptances'] = []
      
    # Set weight on edges and bias
    for _, _, edat in G.edges(data=True):
      #edat['weight'] = 0.0
      #edat['weight'] = random.triangular(-4.0, 4.0, 0.0)
      #edat['weight'] = random.random()
      edat['weight'] = 1.0
      
      edat['bias'] = random.triangular(-2.0, 2.0, 0.0)
      
      ## NOTE THAT THIS WILL ONLY WORK WITH MUTUAL BIAS
      #self.bias[n] = np.random.normal()    # does not use the same random seed
      #edat['bias'] = random.triangular(1.0, cfg.biasrange, 1)**random.choice((-1.0, 1.0))   # multiplier for utility of working with someone
    
    if cfg.skillseed is not None:
      random.setstate(currstate)
    
    skills = [0]*cfg.nskills
    for n, dat in G.nodes_iter(data=True):
      askill = dat['skills']
      for i in range(len(skills)):
        skills[i] += askill[i]
    print "Total skills:", skills
      
    for n, dat in G.nodes_iter(data=True):
      # Calculate agent value based on the default task structure
      dat['worth'] = sum( [(i+1)*10*dat['skills'][i] for i in range(cfg.nskills)] )
    
    
    
  