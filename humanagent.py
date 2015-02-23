from configuration import *
from agentgroup import *
from utils import *
import datetime
import operator
import json

CURR = u'\xA7'


class humanagent(agent):
  def __init__(self, cfg, connection, adat=None, skills=None, aid=None):
    super(humanagent, self).__init__(cfg, adat, skills, aid)
    
    ## This part might have to be more global...
    #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #self.socket = s
    #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #s.bind((ADDRESS, SERVER_PORT))
    #s.listen(1)
    #connection, client_address = s.accept()
    
    self.client = connection
    self.messages = []
    self.slow = True
    self.type = 'human'
    
    # this all needs to go in the frontend
    #if cfg._do_video:
    #  today = datetime.date.today()
    #  self.vidfile = 'ses_{sessionid:02d}_user_{userid:02d}_{date}'.format(
    #      sessionid=cfg._dblog.sessionid, userid=self.id, date=today.strftime('%Y/%m/%d'))
    #  self.vidrec = vidcapture(self.vidfile)
    
    # THIS IS DUPLICATED FROM FRONTEND.PY - should move to configuration?
    self.gletters = [chr(ord('A')+i) for i in range(configuration.n)]
    if configuration.hide_publicgoods:
      self.anames = ['Agent '+str(i) for i in range(configuration.n)]
    else:
      # Icky hardcoding
      self.anames = ['Cat', 'Dog', 'Bear', 'Monkey', 'Cow', 'Elephant', 'Gorilla', 'Fish', 'Sheep', 'Frog', 'Bird', 'Lion', 'Owl', 'Panda', 'Penguin', 'Pig', 'Rabbit', 'Rooster', 'Bee', 'Donkey']
    
    self.current_ratings = {}
    self.global_ratings = {}
    
    send_message(self.client, ('setmyid', self.id))
    self.sendcfg()
    

  def sendcfg(self):
    cfgdict = self.cfg.outputcfg(showhidden=True)
    # remove all things that are not jsonnable
    jsoncfg = {}
    for k,v in cfgdict.iteritems():
      try:    # This is hacky...
        json.dumps(v)
        jsoncfg[k] = v
      except TypeError:
        pass
    send_message(self.client, ('setconfig', jsoncfg))
    receive_message(self.client)    # Make sure the config gets set before moving on

  def gname(self, gid):
    return self.gletters[gid]
  
  def aname(self, aid):
    if aid == self.id:
      return "You"
    return self.anames[aid]
  
  def initvideo(self):
    cfg = self.cfg
    # send additional video info here
    vdata = (cfg._do_video, cfg._dblog.sessionid, self.id)
    send_message(self.client, ('initvideo', vdata))
    send_message(self.client, ('startpreview', 0))
    
  def instructions(self):
    if self.cfg.do_ratings: self.hideratings()
    
    send_message(self.client, ('endpreview', 0))
    
    self.sendcfg()
    
    send_message(self.client, ('instructions', 0))
    receive_message(self.client)
    #if self.cfg.do_ratings: self.showratings()
    print "Instructions done for", self.id

  def initratings(self, neighbors):
    send_message(self.client, ('initratings', neighbors))

  def showratings(self):
    send_message(self.client, ('showratings', 0))

  def hideratings(self):
    send_message(self.client, ('hideratings', 0))

  def disableratings(self):
    send_message(self.client, ('disableratings', 0))

  def introsurvey(self):
    send_message(self.client, ('introsurvey', 0))
    gender, college, status = receive_message(self.client)
    self.cfg._dblog.log_introsurvey(self.id, (gender, college, status))
  
  def exitsurvey(self):
    self.logratings()
    send_message(self.client, ('exitsurvey', 0))
    n_qs = receive_message(self.client)
    responses = []
    for i in range(n_qs):
      (qtext, qresponse) = receive_message(self.client)
      responses.append( (qtext, qresponse) )
      
    self.finalpay = receive_message(self.client)
      
    self.hideratings()
      
    self.cfg._dblog.log_exitsurvey(self.id, responses)
    self.logratings(step='exitsurvey')
    self.logratingstatus('final', range(self.cfg.n))    # Log ratings of everyone
    
    print "Agent", self.id, "exit survey submitted"

  def startcapture(self):
    send_message(self.client, ('startcapture', 0))
    
  def stopcapture(self):
    send_message(self.client, ('stopcapture', 0))

  def endcapture(self):
    send_message(self.client, ('endcapture', 0))

  def update(self):
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
    #nbrdata = [(n.id, n.group.id) for n in self.nbrs]  # old nbrdata
    if self.cfg.show_skills:
      nbrdata = [(n.id, n.group.id, int(np.where(n.skills)[0][0])) for n in self.nbrs]
    else:
      nbrdata = [(n.id, n.group.id, -1) for n in self.nbrs]
    send_message(self.client, ('updatenbrs', nbrdata) )

  def getframetimes(self):
    send_message(self.client, ('getframetimes', 0))
    return receive_message(self.client)   # sframe, eframe, stime, etime

  def logratings(self, simnum = None, iternum = None, step = 'NA'):
    if not self.cfg.do_ratings: return
    send_message(self.client, ('getratinglog', 0))
    ratings = receive_message(self.client)
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
    print "Agent", self.id, "ratings:", ratings

  def logratingstatus(self, eventtype, otherids, gmembers=None):
    if gmembers is not None:
      rtgs = [[self.current_ratings.get(aid) for aid in g if aid in self.current_ratings] for g in gmembers if len(g)]
      grtgs = [[self.global_ratings.get(aid) for aid in g if aid in self.global_ratings] for g in gmembers if len(g)]
      myrtgs = [-1 if not len(rats) else float(sum(rats))/len(rats) for rats in rtgs]
      if self.cfg.show_global_ratings:
        globalrtgs = [-1 if not len(grats) else float(sum(grats))/len(grats) for grats in grtgs]
      else:
        globalrtgs = [-1 for rats in rtgs]
      minrtgs = [-1 if not len(rats) else min(rats) for rats in rtgs]
      maxrtgs = [-1 if not len(rats) else max(rats) for rats in rtgs]
    else:
      myrtgs = [self.current_ratings.get(aid, -1) for aid in otherids]
      globalrtgs = [-1 if not self.cfg.show_global_ratings else self.global_ratings.get(aid,-1) for aid in otherids]
      minrtgs = maxrtgs = [-1 for aid in otherids]
    try:
      self.cfg._dblog.log_ratingstatus(self.cfg.simnumber, self.cfg.iternum, eventtype, self.id, otherids, myrtgs, globalrtgs, minrtgs, maxrtgs)
    except AttributeError:
      self.cfg._dblog.log_ratingstatus(self.cfg.simnumber, -1, eventtype, self.id, otherids, myrtgs, globalrtgs, minrtgs, maxrtgs)

  def getratings(self):
    ratings = send_and_receive(self.client, ('getratings', 0))
    self.current_ratings.update(ratings)
    return self.current_ratings
  
  def updateratings(self, ratings):
    self.global_ratings = ratings
    if self.cfg.show_global_ratings:
      send_message(self.client, ('updateglobalratings', ratings))

  def updatehistory(self, pghistory):
    send_message(self.client, ('updatehistory', pghistory))

  def propose(self):
    task=self.cfg.task
    self.update()   ## Maybe needs to come after the propose message!
    
    nbrgroups = set( n.group for n in self.nbrs )
    nbrgroups.discard(self.group)
    
    if not len(nbrgroups):
      return
    
    idgroups = {g.id:g for g in nbrgroups}

    gdata = sorted([ (g.id, g.gsize, task(g.withskills(self))/(g.gsize+1), [a.id for a in g.agents]) for g in nbrgroups])
    gids, gsizes, newpays, gmembers = zip(*gdata)

    self.logratings()
    self.logratingstatus('apply', gids+(-1, ), gmembers+([a.id for a in self.group.agents],))

    # Send all data to GUI and blocking receive
    send_message(self.client, ('propose', gdata) )

    # Wait for user to reply with list of applications
    applications = receive_message(self.client)
    
    self.logratings(step='apply')
    
    if len(applications):
      gnames = [self.gname(gid) for gid in applications]
      self.messages.append('You applied to group'+('s ' if len(gnames) > 1 else ' ')+', '.join(gnames))
    else:
      self.messages.append('You did not apply to any groups')

    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_apply(self.cfg.simnumber, self.cfg.iternum, self.id, gids, self.nowpay, newpays, applications, sframe, eframe, stime, etime)
    
    print "Agent", self.id, "proposes", applications
  
    for gid in applications:
      g = idgroups[gid]
      g.takeapplication(self)
  
  def acceptvote(self, applicants):
    if not len(applicants):
      # If no applicants, shouldn't be calling this function, but in any case, return None
      return None
    
    task=self.cfg.task
    self.update()

    ## TODO: create a case for group merging
    # acceptvote_groupmerge
    
    idagents = {a.id:a for a in applicants}
    gdata = sorted([ (a.id, task(self.group.withskills(a))/(self.group.gsize+a.gsize)) for a in applicants])
    naids, newpays = zip(*gdata)
    
    self.logratings()
    self.logratingstatus('acceptvote', naids)
    
    # Send all data to GUI and blocking receive
    send_message(self.client, ('acceptvote', gdata) )

    # Wait for user to reply with list of applications
    accept_id = receive_message(self.client)
    
    self.logratings(step='acceptvote')

    naids = list(naids); newpays = list(newpays)
    naids.append(-1); newpays.append(self.nowpay)   # Add the "accept no one" option
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_accept(self.cfg.simnumber, self.cfg.iternum, self.id, naids, self.nowpay, newpays, accept_id, sframe, eframe, stime, etime)


    if accept_id != -1:
      print "Agent", self.id, "votes to accept", accept_id

    if accept_id != -1:
      #self.messages.append('You voted to accept agent '+str(accept_id)+' into the group')
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
    gdata = sorted([ (a.id, task(myg.withoutskills(a))/(myg.gsize-1)) for aid, a in sorted(idagents.items()) if aid != self.id])
    naids, newpays = zip(*gdata)
    
    self.logratings()
    self.logratingstatus('expelvote', naids)
    
    # Send all data to GUI and blocking receive
    send_message(self.client, ('expelvote', gdata) )

    # Wait for user to reply with list of applications
    expel_id = receive_message(self.client)
    
    self.logratings(step='expelvote')

    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_expel(self.cfg.simnumber, self.cfg.iternum, self.id, naids, self.nowpay, newpays, expel_id, sframe, eframe, stime, etime)

    print "Agent", self.id, "votes to expel", expel_id

    if expel_id == -1:
      # No member should leave the team
      return None
    else:
      #self.messages.append('You voted to expel agent '+str(accept_id)+' from the group')
      return idagents[expel_id]


  def consider(self):
    if not len(self.acceptances) or not len([g.gsize for g in self.acceptances if g.gsize > 0]):
      self.messages.append('You received no acceptances')
      return
    
    task = self.cfg.task
    self.update()
    
    idgroups = {g.id:g for g in self.acceptances}

    gdata = sorted([ (g.id, g.gsize, task(g.withskills(self))/(g.gsize+1), [a.id for a in g.agents]) for g in self.acceptances])
    gids, gsizes, gpays, gmembers = zip(*gdata)
    
    self.logratings()
    self.logratingstatus('join', gids+(-1, ), gmembers+([a.id for a in self.group.agents], ))
    
    # Send all data to GUI and blocking receive
    send_message(self.client, ('consider', gdata) )

    # Wait for user to reply with list of applications
    choice_id = receive_message(self.client)
    
    self.logratings(step='join')
    
    if choice_id == -1:
      # Player does not want to switch groups.
      pass 
    else:
      self.messages.append('You switched to group '+self.gname(choice_id))
      self.switchgroup(idgroups[choice_id])
    
    gids = list(gids); gsizes = list(gsizes); gpays = list(gpays)
    gids.append(-1); gsizes.append(self.group.gsize); gpays.append(self.nowpay)  # Add your current group (no change)
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.log_join(self.cfg.simnumber, self.cfg.iternum, self.id, gids, self.nowpay, gpays, choice_id, sframe, eframe, stime, etime)
    
    if choice_id != -1:
      print "Agent", self.id, "joins", choice_id
    
    self.acceptances = []
    
  def notifygaccept(self, aid):
    actor = 'Your group' if self.group.gsize > 1 else 'You'
    if aid != -1:
      self.messages.append(actor+' voted to accept '+self.aname(aid)+' to join your team')
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
      send_message(self.client, ('turndone', '\n'.join(self.messages)) )
      receive_message(self.client)
    else:
      print "No new messages for human player"
    
    #if self.cfg.do_ratings:
    #  self.logratings(step='postprocess_iter')
    self.logratings()
    
    ###TODO: Maybe wait to ensure user is done???
    
    self.messages = []
  
  def postprocess(self, globalpay=None):
    self.update()
    self.messages.append('You earned '+CURR+str(round(self.nowpay,2)))
        
    self.logratings()
    send_message(self.client, ('addpay', round(self.nowpay, 2)) )
    send_message(self.client, ('postprocess', '\n'.join(self.messages)) )
    done = receive_message(self.client)
    self.logratings(step='postprocess')
    
    
    self.messages = []
    
  def postprocess_pg(self, globalpay=None):
    self.update()
    self.messages.append('You can earn '+CURR+str(round(self.nowpay,2))+' on this team.')
    
    self.logratings()
    send_message(self.client, ('postprocess', '\n'.join(self.messages)) )
    #send_message(self.client, ('addpay', round(self.nowpay, 2)) )
    done = receive_message(self.client)
    self.logratings(step='postprocess')
    
    self.logratings()
    
    self.messages = []
  
  ## PUBLIC GOODS FUNCTIONS:
  def publicgoods(self, pgdict):
    self.update()
    
    if self.cfg.do_ratings: self.hideratings()
    send_message(self.client, ('publicgoods_instructions', 0))
    receive_message(self.client)
    if self.cfg.do_ratings: self.showratings()
    
    ## Send team as neighbors
    if self.cfg.show_skills:
      teamdata = [(n.id, n.group.id, int(np.where(n.skills)[0][0])) for n in self.group.agents if n != self]
    else:
      teamdata = [(n.id, n.group.id, -1) for n in self.group.agents if n != self]
    send_message(self.client, ('updatenbrs', teamdata) )    
    
    self.logratings()
    self.logratingstatus('pubgood', [n.id for n in self.group.agents if n != self])
    
    # Send current pay with the publicgoods message
    send_message(self.client, ('publicgoods', int(self.nowpay)))
    contrib = receive_message(self.client)
    self.logratings(step='publicgoods')
    
    print "Agent", self.id, "contribs", contrib, "/", int(self.nowpay)
    
    #return contrib
    pgdict[self] = (contrib, int(self.nowpay)-contrib)
  
    
  def publicgoods_postprocess(self, startpay, keep, contrib, privatepay, potpay, teampays):
    maxcontrib = startpay
    newpay = privatepay + potpay
    self.messages.append('You made '+CURR+str(round(startpay, 2))+' by working with this team.')
    self.messages.append('You contributed '+CURR+str(contrib)+' to the pot and kept '+CURR+str(round(keep,2)))
    cdesc = 'the shared pot' if not configuration.hide_publicgoods else 'the lottery'
    self.messages.append('You received '+CURR+str(round(potpay,2))+' from '+cdesc)
    self.messages.append('You earned '+CURR+str(round(newpay,2))+' this round.')
    #if self.cfg.do_ratings and self.group.gsize > 1:
    #  self.messages.append('You may now rate the behavior of your teammates if you wish.')
    
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
    
    send_message(self.client, ('postprocess', '\n'.join(self.messages)) )
    done = receive_message(self.client)
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
    send_message(self.client, ('u_makeoffer', other_player))
    amount = receive_message(self.client)
    
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.ultevent_insert(self.id, other_player, 'make_offer', amount, sframe, eframe, stime, etime)
    
    return amount

  def wait_offer(self, other_player):
    send_message(self.client, ('u_waitoffer', other_player))
  
  def decide_offer(self, other_player, amount):
    send_message(self.client, ('u_decideoffer', (other_player, amount)))
    result = receive_message(self.client)
    
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.ultevent_insert(self.id, other_player, 'decide_offer', result, sframe, eframe, stime, etime)
    
    return result
  
  def wait_decide(self, other_player):
    send_message(self.client, ('u_waitdecide', other_player))
  
  def show_conclusion_u(self, other_player, amount, result, role):
    send_message(self.client, ('u_conclusion', (other_player, amount, result, role)))
    receive_message(self.client)
    
    if result:
      if role == 0:
        my_amount = 10-amount
      else:
        my_amount = amount
    else:
      my_amount = 0
    sframe, eframe, stime, etime = self.getframetimes()
    self.cfg._dblog.ultevent_insert(self.id, other_player, 'conclusion', my_amount, sframe, eframe, stime, etime)
    
    if self.cfg.do_ratings:
      self.logratings(step='ultimatum', simnum=-1, iternum=-1)
    
  def show_conclusion_d(self, other_player, amount, role):
    send_message(self.client, ('d_conclusion', (other_player, amount, role)))
    
  def u_review(self):
    send_message(self.client, ('u_review', None))
