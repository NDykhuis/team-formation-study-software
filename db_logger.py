import sqlite3
import datetime
import time
import sys
from configuration import configuration    # Try to use this as little as possible...

def r2(pay):
  return round(pay, 2)

class db_logger(object):
  def __init__(self, dbfile):
    self.dbfile = dbfile
    self.setup()
    
    self.NO_LOGGING = False     # TEMP: Set to true to disable database output

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
         show_team_members integer)''')
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
    conn.execute('''CREATE TABLE IF NOT EXISTS tfsetup
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         simnum integer, userid integer, neighbors text)''')
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
    conn.execute('''CREATE TABLE IF NOT EXISTS ratingstatus
        (rowid integer primary key asc,
         timestamp real, sessionid integer, 
         eventtype text, simnum integer, iternum integer,
         userid integer, otherid integer,
         currtg integer, avgrtg integer,
         minrtg integer, maxrtg integer
         )''')
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
    
    
  def log_config(self, u_rounds, intro_sim, pubgoods, hide_pubgoods, pubgoods_mult, ratings, timelimit, nhumans, showteam):
    if self.NO_LOGGING: return
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO session_config VALUES (?,?,?,?,?,?,?,?,?,?)',
      (self.sessionid, u_rounds, intro_sim, pubgoods, hide_pubgoods, pubgoods_mult, ratings, timelimit, nhumans, showteam))
    conn.commit()
    conn.close()
    
  def log_sessionend(self):
    endtime = time.time()
    conn = sqlite3.connect(self.dbfile)
    conn.execute('UPDATE sessions SET endtime=? WHERE sessionid=?', (endtime, self.sessionid))
    conn.commit()
    conn.close()
    
  def log_gen(self, message):
    if self.NO_LOGGING: return
    timestamp = time.time()
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO log VALUES (?,?,?,?)', (None, timestamp, self.sessionid, message))
    conn.commit()
    conn.close()
    
  def log_summary(self, data):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    outdata = tuple([None, timestamp, self.sessionid]+list(data))
         
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO tfsummary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', outdata)
    conn.commit()
    conn.close()
    
  def log_summary_gen(self, simnum, data):
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    inserts = []
    ditems = sorted(data.items())
    for item, value in ditems:
      try:
        v = float(value)
        inserts.append( (None, timestamp, self.sessionid, simnum, item, v, '') )
      except ValueError:
        t = str(value)
        inserts.append( (None, timestamp, self.sessionid, simnum, item, -1, t) )
      except TypeError:
        print "Problem with:", item, value
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO tfdata VALUES (?,?,?,?,?,?,?)', inserts)
    conn.commit()
    conn.close()
    
  def log_agentconfig(self, agents):
    if self.NO_LOGGING: return
    inserts = []
    for aid, atype in agents:
      inserts.append( (None, self.sessionid, aid, atype) )
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO agent_config VALUES (?,?,?,?)', inserts)
    conn.commit()
    conn.close()
    
  def log_ultimatum(self, p1=0, p2=0, amount=0, accepted=0, stime=0, etime=0):
    if self.NO_LOGGING: return
    timestamp = time.time()
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO ultimatum VALUES (?,?,?,?,?,?,?,?,?)', (None, timestamp, self.sessionid, p1, p2, amount, accepted, stime, etime))
    conn.commit()
    conn.close()

  def tflog_insert(self, inserts):
    if self.NO_LOGGING: return
  
    # Create a column that counts how many other options had the same value
    # newpay is column 9 
    # nsame is column 11
    
    nsames = {} # (value, count) dictionary
    for ins in inserts:
      nsames[ins[9]] = nsames.get(ins[9],0)+1
    
    newinserts = [ins[0:11]+(nsames[ins[9]],ins[11]) for ins in inserts]   # splice in the nsame column (not elegant)
  
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO tflog VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', newinserts)
    conn.commit()
    conn.close()
  
  def tfevent_insert(self, data):
    # data = (timestamp, session, userid, simnum, iternum, event, sframe, eframe, stime, etime)
    if self.NO_LOGGING: return
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO tfevent VALUES (?,?,?,?,?,?,?,?,?,?,?)', data)
    conn.commit()
    conn.close()
  
  def ultevent_insert(self, userid, otherid, eventtype, value, sframe, eframe, stime, etime):
    if self.NO_LOGGING: return
    timestamp = time.time()
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO ultevent VALUES (?,?,?,?,?,?,?,?,?,?,?)', (None, timestamp, self.sessionid, userid, otherid, eventtype, value, sframe, eframe, stime, etime))
    conn.commit()
    conn.close()
  
  def log_topo(self, simnum, agent):
    if self.NO_LOGGING: return
    timestamp = time.time()
    aid = agent.id
    nbrids = ','.join([str(n.id) for n in agent.nbrs])
    # Insert timestamp, round, aid, str(nbrids)
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO tfsetup VALUES (?,?,?,?,?,?)', (None, timestamp, self.sessionid, simnum, aid, nbrids))
    conn.commit()
    conn.close()
  
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
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO tfrounds VALUES (?,?,?,?,?,?,?,?)', inserts)
    conn.commit()
    conn.close()

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
    
    conn=sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO pglog VALUES (?,?,?,?,?,?,?,?,?)',
         (None, timestamp, self.sessionid, simnum, userid, gid, usercontrib, keep, pay))
    conn.commit() 
    conn.close()
        
    self.tfevent_insert( (None, timestamp, self.sessionid, userid, simnum, iternum, 'pubgood', sframe, eframe, stime, etime) )
    
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
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO ratings VALUES (?,?,?,?,?,?,?,?,?,?,?)', inserts)
    conn.commit()
    conn.close()
  
  def log_ratingstatus(self, simnum, iternum, eventtype, aid, otherids, currtgs, avgrtgs, minrtgs, maxrtgs):
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for otherid, currtg, avgrtg, minrtg, maxrtg in zip(otherids, currtgs, avgrtgs, minrtgs, maxrtgs):
      inserts.append( (None, timestamp, self.sessionid, eventtype, simnum, iternum, aid, otherid, currtg, avgrtg, minrtg, maxrtg) )
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO ratingstatus VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', inserts)
    conn.commit()
    conn.close()
  
  def log_introsurvey(self, aid, responses):
    timestamp = time.time()
    gender, college, status = responses
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO introresponses VALUES (?,?,?,?,?,?,?)', (None, timestamp, self.sessionid, aid, gender, college, status))
    conn.commit()
    conn.close()

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
    conn = sqlite3.connect(self.dbfile)
    for qtext, qresponse in responses:
      qid = self.get_qid(qtext, conn)
      conn.execute('INSERT INTO exitresponses VALUES (?,?,?,?,?,?)', (None, timestamp, self.sessionid, aid, qid, qresponse))
    conn.commit()
    conn.close()
  
  def log_finalpay(self, paydata):  # paydata is (id, pay) tuples
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for userid, pay in paydata:
      inserts.append( (None, timestamp, self.sessionid, userid, pay, configuration.exchange_rate) )
    conn = sqlite3.connect(self.dbfile)
    conn.executemany('INSERT INTO finalpay VALUES (?,?,?,?,?,?)', inserts)
    conn.commit()
    conn.close()
    
  def log_simtime(self, simnum, iternum, stime, etime):
    if self.NO_LOGGING: return
    timestamp = time.time()
    conn = sqlite3.connect(self.dbfile)
    conn.execute('INSERT INTO simtime VALUES (?,?,?,?,?,?,?,?)', (None, timestamp, self.sessionid, simnum, iternum, stime, etime, etime-stime))
    conn.commit()
    conn.close()