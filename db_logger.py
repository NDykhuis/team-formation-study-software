#
# db_logger.py - logs data on team formation decisions to SQLite3 database
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


import sqlite3
import time

# Try to use this as little as possible...
from configuration import Configuration

import threading
import Queue

def r2(pay):
  """ Shorthand for 'round to 2 decimals' """
  return round(pay, 2)

class DBLogger(object):
  """Handles logging results to SQLite3 database
  
  Contains numerous methods for logging all aspects of team formation.
  Uses a threaded batch insert system to reduce database commits 
  and improve performance.
  """
  
  def __init__(self, dbfile):
    self.dbfile = dbfile
    
    self.NO_LOGGING = False     # TEMP: Set to true to disable database output
    
    self.sessionid = None   # Init from database in self.setup()
    self.setup()
    
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
    """Setup database schema and get new sessionid"""
    # Types: NULL, INTEGER, REAL, TEXT, BLOB
    print "Setting up database..."
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
    conn.execute('''CREATE TABLE IF NOT EXISTS agentparams
        (rowid integer primary key asc,
        uuid text,
        apply_nohist real, 
        apply_deltapay_aic real,
        apply_deltapay_intercept real, apply_deltapay_slope real,
        apply_pastcontrib_aic integer, 
        apply_pastcontrib_intercept real,  apply_pastcontrib_slope real,
        apply_pastcontrib_slope_pay real,
        acceptvote_nohist real, acceptvote_noaccept real,
        acceptvote_stayaccept real, 
        acceptvote_deltapay_aic real,
        acceptvote_deltapay_intercept real, acceptvote_deltapay_slope real,
        acceptvote_globalrtg_aic real,
        acceptvote_globalrtg_intercept real, acceptvote_globalrtg_slope real,
        acceptvote_globalrtg_slope_pay real,
        acceptvote_pastcontrib_aic real,
        acceptvote_pastcontrib_intercept real, acceptvote_pastcontrib_slope real,
        acceptvote_pastcontrib_slope_pay real,
        join_nohist real,
        join_deltapay_aic real,
        join_deltapay_intercept real, join_deltapay_slope_stay real,
        join_deltapay_slope real,
        join_globalrtg_aic real,
        join_globalrtg_intercept real, join_globalrtg_slope_stay real,
        join_globalrtg_slope real, join_globalrtg_slope_pay real,
        pubgood_avgcontrib real, pubgood_sdcontrib real,
        pubgood_contrib_globalrtg integer,
        pubgood_contrib_globalrtg_intercept real,
        pubgood_contrib_globalrtg_slope real,
        pubgood_contrib_globalrtg_stderr real,
        pubgood_contrib_globalrtg_r2 real,
        pubgood_contrib_pastcontrib integer,
        pubgood_contrib_pastcontrib_intercept real,
        pubgood_contrib_pastcontrib_slope real,
        pubgood_contrib_pastcontrib_stderr real,
        pubgood_contrib_pastcontrib_r2 real,
        pubgood_rating_contrib integer,
        pubgood_rating_contrib_intercept real,
        pubgood_rating_contrib_slope real,
        pubgood_rating_contrib_stderr real,
        pubgood_rating_contrib_r2 real,
        pubgood_ratings_per_round real,
        pubgood_ratings_per_round_sd real,
        pubgood_prop_rounds_nrats_0 real,
        pubgood_rating_props_1 real,
        pubgood_rating_props_2 real,
        pubgood_rating_props_3 real,
        pubgood_rating_props_4 real,
        pubgood_rating_props_5 real,
        pubgood_cum_rating_props_1 real,
        pubgood_cum_rating_props_2 real,
        pubgood_cum_rating_props_3 real,
        pubgood_cum_rating_props_4 real,
        pubgood_cum_rating_props_5 real,
        condition text
        )''')
    self.idparams = {}
    self.paramsid = {}
    conn.commit()
    
    conn.close()
    
    self.log_newsession()
    print "Done!"
    
    
  def log_newsession(self):
    timestamp = time.time()
    conn = sqlite3.connect(self.dbfile)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sessions(starttime) VALUES (?)', (timestamp,))
    self.sessionid = cursor.lastrowid
    # Could also use the SQLite function last_insert_rowid()
    conn.commit()
    conn.close()
    
  def log_config(self, u_rounds, intro_sim, pubgoods, hide_pubgoods, 
                 pubgoods_mult, ratings, timelimit, nhumans, showteam, 
                 keepteams, dynamic, keepgraph, globalratings, nhistory):
    """Log sim configuration to 'session_config' table"""
    if self.NO_LOGGING: return
    
    self.queue_insert('session_config', 
                      (self.sessionid, u_rounds, intro_sim, pubgoods, 
                       hide_pubgoods, pubgoods_mult, ratings, timelimit, 
                       nhumans, showteam, keepteams, dynamic, keepgraph, 
                       globalratings, nhistory))
        
  def log_sessionend(self):
    """Log timestamp of session end to 'sessions' table"""
    endtime = time.time()
    conn = sqlite3.connect(self.dbfile)
    conn.execute('UPDATE sessions SET endtime=? WHERE sessionid=?', (endtime, self.sessionid))
    conn.commit()
    conn.close()

  def log_newsession_fast(self):
    timestamp = time.time()
    self.queue_insert('sessions', (None, timestamp, -1))
    self.sessionid += 1

  def log_gen(self, message):
    """Log generic message to 'log' table"""
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('log', (None, timestamp, self.sessionid, message))
        
  def log_summary(self, data):
    """Log sim summary statistics to a single row in 'tfsummary' table"""
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    outdata = tuple([None, timestamp, self.sessionid]+list(data))
    
    self.queue_insert('tfsummary', outdata)
        
  def log_summary_gen(self, simnum, data):
    """Log all summary data values to separate rows in 'tfdata' table"""
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
    """Log agent types/personalities to 'agent_config' table
    
    agents: list of (agent id, agent type) tuples
    """
    if self.NO_LOGGING: return
    inserts = []
    for aid, atype in agents:
      inserts.append( (None, self.sessionid, aid, atype) )
    
    self.queue_insert('agent_config', inserts, many=True)
        
  def log_ultimatum(self, p1=0, p2=0, amount=0, accepted=0, stime=0, etime=0):
    """Log results of ultimatum to 'ultimatum' table"""
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('ultimatum', (None, timestamp, self.sessionid, p1, p2, amount, accepted, stime, etime))
    
  def tflog_insert(self, inserts):
    """Log team formation event to 'tflog' table
    
    This method is generic and used by other log methods
    to log the relevant data for each step of team formation
    
    inserts = (None, timestamp, sessionid, eventtype, 
               simnum, iternum, userid, otherid, 
               currentpay, newpay, maxpay, chosen)
    """
    if self.NO_LOGGING: return
  
    # Create a column that counts how many other options had the same value
    # newpay is column 9 
    # nsame is column 11
    
    nsames = {} # (value, count) dictionary
    for ins in inserts:
      nsames[ins[9]] = nsames.get(ins[9], 0)+1
    
    # splice in the nsame column (not elegant)
    newinserts = [ins[0:11]+(nsames[ins[9]], ins[11]) for ins in inserts]
    
    self.queue_insert('tflog', newinserts, many=True)
      
  def tfevent_insert(self, data):
    """Log a team formation event to 'tfevent' table
    
    data = (None, timestamp, sessionid, userid, simnum, iternum, 
            eventtype, startframe, endframe, starttime, endtime)
    """
    
    if self.NO_LOGGING: return
    
    self.queue_insert('tfevent', data)
      
  def ultevent_insert(self, userid, otherid, eventtype, value, 
                      sframe, eframe, stime, etime):
    """Log an ultimatum event to 'ultevent' table"""
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('ultevent', (None, timestamp, self.sessionid, userid, otherid, eventtype, value, sframe, eframe, stime, etime))
      
  def log_topo(self, simnum, aid, nbrids):
    """Log graph topology info to 'neighborlist' and 'neighbors' tables
    
    aid: agent ID
    nbrids: list of neighbor IDs
    """
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
      
  def log_apply(self, simnum, iternum, aid, gids, 
                currpay, newpays, applications, 
                sframe=-1, eframe=-1, stime=-1, etime=-1):
    """Log apply event to 'tflog' and 'tfevent' tables
    
    gids: list of groups to apply to
    currpay: current pay amount
    newpays: list of how much each new group pays
    applications: list of which group IDs applied to
    """
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for gid, newpay in zip(gids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'apply', simnum, iternum, aid, gid, r2(currpay), r2(newpay), maxpay, gid in applications) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'apply', sframe, eframe, stime, etime) )
    
  def log_accept(self, simnum, iternum, aid, naids, 
                 currpay, newpays, accepts, 
                 sframe=-1, eframe=-1, stime=-1, etime=-1):
    """Log acceptvote event to 'tflog' and 'tfevent' tables
    
    naids: list of applicant ids
    currpay: current pay amount
    newpays: list of how much each applicant would pay
    accepts: ID of agent receiving accept vote
    """
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for aidvote, newpay in zip(naids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'acceptvote', simnum, iternum, aid, aidvote, r2(currpay), r2(newpay), maxpay, aidvote == accepts) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'acceptvote', sframe, eframe, stime, etime) )
    
  def log_join(self, simnum, iternum, aid, gids, 
               currpay, newpays, acceptance, 
               sframe=-1, eframe=-1, stime=-1, etime=-1):
    """Log join event to 'tflog' and 'tfevent' tables
    
    gids: list of groups to join
    currpay: current pay amount
    newpays: list of how much each group would pay
    acceptance: ID of group chosen to join
    """
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for gid, newpay in zip(gids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'join', simnum, iternum, aid, gid, r2(currpay), r2(newpay), maxpay, gid == acceptance) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'join', sframe, eframe, stime, etime) )
    
  def log_expel(self, simnum, iternum, aid, naids, 
                currpay, newpays, expels, 
                sframe=-1, eframe=-1, stime=-1, etime=-1):
    """Log expelvote event to 'tflog' and 'tfevent' tables
    
    naids: list of team member ids
    currpay: current pay amount
    newpays: list of how much expelling each member would pay
    accepts: ID of agent receiving expel vote
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    maxpay = r2(max(newpays))
    for aide, newpay in zip(naids, newpays):
      inserts.append( (None, timestamp, self.sessionid, 'expelvote', simnum, iternum, aid, aide, r2(currpay), r2(newpay), maxpay, aid == expels) )
    self.tflog_insert(inserts)
    self.tfevent_insert( (None, timestamp, self.sessionid, aid, simnum, iternum, 'expelvote', sframe, eframe, stime, etime) )
  
  def log_conclusion(self, groups, simnum):
    """Log final group id and pay to 'tfrounds' table
    
    groups: list of group objects
    """
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
    
  def log_pubgoods(self, simnum, userid, gid, otherids, 
                   usercontrib, othercontribs, keep, pay, 
                   sframe=-1, eframe=-1, stime=-1, etime=-1):
    """Log pubgoods data to 'tflog' and 'tfevent' tables
    
    gid: group ID (not used)
    otherids: ids of team members
    usercontrib: this agent's contribution (currentpay)
    othercontribs: list of team member contributions (newpay)
    keep: pay not contributed
          --> amount agent started with goes in maxpay
    pay: final pay  (not used, see log_all_pubgoods)
    """
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
    """Log pubgoods data to 'pglog' table
    
    pgtuple = (agentid, groupid, contrib, keep, pay)
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for agentid, groupid, contrib, keep, pay in pgtuples:
      inserts.append( (None, timestamp, self.sessionid, simnum, agentid, groupid, contrib, keep, pay) )
    self.queue_insert('pglog', inserts, many=True)
    
  def log_all_pubgoods_extra(self, simnum, pgtuples): 
    """Log extended pubgoods data to 'pglog' and 'pglog_extra' tables
    
    pgtuple = (agentid, groupid, contrib, keep, pay, avgrating, avgcontrib, multiplier, sharedamount)
    """
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
    """Log team IDs of each agent to 'teamstatus' table
    
    gdata = (group ID, [group member IDs], group pay)
    activeagent: the currently-deciding agent, used during 'join' step
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for gid, gmembers, gpay in gdata:
      for aid in gmembers:
        inserts.append( (None, timestamp, self.sessionid, eventtype, simnum, iternum, activeagent, aid, gid, gpay) )
    
    self.queue_insert('teamstatus', inserts, many=True)
        
  def log_ratings(self, logdata):
    """Log each agent's ratings of the other agents to 'ratings' table
    
    logdata=(userid, otherid, rating, eframe, etime, simnum, iternum, step)
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    iternum = -1
    inserts = []
    for userid, otherid, rating, eframe, etime, simnum, iternum, step in logdata:
      inserts.append( (None, timestamp, self.sessionid, userid, otherid, rating, eframe, etime, simnum, iternum, step) )
    
    self.queue_insert('ratings', inserts, many=True)
      
  def log_ratingstatus(self, simnum, iternum, eventtype, aid, otherids, myrtgs, globalrtgs, minrtgs, maxrtgs):
    """Log current ratings of agents or groups to 'ratingstatus' table
    
    otherids: IDs of other agents or groups
    myrtgs: my rating of an agent, or my average rating of a group
    globalrtgs: global rating of an agent, or average global rating of a group
    minrtgs, maxrtgs: lowest and highest personal rating of group members
                      (only used for groups)
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for otherid, myrtg, globalrtg, minrtg, maxrtg in zip(otherids, myrtgs, globalrtgs, minrtgs, maxrtgs):
      inserts.append( (None, timestamp, self.sessionid, eventtype, simnum, iternum, aid, otherid, myrtg, globalrtg, minrtg, maxrtg) )
    
    self.queue_insert('ratingstatus', inserts, many=True)
      
  def log_globalratings(self, simnum, iternum, aidratingdict, eframe=-1, etime=-1):
    """Log current global ratings of all agents
    
    aidratingdict = {agent id:rating}
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for aid, rating in aidratingdict.iteritems():
      inserts.append( (None, timestamp, self.sessionid, simnum, iternum, aid, rating, eframe, etime) )
    
    self.queue_insert('globalratings', inserts, many=True)
      
  def log_introsurvey(self, aid, responses):
    """Log intro survey responses to 'introresponses'
    
    responses = (gender, college, status)
    """
    timestamp = time.time()
    gender, college, status = responses
    
    self.queue_insert('introresponses', (None, timestamp, self.sessionid, aid, gender, college, status))
    
  def get_qid(self, qtext, conn):
    """Get exit survey question ID, given a question's text
    
    If question's text is not found, add it to 'exitquestionids' table
    """
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

  def log_exitsurvey(self, aid, responses):
    """Log exit survey responses to 'exitresponses'
    
    responses = (question text, question response)
    """
    timestamp = time.time()
    conn = sqlite3.connect(self.dbfile) # KEEP
    for qtext, qresponse in responses:
      qid = self.get_qid(qtext, conn)
      conn.execute('INSERT INTO exitresponses VALUES (?,?,?,?,?,?)', (None, timestamp, self.sessionid, aid, qid, qresponse))
    conn.commit() # KEEP
    conn.close() # KEEP
  
  def log_finalpay(self, paydata):
    """Log final pay for each agent to 'finalpay' table
    
    paydata = (agent id, final pay)
    """
    if self.NO_LOGGING: return
    timestamp = time.time()
    inserts = []
    for userid, pay in paydata:
      inserts.append( (None, timestamp, self.sessionid, userid, pay, Configuration.exchange_rate) )
    
    self.queue_insert('finalpay', inserts, many=True)
        
  def log_simtime(self, simnum, iternum, stime, etime):
    """Log elapsed time of a simulation round to 'simtime' table"""
    if self.NO_LOGGING: return
    timestamp = time.time()
    
    self.queue_insert('simtime', (None, timestamp, self.sessionid, simnum, iternum, stime, etime, etime-stime))

  def log_simhumanagent(self, agent):
    # Try to ensure that we don't log duplicate agent configurations here
    atuple = agent.to_tuple(dbcompat=True)
    if atuple[0] not in self.idparams:
      self.queue_insert('agentparams', (None,) + atuple)
      self.idparams[atuple[0]] = atuple
    
    #if atuple[1:] not in self.paramsid:
      #self.queue_insert('agentparams', atuple)
      #rowid = cursor.lastrowid
      #self.paramsid[atuple[1:]] = rowid
      #self.idparams[rowid] = atuple
     
  def queue_insert(self, instable, instuple, many=False):
    """Queue an insert for the database
    
    instable:  the table in which to make the insert
    instuple:  tuple of values for each column, or list of these tuples
    many: False if this is a single insert, True if instuple is a list
          (decides whether to use execute or executemany to make the insert)
    """
    self.insqueue.put( (instable, instuple, many) ) 
  
  def batch_inserts(self, forcecommit=True):
    """Insert all items from self.insqueue and commit if forcecommit is set."""
    conn = sqlite3.connect(self.dbfile)
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
    """Thread that makes batch inserts from self.insqueue
    
    Speeds up performance by minimizing number of commits 
    for bursts of inserts.
    
    Get all waiting inserts and execute them.
    Once no inserts come in for 2 seconds, commit all inserts.
    Continue while self.autoins
    """
    print "Database insert thread started"
    commits = False
    conn = sqlite3.connect(self.dbfile)
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
      self.forcecommit = False
    conn.close()
    print "Database insert thread ended"
    
  def start_batch_insert_thread(self):
    """Start thread that makes batch inserts from self.insqueue"""
    self.autoins = True
    t = threading.Thread(target=self.batch_insert_thread)
    self.insthread = t
    
    # Note that this could lose data! 
    # But also makes it easier to quit the server...
    t.daemon = True
    
    t.start()
    
  def stop_batch_insert_thread(self):
    """End the batch insert thread"""
    self.autoins = False
    
  def __del__(self):
    """On object destruction, do inserts and end the batch insert thread"""
    if self.insthread:
      self.autoins = False
      self.insthread.join()

  def force_commit(self):
    self.forcecommit = True

  def flush_inserts(self):
    """Ensure that insert queue is empty"""
    
    if not self.insthread.isAlive():
      raise RuntimeError("Database insert thread is dead!")

    self.insqueue.join()
