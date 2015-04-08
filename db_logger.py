import sqlite3
import datetime
import time
import sys
from configuration import configuration    # Try to use this as little as possible...

import threading
import Queue

def r2(pay):
  return round(pay, 2)

class db_logger(object):
  def __init__(self, dbfile):
    self.dbfile = dbfile
    self.setup()
    
    self.NO_LOGGING = False     # TEMP: Set to true to disable database output
    
    # Threaded producer-consumer code
    self.insthread = None
    self.autoins = False
    self.forcecommit = False
    self.insqueue = Queue.Queue()

  # Team formation:
  #   what do people apply to?
  #     turn id, user id, group, current pay, new group pay, applied or not  (max group pay?)
  #     (also, what have people applied to previously?)
  #   how do people pick new teammates?
  #     turn id, user id, applicant id, current pay, new pay, accepted or not  (max applicant pay?)
  #     (also, who have people accepted previously?)
  #   how do people decide what team to join?
  #     turn id, user id, group, current pay, new group pay, joined or not  (max group pay?)
  
  def setup(self):
    # Types: NULL, INTEGER, REAL, TEXT, BLOB
    conn = sqlite3.connect(self.dbfile)
    conn.execute('''CREATE TABLE IF NOT EXISTS sessions 
        (sessionid integer primary key asc, 
         starttime real, endtime real DEFAULT -1)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS session_config
        (sessionid integer primary key asc, 
         ultimatum_rounds integer, 
         intro_sim integer,
         public_goods integer, hide_public_goods integer,
         pubgoods_mult real,
         ratings integer, timelimit real, nhumans integer,
         show_team_members integer, keep_teams integer,
         dynamic_network integer, keep_graph integer,
         show_global_ratings integer, show_nhistory integer)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tfsummary
        (rowid integer primary key asc,
         timestamp real, sessionid integer, simnum integer,
         start_time real, end_time real, elapsed_time real, iterations integer,
         num_groups integer, singletons integer,
         avg_switches real, avg_earnings real, 
         human_pay real, dumb_pay real, greedy_pay real)
         ''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tfdata
        (rowid integer primary key asc,
         timestamp real, sessionid integer, simnum integer,
         colname text, nvalue real, tvalue text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS log 
        (rowid integer primary key asc,
         timestamp real unique, sessionid integer, 
        description text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS agent_config
        (rowid integer primary key asc,
         sessionid integer, agentid integer,
         agenttype text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ultimatum 
        (rowid integer primary key asc,
        timestamp real unique, sessionid integer, 
        giver integer, receiver integer, 
        amount integer, accepted integer,
        stime real, etime real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ultevent
         (rowid integer primary key asc,
          timestamp real, sessionid integer,
          userid integer, otherid integer, 
          eventtype text, value integer,
          sframe integer, eframe integer,
          stime real, etime real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS neighborlist
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         simnum integer, userid integer, neighbors text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS neighbors
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         simnum integer, userid integer, neighbor integer)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tflog
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         eventtype text, simnum integer, iternum integer,
         userid integer, otherid integer,
         currentpay real, newpay real, maxpay real,
         nsame integer, chosen integer)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tfevent
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         userid integer, simnum integer, iternum integer,
         eventtype text, 
         sframe integer, eframe integer,
         stime real, etime real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS teamstatus
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         eventtype text, simnum integer, internum integer,
         activeagent integer,
         agentid integer, teamid integer,
         currentpay real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ratingstatus
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         eventtype text, simnum integer, iternum integer,
         userid integer, otherid integer,
         myrtg real, globalrtg real,
         minrtg integer, maxrtg integer
         )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS globalratings
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         simnum integer, iternum integer,
         userid integer, avgrating real,
         eframe real, etime real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tfrounds
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         simnum integer, userid integer, groupid integer, human integer,
         pay real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS pglog
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         simnum integer, userid integer, groupid integer,
         contrib real, keep real, pay real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS pglog_extra
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         simnum integer, userid integer, groupid integer,
         contrib real, keep real, pay real,
         avgrating real, avgcontrib real, multiplier real,
         sharedamount real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS exitquestionids
        (qid integer primary key asc, qtext text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS exitresponses
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         userid integer, qid integer, qresponse text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS introresponses 
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         userid integer, gender text, college text, status text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ratings
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         userid integer, otherid integer,
         rating integer, 
         eframe integer, etime real,
         simnum integer, iternum integer, step text)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS finalpay
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         userid integer, pay real, exchange_rate real)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS simtime
        (rowid integer primary key asc,
         timestamp real, sessionid integer,
         simnum integer, iternum real, stime real, etime real, ttime real)''')
    conn.commit()
    
    timestamp = time.time()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sessions(starttime) VALUES (?)', (timestamp,))
    self.sessionid = cursor.lastrowid   # Could also use the SQLite function last_insert_rowid()
    conn.commit()
    
    conn.close()
    
    
  def log_config(self, u_rounds, intro_sim, pubgoods, hide_pubgoods, pubgoods_mult, ratings, timelimit, nhumans, showteam, keepteams, dynamic, keepgraph, globalratings, nhistory):
    if self.NO_LOGGING: return
    
    self.queue_insert('session_config', (self.sessionid, u_rounds, intro_sim, pubgoods, hide_pubgoods, pubgoods_mult, ratings, timelimit, nhumans, showteam, keepteams, dynamic, keepgraph, globalratings, nhistory))
        
  def log_sessionend(self):
    endtime = time.time()
    conn=sqlite3.connect(self.dbfile)
    conn.execute('UPDATE sessions SET endtime=? WHERE sessionid=?', (endtime, self.sessionid))
    conn.commit()
    conn.close()
        
  def log_gen(self, message):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('log', (None, timestamp, self.sessionid, message))
        
  def log_summary(self, data):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    outdata = tuple([None, timestamp, self.sessionid]+list(data))
    
    self.queue_insert('tfsummary', outdata)
        
  def log_summary_gen(self, simnum, data):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    inserts = []
    ditems = sorted(data.items())
    for item, value in ditems:
      try:
        v = float(value)
        inserts.append( (None, timestamp, self.sessionid, simnum, item, v, '') )
      except (ValueError, TypeError):
        t = str(value)
        inserts.append( (None, timestamp, self.sessionid, simnum, item, -1, t) )
      except:
        print "Problem with:", item, value
    
    self.queue_insert('tfdata', inserts, many=True)
        
  def log_agentconfig(self, agents):
    if self.NO_LOGGING: return
    inserts = []
    for aid, atype in agents:
      inserts.append( (None, self.sessionid, aid, atype) )
    
    self.queue_insert('agent_config', inserts, many=True)
        
  def log_ultimatum(self, p1=0, p2=0, amount=0, accepted=0, stime=0, etime=0):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('ultimatum', (None, timestamp, self.sessionid, p1, p2, amount, accepted, stime, etime))
    
  def tflog_insert(self, inserts):
    if self.NO_LOGGING: return
  
    # Create a column that counts how many other options had the same value
    # newpay is column 9 
    # nsame is column 11
    
    nsames = {} # (value, count) dictionary
    for ins in inserts:
      nsames[ins[9]] = nsames.get(ins[9],0)+1
    
    newinserts = [ins[0:11]+(nsames[ins[9]],ins[11]) for ins in inserts]   # splice in the nsame column (not elegant)
    
    self.queue_insert('tflog', newinserts, many=True)
      
  def tfevent_insert(self, data):
    # data = (timestamp, session, userid, simnum, iternum, event, sframe, eframe, stime, etime)
    if self.NO_LOGGING: return
    
    self.queue_insert('tfevent', data)
      
  def ultevent_insert(self, userid, otherid, eventtype, value, sframe, eframe, stime, etime):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('ultevent', (None, timestamp, self.sessionid, userid, otherid, eventtype, value, sframe, eframe, stime, etime))
      
  def log_topo(self, simnum, aid, nbrids):
    if self.NO_LOGGING: return
    timestamp = time.time()
    nbrids = sorted(nbrids)
    nbridstring = ','.join([str(nid) for nid in nbrids])
    # Insert timestamp, round, aid, str(nbrids)
    inserts = []
    for nid in nbrids:
      inserts.append( (None, timestamp, self.sessionid, simnum, aid, nid) )
    
    self.queue_insert('neighborlist', (None, timestamp, self.sessionid, simnum, aid, nbridstring))
    self.queue_insert('neighbors', inserts, many=True)
      
  def log_apply(self, simnum, iternum, aid, gids, currpay, newpays, applications, sframe=-1, eframe=-1, stime=-1, etime=-1):
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for gid, newpay in zip(gids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'apply', simnum, iternum, aid, gid, r2(currpay), r2(newpay), maxpay, gid in applications) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'apply', sframe, eframe, stime, etime) )
    
  def log_accept(self, simnum, iternum, aid, naids, currpay, newpays, accepts, sframe=-1, eframe=-1, stime=-1, etime=-1):
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for aidvote, newpay in zip(naids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'acceptvote', simnum, iternum, aid, aidvote, r2(currpay), r2(newpay), maxpay, aidvote == accepts) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'acceptvote', sframe, eframe, stime, etime) )
    
  def log_join(self, simnum, iternum, aid, gids, currpay, newpays, acceptance, sframe=-1, eframe=-1, stime=-1, etime=-1):
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for gid, newpay in zip(gids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'join', simnum, iternum, aid, gid, r2(currpay), r2(newpay), maxpay, gid == acceptance) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'join', sframe, eframe, stime, etime) )
    
  def log_expel(self, simnum, iternum, aid, naids, currpay, newpays, expels, sframe=-1, eframe=-1, stime=-1, etime=-1):
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for aide, newpay in zip(naids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'expelvote', simnum, iternum, aid, aide, r2(currpay), r2(newpay), maxpay, aid == expels) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'expelvote', sframe, eframe, stime, etime) )
  
  def log_conclusion(self, groups, simnum):
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for g in groups:
      pay = g.nowpay
      gid = g.id
      for a in g.agents:
        #pay = a.nowpay
        inserts.append( (None, timestamp, self.sessionid, simnum, a.id, gid, (1 if a.type=='human' else 0), pay) )
    
    self.queue_insert('tfrounds', inserts, many=True)
    
  def log_pubgoods(self, simnum, userid, gid, otherids, usercontrib, othercontribs, keep, pay, sframe=-1, eframe=-1, stime=-1, etime=-1):
    if self.NO_LOGGING: return
    timestamp = time.time()
    iternum = -1
    inserts = []
    for otherid, othercontrib in zip(otherids, othercontribs):
      inserts.append( (None, timestamp, self.sessionid, 'pubgood', simnum, iternum, userid, otherid, usercontrib, othercontrib, usercontrib+keep, -1) )   # A little hacky to shove this into tflog, but we'll leave it for now.
    self.tflog_insert(inserts)
    # currentpay = usercontrib
    # newpay = othercontrib
    # maxpay = amount group earned
    
    #self.queue_insert('pglog', (None, timestamp, self.sessionid, simnum, userid, gid, usercontrib, keep, pay))
    
    self.tfevent_insert( (None, timestamp, self.sessionid, userid, simnum, iternum, 'pubgood', sframe, eframe, stime, etime) )
    
  def log_all_pubgoods(self, simnum, pgtuples): 
    #pgtuple = (agentid, groupid, contrib, keep, pay)
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for agentid, groupid, contrib, keep, pay in pgtuples:
      inserts.append( (None, timestamp, self.sessionid, simnum, agentid, groupid, contrib, keep, pay) )
    self.queue_insert('pglog', inserts, many=True)
    
  def log_all_pubgoods_extra(self, simnum, pgtuples): 
    #pgtuple = (agentid, groupid, contrib, keep, pay, avgrating, avgcontrib, multiplier, sharedamount)
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    exinserts = []
    for agentid, groupid, contrib, keep, pay, avgrating, avgcontrib, multiplier, sharedamount in pgtuples:
      inserts.append( (None, timestamp, self.sessionid, simnum, agentid, groupid, contrib, keep, pay) )
      exinserts.append( (None, timestamp, self.sessionid, simnum, agentid, groupid, contrib, keep, pay, avgrating, avgcontrib, multiplier, sharedamount) )
    self.queue_insert('pglog', inserts, many=True)
    self.queue_insert('pglog_extra', exinserts, many=True)
    
    
  def log_teamstatus(self, simnum, iternum, eventtype, gdata, activeagent=-1):
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for gid, gmembers, gpay in gdata:
      for aid in gmembers:
        inserts.append( (None, timestamp, self.sessionid, eventtype, simnum, iternum, activeagent, aid, gid, gpay) )
    
    self.queue_insert('teamstatus', inserts, many=True)
        
  def log_ratings_OLD(self, simnum, userid, gid, otherids, ratings, sframe=-1, eframe=-1, stime=-1, etime=-1):
    timestamp = time.time()
    iternum = -1
    inserts = []
    for otherid, rating in zip(otherids, ratings):
      inserts.append( (None, timestamp, self.sessionid, 'rating', simnum, iternum, userid, otherid, -1, rating, -1, -1) )   # A little hacky to shove this into tflog, but we'll leave it for now.
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, userid, simnum, iternum, 'rating', sframe, eframe, stime, etime) )

  def log_ratings(self, logdata):
    if self.NO_LOGGING: return
    timestamp = time.time()
    iternum = -1
    inserts = []
    for userid, otherid, rating, eframe, etime, simnum, iternum, step in logdata:
      inserts.append( (None, timestamp, self.sessionid, userid, otherid, rating, eframe, etime, simnum, iternum, step) )
    
    self.queue_insert('ratings', inserts, many=True)
      
  def log_ratingstatus(self, simnum, iternum, eventtype, aid, otherids, myrtgs, globalrtgs, minrtgs, maxrtgs):
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for otherid, myrtg, globalrtg, minrtg, maxrtg in zip(otherids, myrtgs, globalrtgs, minrtgs, maxrtgs):
      inserts.append( (None, timestamp, self.sessionid, eventtype, simnum, iternum, aid, otherid, myrtg, globalrtg, minrtg, maxrtg) )
    
    self.queue_insert('ratingstatus', inserts, many=True)
      
  def log_globalratings(self, simnum, iternum, aidratingdict, eframe=-1, etime=-1):
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for aid, rating in aidratingdict.iteritems():
      inserts.append( (None, timestamp, self.sessionid, simnum, iternum, aid, rating, eframe, etime) )
    
    self.queue_insert('globalratings', inserts, many=True)
      
  def log_introsurvey(self, aid, responses):
    timestamp = time.time()
    gender, college, status = responses
    
    self.queue_insert('introresponses', (None, timestamp, self.sessionid, aid, gender, college, status))
    
  def get_qid(self, qtext, conn):
    q = conn.execute('SELECT qid FROM exitquestionids WHERE qtext = ?', (qtext,) )
    result = q.fetchone()
    if result is not None:
      return result[0]
    else:
      conn.execute('INSERT INTO exitquestionids(qtext) VALUES (?)', (qtext,))
      q = conn.execute('SELECT qid FROM exitquestionids WHERE qtext = ?', (qtext,) )
      result = q.fetchone()
      if result is not None:
        return result[0]
      else:
        raise KeyError("qtext not found in exitquestionids after creation!")
        return None

  def log_exitsurvey(self, aid, responses):
    timestamp = time.time()
    conn=sqlite3.connect(self.dbfile) # KEEP
    for qtext, qresponse in responses:
      qid = self.get_qid(qtext, conn)
      conn.execute('INSERT INTO exitresponses VALUES (?,?,?,?,?,?)', (None, timestamp, self.sessionid, aid, qid, qresponse))
    conn.commit() # KEEP
    conn.close() # KEEP
  
  def log_finalpay(self, paydata):  # paydata is (id, pay) tuples
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for userid, pay in paydata:
      inserts.append( (None, timestamp, self.sessionid, userid, pay, configuration.exchange_rate) )
    
    self.queue_insert('finalpay', inserts, many=True)
        
  def log_simtime(self, simnum, iternum, stime, etime):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('simtime', (None, timestamp, self.sessionid, simnum, iternum, stime, etime, etime-stime))
        
  def queue_insert(self, instable, instuple, many=False):
    self.insqueue.put( (instable, instuple, many) ) 
  
  def batch_inserts(self, forcecommit=True):
    conn=sqlite3.connect(self.dbfile)
    while not self.insqueue.empty():
      try:
        instable, instuple, many = self.insqueue.get(False)
      except Queue.Empty:
        break
      else:
        if not many:
          nqs = len(instuple)-1
          conn.execute('INSERT INTO '+instable+' VALUES (?'+',?'*nqs+')', instuple)
        elif len(instuple):     # Ensure at least one insert exists
          nqs = len(instuple[0])-1
          conn.executemany('INSERT INTO '+instable+' VALUES (?'+',?'*nqs+')', instuple)
        self.insqueue.task_done()
            
    if forcecommit:
      conn.commit()
    
  def batch_insert_thread(self):
    print "Database insert thread started"
    commits = False
    conn=sqlite3.connect(self.dbfile)
    waiting = 0
    while self.autoins:
      try:
        instable, instuple, many = self.insqueue.get(block=True, timeout=2.0)
        if not many:
          nqs = len(instuple)-1
          conn.execute('INSERT INTO '+instable+' VALUES (?'+',?'*nqs+')', instuple)
        elif len(instuple):     # Ensure at least one insert exists
          nqs = len(instuple[0])-1
          conn.executemany('INSERT INTO '+instable+' VALUES (?'+',?'*nqs+')', instuple)
        self.insqueue.task_done()
        
        if self.forcecommit:
          conn.commit()
        else:
          commits = True
      except Queue.Empty:
        if commits:
          conn.commit()
          commits = False
        waiting = 0
      self.forcecommit = False
    conn.close()
    print "Database insert thread ended"
    
  def start_batch_insert_thread(self):
    self.autoins = True
    # start thingy in thread
    t = threading.Thread(target=self.batch_insert_thread)
    self.insthread = t
    t.daemon = True     # Note that this could lose data! But also makes it easier to quit the server...
    t.start()
    
  def stop_batch_insert_thread(self):
    self.autoins = False
    
  def __del__(self):
    if self.insthread:
      self.autoins = False
      self.insthread.join()

  def flush_inserts(self):
    self.insqueue.join()
