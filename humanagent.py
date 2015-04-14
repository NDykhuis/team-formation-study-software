#
# humanagent.py - provides server-side backend for interaction with
#                 human players in team formation
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
"""Agent class to allow humans on client computers to play team formation.

The HumanAgent class is the server-side backend of the human interaction
system. It performs all calculation of payoffs, etc, and forwards the info
to the Frontend client over TCP. The Frontend client is a fairly-thin wrapper
which simply takes messages describing what screen to display, with what info,
and receives input from the user.

Numerous functions use send_and_receive to ask for user input, and ensure that
the program (or thread) blocks until it has been received.
"""

import json
import numpy as np

from configuration import Configuration
from agentgroup import Agent
from utils import send_message, receive_message, send_and_receive

CURR = u'\xA7'


class HumanAgent(Agent):
  """HumanAgent class implements all functions necessary for team formation
  
  Each function gathers the relevant information, then ships it off to a
  Frontend instance over TCP for evaluation and decision by a human player.
  
  Attributes:
    slow: always True, since humans take time to decide
    type: 'human'
    client: the sockets connection to the Frontend
    finalpay: total pay, only set after the exit survey is submitted
    messages: list accumulator of message strings that are sent to the user as
              a summary of the turn during the postprocess stage.
  """
  
  def __init__(self, cfg, connection, adat=None, skills=None, aid=None):
    super(HumanAgent, self).__init__(cfg, adat, skills, aid)
    
    self.client = connection
    self.messages = []
    self.slow = True
    self.type = 'human'
    
    # THIS IS DUPLICATED FROM FRONTEND.PY - should move to configuration?
    self.gletters = [chr(ord('A')+i) for i in range(Configuration.n)]
    if Configuration.hide_publicgoods:
      self.anames = ['Agent '+str(i) for i in range(Configuration.n)]
    else:
      # Icky hardcoding
      self.anames = ['Cat', 'Dog', 'Bear', 'Monkey', 'Cow', 'Elephant', 
                     'Gorilla', 'Fish', 'Sheep', 'Frog', 'Bird', 'Lion', 
                     'Owl', 'Panda', 'Penguin', 'Pig', 'Rabbit', 'Rooster', 
                     'Bee', 'Donkey']
    
    self.current_ratings = {}
    self.finalpay = -1
    
    send_message(self.client, ('setmyid', self.id))
    self.sendcfg()

  def sendcfg(self):
    """Send the current configuration to the client as a dictionary.
    
    Sends only the variables which can be packed with JSON.
    Blocks until client confirms that it has received the message
    """
    cfgdict = self.cfg.outputcfg(showhidden=True)
    # remove all things that are not jsonnable
    jsoncfg = {}
    for k,v in cfgdict.iteritems():
      try:    # This is hacky...
        json.dumps(v)
        jsoncfg[k] = v
      except TypeError:
        pass
    send_and_receive(self.client, ('setconfig', jsoncfg))
    # Make sure the config gets set before moving on

  def gname(self, gid):
    """Get the name (letter) of a group from an integer group ID"""
    return self.gletters[gid]
  
  def aname(self, aid):
    """Get the name of an agent from an integer agent ID"""
    if aid == self.id:
      return "You"
    return self.anames[aid]
  
  def initvideo(self):
    """Tell client to start video capture and open a preview window"""
    cfg = self.cfg
    # send additional video info here
    vdata = (cfg._do_video, cfg._dblog.sessionid, self.id)
    send_message(self.client, ('initvideo', vdata))
    send_message(self.client, ('startpreview', 0))
    
  def instructions(self):
    """Tell client to show instructions screen and close preview window"""
    if self.cfg.do_ratings: self.hideratings()
    
    send_message(self.client, ('endpreview', 0))
    
    self.sendcfg()
    
    send_and_receive(self.client, ('instructions', 0))
    #if self.cfg.do_ratings: self.showratings()
    self.logp(("Instructions done for", self.id))

  def initratings(self, neighbors):
    """Tell client to create the ratings sidebar"""
    send_message(self.client, ('initratings', neighbors))

  def showratings(self):
    """Tell client to show the ratings sidebar"""
    send_message(self.client, ('showratings', 0))

  def hideratings(self):
    """Tell client to hide the ratings sidebar"""
    send_message(self.client, ('hideratings', 0))

  def disableratings(self):
    """Tell client to make ratings sidebar un-clickable"""
    send_message(self.client, ('disableratings', 0))

  def introsurvey(self):
    """Tell client to present intro survey screen, and record response"""
    gender, college, status = send_and_receive(self.client, ('introsurvey', 0))
    self.cfg._dblog.log_introsurvey(self.id, (gender, college, status))
  
  def exitsurvey(self):
    """Tell client to present exit survey, and after submit, get final pay"""
    self.logratings()
    send_message(self.client, ('exitsurvey', 0))
    
    # Receive num of questions, and then each question and response
    n_qs = receive_message(self.client)
    responses = []
    for i in range(n_qs):
      (qtext, qresponse) = receive_message(self.client)
      responses.append( (qtext, qresponse) )
      
    self.finalpay = receive_message(self.client)
      
    self.hideratings()
      
    self.cfg._dblog.log_exitsurvey(self.id, responses)
    self.logratings(step='exitsurvey')
    self.logratingstatus('final', range(self.cfg.n)) # Log ratings of everyone
    
    self.logp(("Agent", self.id, "exit survey submitted"), 0)

  def startcapture(self):
    """Client: start video capture"""
    send_message(self.client, ('startcapture', 0))
    
  def stopcapture(self):
    """Client: pause video capture"""
    send_message(self.client, ('stopcapture', 0))

  def endcapture(self):
    """Client: terminate video capture"""
    send_message(self.client, ('endcapture', 0))

  def update(self):
    """Update current pay and neighbors here and in the GUI"""
    if self.cfg.bias:
      self.nowpay = self.nowpaycalc(self.cfg.task(self.group.skills))
    else:
      self.nowpay = self.cfg.task(self.group.skills)/self.group.gsize
    send_message(self.client, ('updatepay', self.nowpay) )
    
    if self.cfg.show_skills:
      send_message(self.client, ('updatemyteam', (self.group.id, int(np.where(self.skills)[0][0])) ))
    else:
      send_message(self.client, ('updatemyteam', (self.group.id, -1)) )
    
    send_message(self.client, ('updateteam', sorted([a.id for a in self.group.agents])))
    self.updatenbrs()

  def updatenbrs(self):
    """Update graphical view of neighbors in the GUI"""
    #nbrdata = [(n.id, n.group.id) for n in self.nbrs]  # old nbrdata
    if self.cfg.show_skills:
      nbrdata = [(n.id, n.group.id, int(np.where(n.skills)[0][0])) for n in self.nbrs]
    else:
      nbrdata = [(n.id, n.group.id, -1) for n in self.nbrs]
    send_message(self.client, ('updatenbrs', nbrdata) )

  def getframetimes(self):
    """Get the start and end frame numbers and timestamps from the last event.
    
    Returns:
      tuple of (start frame, end frame, start time, end time)
      frame numbers are ints, times are Unix timestamps
    """
    return send_and_receive(self.client, ('getframetimes', 0))

  def logratings(self, simnum = None, iternum = None, step = 'NA'):
    """Get all accumulated ratings from the client and log to database.
    
    Also update self.current_ratings with the most recent rating assigned.
    
    Arguments:
      simnum: the current round number
      iternum: the current iteration number
      step: the current step (apply, acceptvote, join, expel, pubgood, etc.)
    
    All ratings fetched will be marked with these values, so to ensure that
    ratings are assigned to the correct step, collect ratings once before the
    step starts, and again after the step ends, marking with the step name on
    the second call. (see usage in code)
    """
    if not self.cfg.do_ratings: return
    ratings = send_and_receive(self.client, ('getratinglog', 0))
    if not len(ratings):
      return
    if not simnum:
      try:
        simnum, iternum = self.cfg.simnumber, self.cfg.iternum
      except AttributeError:
        simnum, iternum = -1, -1
    try:
      for r in ratings:
        r.extend( [simnum, iternum, step] )
        self.current_ratings[r[1]] = r[2]
      self.cfg._dblog.log_ratings(ratings)
    except AttributeError:
      print "PROBLEM!"
      print "ratings data is:", ratings
    self.logp(("Agent", self.id, "ratings:", ratings))

  def logratingstatus(self, eventtype, otherids, gmembers=None):
    """Log the current ratings that a user is seeing when making a decision.
    
    If gmembers is None, then otherids is a list of agent IDs, as during the
    acceptvote or pubgood steps.
    
    If gmembers is not None, then otherids is a list of group IDs, and gmembers
    is a list of lists of the agent IDs of the members of each group, used
    during the apply or join steps.
    """
    if gmembers is not None:
      rtgs = [[self.current_ratings.get(aid) for aid in g if aid in self.current_ratings] 
              for g in gmembers if len(g)]
      grtgs = [[self.global_ratings.get(aid) for aid in g if aid in self.global_ratings] 
               for g in gmembers if len(g)]
      myrtgs = [-1 if not len(rats) else float(sum(rats))/len(rats) for rats in rtgs]
      if self.cfg.show_global_ratings:
        globalrtgs = [-1 if not len(grats) else float(sum(grats))/len(grats) 
                      for grats in grtgs]
      else:
        globalrtgs = [-1 for rats in rtgs]
      minrtgs = [-1 if not len(rats) else min(rats) for rats in rtgs]
      maxrtgs = [-1 if not len(rats) else max(rats) for rats in rtgs]
    else:
      myrtgs = [self.current_ratings.get(aid, -1) for aid in otherids]
      globalrtgs = [-1 if not self.cfg.show_global_ratings 
                    else self.global_ratings.get(aid, -1) 
                    for aid in otherids]
      minrtgs = maxrtgs = [-1 for aid in otherids]
    try:
      self.cfg._dblog.log_ratingstatus(
        self.cfg.simnumber, self.cfg.iternum, eventtype, self.id, otherids, 
        myrtgs, globalrtgs, minrtgs, maxrtgs
      )
    except AttributeError:
      self.cfg._dblog.log_ratingstatus(
        self.cfg.simnumber, -1, eventtype, self.id, otherids, 
        myrtgs, globalrtgs, minrtgs, maxrtgs
      )

  def getratings(self):
    """Get current ratings from the client, and return them.
    
    Returns:
      dictionary mapping agent ID (int) to rating (int)
    """
    ratings = send_and_receive(self.client, ('getratings', 0))
    self.current_ratings.update(ratings)
    return self.current_ratings
  
  def updateratings(self, ratings):
    """Send the current global ratings to the client to update UI.
    
    Arguments:
      ratings: dictionary mapping agent ID (int) to rating (int, 1-5)
    """
    self.global_ratings = ratings
    if self.cfg.show_global_ratings:
      send_message(self.client, ('updateglobalratings', ratings))

  def updatehistory(self, pghistory):
    """Send public contribution history information to the client to update UI.
    
    Arguments:
      pghistory: dictionary mapping agent ID to list of previous contributions
    """
    send_message(self.client, ('updatehistory', pghistory))

  def propose(self):
    task = self.cfg.task
    self.update()   ## Maybe needs to come after the propose message!
    
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    if not len(nbrgroups):
      return
    
    idgroups = {g.id:g for g in nbrgroups}

    gdata = sorted([ (g.id, g.gsize, task(g.withskills(self))/(g.gsize+1), 
                      [a.id for a in g.agents]) for g in nbrgroups])
    gids, gsizes, newpays, gmembers = zip(*gdata)

    self.logratings()
    self.logratingstatus('apply', gids+(-1, ), gmembers+([a.id for a in self.group.agents],))

    # Send all data to GUI and blocking receive
    # Wait for user to reply with list of applications
    applications = send_and_receive(self.client, ('propose', gdata) )
    
    self.logratings(step='apply')
    
    if len(applications):
      gnames = [self.gname(gid) for gid in applications]
      self.messages.append('You applied to group'+('s ' if len(gnames) > 1 else ' ')+', '.join(gnames))
    else:
      self.messages.append('You did not apply to any groups')

    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_apply(
      self.cfg.simnumber, self.cfg.iternum, self.id, gids, self.nowpay, 
      newpays, applications, sframe, eframe, stime, etime
    )
    
    self.logp(("Agent", self.id, "proposes", applications))
  
    for gid in applications:
      g = idgroups[gid]
      g.takeapplication(self)
  
  def acceptvote(self, applicants):
    if not len(applicants):
      # If no applicants, shouldn't be calling this function, but in any case, 
      # return None
      return None
    
    task = self.cfg.task
    self.update()
    myg = self.group

    ## TODO: create a case for group merging
    # acceptvote_groupmerge
    
    idagents = {a.id:a for a in applicants}
    gdata = sorted([(a.id, task(myg.withskills(a))/(myg.gsize+a.gsize)) 
                    for a in applicants])
    naids, newpays = zip(*gdata)
    
    self.logratings()
    self.logratingstatus('acceptvote', naids)
    
    # Send all data to GUI and blocking receive
    # Wait for user to reply with list of applications
    accept_id = send_and_receive(self.client, ('acceptvote', gdata) )
    
    self.logratings(step='acceptvote')

    naids = list(naids)
    newpays = list(newpays)
    # Add the "accept no one" option
    naids.append(-1)
    newpays.append(self.nowpay)
    
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_accept(
      self.cfg.simnumber, self.cfg.iternum, self.id, naids, self.nowpay,
      newpays, accept_id, sframe, eframe, stime, etime
    )


    if accept_id != -1:
      self.logp(("Agent", self.id, "votes to accept", accept_id))

    if accept_id != -1:
      #self.messages.append('You voted to accept agent '+str(accept_id)+
      #                     ' into the group')
      return idagents[accept_id]
    else:
      # No applicant should join the team
      return None

  def expelvote(self):
    task = self.cfg.task
    self.update()
    nowpay = self.nowpay
    myg = self.group
  
    idagents = {a.id:a for a in myg.agents}
    #del idagents[self.id]
    gdata = sorted([(a.id, task(myg.withoutskills(a))/(myg.gsize-1)) 
                    for aid, a in sorted(idagents.items()) if aid != self.id])
    naids, newpays = zip(*gdata)
    
    self.logratings()
    self.logratingstatus('expelvote', naids)
    
    # Send all data to GUI and blocking receive
    # Wait for user to reply with list of applications
    expel_id = send_and_receive(self.client, ('expelvote', gdata) )
    
    self.logratings(step='expelvote')

    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_expel(
      self.cfg.simnumber, self.cfg.iternum, self.id, naids, self.nowpay, 
      newpays, expel_id, sframe, eframe, stime, etime
    )

    self.logp(("Agent", self.id, "votes to expel", expel_id))

    if expel_id == -1:
      # No member should leave the team
      return None
    else:
      #self.messages.append('You voted to expel agent '+str(accept_id)+
      #                     ' from the group')
      return idagents[expel_id]


  def consider(self):
    if not len(self.acceptances) or \
       not len([g.gsize for g in self.acceptances if g.gsize > 0]):
      self.messages.append('You received no acceptances')
      return
    
    task = self.cfg.task
    self.update()
    
    idgroups = {g.id:g for g in self.acceptances}

    gdata = sorted([ (g.id, g.gsize, task(g.withskills(self))/(g.gsize+1), 
                      [a.id for a in g.agents]) for g in self.acceptances])
    gids, gsizes, gpays, gmembers = zip(*gdata)
    
    self.logratings()
    self.logratingstatus('join', gids+(-1, ), 
                         gmembers+([a.id for a in self.group.agents], ))
    
    # Send all data to GUI and blocking receive
    # Wait for user to reply with list of applications
    choice_id = send_and_receive(self.client, ('consider', gdata) )
    
    self.logratings(step='join')
    
    if choice_id == -1:
      # Player does not want to switch groups.
      pass 
    else:
      self.messages.append('You switched to group '+self.gname(choice_id))
      self.switchgroup(idgroups[choice_id])
    
    gids = list(gids)
    gsizes = list(gsizes)
    gpays = list(gpays)
    # Add your current group (no change)
    gids.append(-1)
    gsizes.append(self.group.gsize)
    gpays.append(self.nowpay)
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_join(
      self.cfg.simnumber, self.cfg.iternum, self.id, gids, self.nowpay, gpays, 
      choice_id, sframe, eframe, stime, etime
    )
    
    if choice_id != -1:
      self.logp(("Agent", self.id, "joins", choice_id))
    
    self.acceptances = []
    
  def notifygaccept(self, aid):
    actor = 'Your group' if self.group.gsize > 1 else 'You'
    if aid != -1:
      self.messages.append(actor+' voted to accept '+self.aname(aid)+
                           ' to join your team')
    else:
      self.messages.append(actor+' voted to allow no one to join your team')
    
  def notifyjoin(self, aid, add=True, expel=False):
    changewords = ['left', 'joined']
    if aid != -1:
      if not expel:
        self.messages.append(self.aname(aid)+' '+changewords[add]+' your team')
      else:
        if aid == self.id:
          self.messages.append('You were expelled from your team')
        else:
          self.messages.append('Your team expelled '+self.aname(aid))
    else:
      if expel:
        self.messages.append('No agents were expelled from your team')
      else:
        self.messages.append('No agents '+changewords[add]+' your team')
  
  def postprocess_iter(self):
    # Send all data to GUI and blocking receive
    self.update()
    if len(self.messages):
      send_and_receive(self.client, ('turndone', '\n'.join(self.messages)) )
    else:
      self.log("No new messages for human player", 6)
    
    #if self.cfg.do_ratings:
    #  self.logratings(step='postprocess_iter')
    self.logratings()
    
    ###TODO: Maybe wait to ensure user is done???
    
    self.messages = []
  
  def postprocess(self, globalpay=None):
    self.update()
    self.messages.append('You earned '+CURR+str(round(self.nowpay, 2)))
        
    self.logratings()
    send_message(self.client, ('addpay', round(self.nowpay, 2)) )
    send_and_receive(self.client, ('postprocess', '\n'.join(self.messages)) )
    self.logratings(step='postprocess')
    
    
    self.messages = []
    
  def postprocess_pg(self, globalpay=None):
    self.update()
    self.messages.append('You can earn '+CURR+str(round(self.nowpay, 2))+
                         ' on this team.')
    
    self.logratings()
    send_and_receive(self.client, ('postprocess', '\n'.join(self.messages)) )
    #send_message(self.client, ('addpay', round(self.nowpay, 2)) )
    self.logratings(step='postprocess')
    
    self.logratings()
    
    self.messages = []
  
  ## PUBLIC GOODS FUNCTIONS:
  def publicgoods(self, pgdict, potmult):
    self.update()
    
    if self.cfg.do_ratings: self.hideratings()
    send_and_receive(self.client, ('publicgoods_instructions', potmult))
    if self.cfg.do_ratings: self.showratings()
    
    ## Send team as neighbors
    if self.cfg.show_skills:
      teamdata = [(n.id, n.group.id, int(np.where(n.skills)[0][0])) 
                  for n in self.group.agents if n != self]
    else:
      teamdata = [(n.id, n.group.id, -1) for n in self.group.agents if n != self]
    send_message(self.client, ('updatenbrs', teamdata) )    
    
    self.logratings()
    self.logratingstatus('pubgood', [n.id for n in self.group.agents if n != self])
    
    # Send current pay with the publicgoods message
    contrib = send_and_receive(self.client, ('publicgoods', (int(self.nowpay), potmult)))
    self.logratings(step='publicgoods')
    
    self.logp(("Agent", self.id, "contribs", contrib, "/", int(self.nowpay)))
    
    #return contrib
    pgdict[self] = (contrib, int(self.nowpay)-contrib)
  
    
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, potpay, teampays):
    maxcontrib = startpay
    newpay = privatepay + potpay
    
    # Send summary info to the GUI
    self.messages.append('You made '+CURR+str(round(startpay, 2))+
                         ' this round by working with this team.')
    cdesc = 'the shared pot' if not self.cfg.hide_publicgoods else 'the lottery'
    self.messages.append('Of that, you contributed '+CURR+str(contrib)+' to '+
                         cdesc+' and kept '+CURR+str(round(keep, 2)))
    if self.cfg.alt_pubgoods and not self.cfg.hide_publicgoods:
      ratings = [self.global_ratings[n.id] for n in self.group.agents 
                 if n.id in self.global_ratings]
      contribs = [teampays[n.id][0]/float(startpay) for n in self.group.agents]
      potmult = self.cfg.pubgoods_calc(contribs, ratings)
      potmult = int((potmult-1)*100)
      self.messages.append('The pot was increased by {0}%'.format(potmult))
    self.messages.append('You received '+CURR+str(round(potpay, 2))+
                         ' from '+cdesc)
    self.messages.append('You earned a total of '+CURR+str(round(newpay, 2))+
                         ' this round.')
    
    ### UPDATE UI WITH DATA ABOUT TEAM CONTRIBS
    teammateids = [n.id for n in self.group.agents]
    contribs = [teampays[n][0] for n in teammateids]
    
    send_message(self.client, ('updatemyteam', (self.group.id, str(contrib)) )) 
    teammates = list(self.group.agents)
    teammates.remove(self)
    teamids = [n.id for n in teammates]
    teamdata = [(n.id, n.group.id, teampays[n.id][0]) for n in teammates]
    send_message(self.client, ('updatenbrs', teamdata) )
    
    send_message(self.client, ('publicgoods_conclusion', (newpay, (teammateids, contribs))))
    send_message(self.client, ('addpay', round(newpay, 2)) )
    
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_pubgoods(self.cfg.simnumber, 
        self.id, self.group.id, 
        teamids, contrib, 
        [teampays[n.id][0] for n in teammates], 
        keep, newpay,
        sframe, eframe, stime, etime)
    
    self.logratings()
    
    send_and_receive(self.client, ('postprocess', '\n'.join(self.messages)) )
    self.logratings(step='pg_postprocess')
    
    self.logratingstatus('simend', teamids)
    
    self.messages = []
    
    
    
  ## ULTIMATUM FUNCTIONS:
  def ultimatum_init(self):
    send_message(self.client, ('ultimatum', None))
    send_message(self.client, ('u_instructions', None))
    
  def ultimatum(self, other_player):
    pass
  
  def dictator(self, other_player):
    send_message(self.client, ('dictator', None))
    send_message(self.client, ('d_instructions', None))
  
  def ask_for_offer(self, other_player):
    amount = send_and_receive(self.client, ('u_makeoffer', other_player))
    
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.ultevent_insert(
      self.id, other_player, 'make_offer', amount, sframe, eframe, stime, etime
    )
    
    return amount

  def wait_offer(self, other_player):
    send_message(self.client, ('u_waitoffer', other_player))
  
  def decide_offer(self, other_player, amount):
    result = send_and_receive(self.client, 
                              ('u_decideoffer', (other_player, amount)))
    
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.ultevent_insert(
      self.id, other_player, 'decide_offer', result, sframe, eframe, stime, etime
    )
    
    return result
  
  def wait_decide(self, other_player):
    send_message(self.client, ('u_waitdecide', other_player))
  
  def show_conclusion_u(self, other_player, amount, result, role):
    send_and_receive(self.client, 
                     ('u_conclusion', (other_player, amount, result, role)))
    
    if result:
      if role == 0:
        my_amount = 10-amount
      else:
        my_amount = amount
    else:
      my_amount = 0
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.ultevent_insert(
      self.id, other_player, 'conclusion', my_amount, 
      sframe, eframe, stime, etime)
    
    if self.cfg.do_ratings:
      self.logratings(step='ultimatum', simnum=-1, iternum=-1)
    
  def show_conclusion_d(self, other_player, amount, role):
    send_message(self.client, ('d_conclusion', (other_player, amount, role)))
    
  def u_review(self):
    send_message(self.client, ('u_review', None))
