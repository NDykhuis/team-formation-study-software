import threading
import socket
import Tkinter as tk
import ScrolledText as tkst
import Queue
import math
import sys
import os
import glob
import time
import datetime
import operator
import copy

import subprocess

from vidcapture import *

from configuration import *
from utils import *
from teamcolors import *
MAX_TEAMS = configuration.n   # For color choosing

CURR = u'\xA7'

def log(text, level=0):
  print text
  # write text to file


class TFNetBack(threading.Thread):
  def __init__(self, serverIP, frontend):
    threading.Thread.__init__(self)
    self.frontend = frontend
    self.tkroot = frontend.root
    self.msgnum = 0
    self.sendqueue = Queue.Queue()
    self.serverIP = serverIP

  def run(self):
    self.server_setup(self.serverIP)
    self.event_loop()
  
  def server_setup(self, serverIP):
    conn = None
    while not conn:
      try:
        conn = socket.create_connection( (serverIP, SERVER_PORT) )
      except socket.error:
        print "Connection refused; is server running yet?"
        time.sleep(2.0)
    self.connection = conn
  
  def event_loop(self):
    # Start a loop of waiting for messages
    while True:
      msg = receive_message(self.connection)
      # Should be a 2-tuple of (command, data)
      try:
        command, data = msg
      except TypeError:
        print "Received non-tuple message:", msg
        continue
      self.handle_message(command, data)
      self.msgnum += 1

  def handle_message(self, command, data):
    log("Received command: "+command)
    
    if '<<'+command+'>>' in self.tkroot.bind():
      # Give the data to the frontend
      self.frontend.dataqueue.put( (self.msgnum, command, data) )
      
      # Raise the event to process the message
      # Stupid to use 'x' as the message number, but can't figure out how else to attach data to the event
      self.tkroot.event_generate('<<'+command+'>>', x=self.msgnum, when='tail')
      
      # May need to wait on the result?
      response = self.sendqueue.get()
      if response != 'done':
        send_message(self.connection, response)
    else:
      log("Command has no valid binding")

  def client_setup(self, clientnum):
    self.clientnum = clientnum
    log("I am client "+str(clientnum)+"!")


AVATAR_DIR = './avatars'

#GCHR_start = ord('A')
#GCHR_letters = [chr(GCHR_start+i) for i in range(configuration.n)]
#def gname(gid):     # Convert group ids to strings
  #return GCHR_letters[gid]

## icky hardcoding...
##ACHR_names = ['Agent '+str(i) for i in range(configuration.n)]     # Boring names
#ACHR_names = ['Cat', 'Dog', 'Bear', 'Bird', 'Cow', 'Elephant', 'Fish', 'Frog', 'Gorilla', 'Lion', 'Monkey', 'Bee', 'Owl', 'Panda', 'Penguin', 'Pig', 'Rabbit', 'Rooster', 'Sheep', 'Donkey']    # "Real" names
              
#def aname(aid):
  #return ACHR_names[aid]

## TODO: Fix Tk functions so they don't keep destroying and recreating all the widgets

class TFGui(object):
  def __init__(self, serverIP=None):
    self.dataqueue = Queue.Queue()
    self.myid = 0
    self.myteam = 0
    self.myskill = -1
    self.totalpay = 0   # Total subject pay
    self.ratinglog = []
    self.nteam = 1
    
    self.gletters = [chr(ord('A')+i) for i in range(configuration.n)]
    if configuration._hide_publicgoods:
      self.anames = ['Agent '+str(i) for i in range(configuration.n)]
    else:
      # Icky hardcoding
      self.anames = ['Cat', 'Dog', 'Bear', 'Bird', 'Cow', 'Elephant', 'Fish', 'Frog', 'Gorilla', 'Lion', 'Monkey', 'Bee', 'Owl', 'Panda', 'Penguin', 'Pig', 'Rabbit', 'Rooster', 'Sheep', 'Donkey']
    
    self.initTk()
    if serverIP is not None:
      self.backend = TFNetBack(serverIP, self)
      self.backend.daemon = True
      self.backend.start()
    else:
      # Create a backend, but don't start it
      self.backend = TFNetBack(serverIP, self)

    
  def gname(self, gid):
    return self.gletters[gid]
  
  def aname(self, aid):
    if aid == self.myid:
      return "You"
    return self.anames[aid]

  def run(self):
    self.root.mainloop()
    
  def terminate(self):
    self.root.quit()
    
  def initTk(self):
    self.root = tk.Tk()
    self.root.protocol("WM_DELETE_WINDOW", self.terminate)
    self.root.minsize(1500,900)
    self.root.geometry("1000x800")
    self.root.columnconfigure(0, weight=1)
    self.root.rowconfigure(0, weight=1)
    self.content = tk.Frame(self.root)
    self.content.grid(row=0, column=0)
    
    self.bgdefault = self.root.cget('bg')
    
    self.fontlg = ('Helvetica', 64)
    self.fontmed = ('Helvetica', 32)
    self.fontmid = ('Helvetica', 24)
    self.fontsm = ('Helvetica', 16)
    self.fontxsm = ('Helvetica', 12)
    
    self.widgetrefs = []
    
    self.inithandlers()
    self.initavatars()
    self.checkyes = tk.PhotoImage(file='greencheck16.gif')
    self.xno = tk.PhotoImage(file='redx16.gif')
    self.staron = tk.PhotoImage(file='star_on.gif')
    self.staroff = tk.PhotoImage(file='star_off3.gif')

    self.sidebarwid = 264
    self.sidebarheight = 400
    self.csize = 400            # Canvas size for neighbor view
    
    self.infobutton = None

    self.introscreen = self.make_introscreen()
    self.introsurveyscreen = self.make_introsurveyscreen()
    self.exitsurveyscreen = self.make_exitsurveyscreen()
    #self.exitscreen = self.make_exitscreen()
    self.instructions = self.make_instructions()
    self.mainscreen = self.make_mainscreen()
    self.uscreen = self.make_ultimatum()
    #self.endscreen = self.make_conclusion()
    
    self.publicgoods_instructions = self.make_publicgoods_instructions()
    #self.publicgoodsscreen = self.make_publicgoodsscreen() # not necessary; part of mainscreen
    
    self.activescreen = self.introscreen
    self.show_screen(self.introscreen)
    
    
  def initavatars(self):
    avatars = []
    afiles = sorted(glob.glob(AVATAR_DIR+'/*.gif'))
    for fname in afiles:
      #print fname
      img = tk.PhotoImage(file=fname)
      avatars.append(img)
    self.avatars = avatars
    
    avatars_sm = []
    afiles = sorted(glob.glob(AVATAR_DIR+'_sm/*.gif'))
    for fname in afiles:
      img = tk.PhotoImage(file=fname)
      avatars_sm.append(img)
    self.avatars_sm = avatars_sm
    
  def inithandlers(self):
    self.root.bind('<<intro>>', self.m_intro)
    self.root.bind('<<introsurvey>>', self.m_introsurvey)
    self.root.bind('<<exitsurvey>>', self.m_exitsurvey)
    self.root.bind('<<exit>>', self.m_exit)
    
    self.root.bind('<<setconfig>>', self.m_setconfig)
    
    self.root.bind('<<ultimatum>>', self.m_ultimatum)
    self.root.bind('<<u_instructions>>', self.m_u_instructions)
    self.root.bind('<<u_makeoffer>>', self.m_u_makeoffer)
    self.root.bind('<<u_waitoffer>>', self.m_u_waitoffer)
    self.root.bind('<<u_decideoffer>>', self.m_u_decideoffer)
    self.root.bind('<<u_waitdecide>>', self.m_u_waitdecide)
    self.root.bind('<<u_conclusion>>', self.m_u_conclusion)
    self.root.bind('<<u_review>>', self.m_u_review)
    
    #self.root.bind('<<dictator>>', self.m_dictator)
    #self.root.bind('<<d_instructions>>', self.m_d_instructions)
    self.root.bind('<<d_makeoffer>>', self.m_u_makeoffer)
    self.root.bind('<<d_waitoffer>>', self.m_u_waitoffer)
    #self.root.bind('<<u_decideoffer>>', self.m_u_decideoffer)
    #self.root.bind('<<d_conclusion>>', self.m_d_conclusion)
    
    self.root.bind('<<setmyid>>', self.m_setmyid)
    self.root.bind('<<initvideo>>', self.m_initvideo)
    self.root.bind('<<getframetimes>>', self.m_getframetimes)
    self.root.bind('<<startcapture>>', self.m_startcapture)
    self.root.bind('<<stopcapture>>', self.m_stopcapture)
    self.root.bind('<<endcapture>>', self.m_endcapture)
    self.root.bind('<<startpreview>>', self.m_startpreview)
    self.root.bind('<<endpreview>>', self.m_endpreview)

    self.root.bind('<<instructions>>', self.m_instructions)
    self.root.bind('<<updatepay>>', self.m_updatepay)
    self.root.bind('<<updatenbrs>>', self.m_updatenbrs)
    self.root.bind('<<updatemyteam>>', self.m_updatemyteam)
    self.root.bind('<<updateteam>>', self.m_updateteam)
    self.root.bind('<<propose>>', self.m_propose)
    self.root.bind('<<acceptvote>>', self.m_acceptvote)
    self.root.bind('<<acceptvote_groupmerge>>', self.m_acceptvote_groupmerge)
    self.root.bind('<<consider>>', self.m_consider)
    self.root.bind('<<expelvote>>', self.m_expelvote)
    self.root.bind('<<turndone>>', self.m_turndone)
    self.root.bind('<<postprocess>>', self.m_postprocess)
    self.root.bind('<<addpay>>', self.m_addpay)
    
    self.root.bind('<<publicgoods_instructions>>', self.m_publicgoods_instructions)
    self.root.bind('<<publicgoods>>', self.m_publicgoods)
    self.root.bind('<<publicgoods_conclusion>>', self.m_publicgoods_conclusion)
    
    self.root.bind('<<initratings>>', self.m_initratings)
    self.root.bind('<<getratinglog>>', self.m_getratinglog)
    self.root.bind('<<getratings>>', self.m_getratings)
    self.root.bind('<<showratings>>', self.m_showratings)
    self.root.bind('<<hideratings>>', self.m_hideratings)
    self.root.bind('<<disableratings>>', self.m_disableratings)
    self.root.bind('<<enableratings>>', self.m_enableratings)
    self.root.bind('<<updateratings>>', self.m_updateratings)
    
    self.root.bind('<<conclusion>>', self.m_conclusion)
  
  def destroy_children(self, widget):
    for child in widget.winfo_children():
      child.destroy()
  
  def remove_children(self, widget):
    for child in widget.winfo_children():
      child.grid_remove()
  
  def grid_all(self, widgetdict):
    for widget in widgetdict.values():
      try:
        widget.grid()
      except AttributeError:
        print "Could not grid:", widget
  
  def make_introscreen(self):
    introframe = tk.Frame(self.content)
    intro1 = tk.Label(introframe, text='Welcome to the experiment!', font=self.fontmed)
    intro2 = tk.Label(introframe, text='Please wait for the experiment to start', font=self.fontsm)
    intro1.grid(row=0, column=0)
    intro2.grid(row=1, column=0)
    self.widgetrefs.extend([introframe, intro1, intro2])
    return introframe

  def make_exitscreen(self):
    exitframe = tk.Frame(self.content)
    exit1 = tk.Label(exitframe, text='Thank you!', font=self.fontmed)
    exit2 = tk.Label(exitframe, text='The experiment is over. Thank you for participating!', font=self.fontsm)
    exit3 = tk.Label(exitframe, text='You earned '+CURR+str(round(self.totalpay,2))+'.', font=self.fontsm)
    exit1.grid(row=0, column=0)
    exit2.grid(row=1, column=0)
    exit3.grid(row=2, column=0)
    self.widgetrefs.extend([exitframe, exit1, exit2, exit3])
    return exitframe

  ## Use show_screen(screen)
  
  def make_introsurveyscreen(self):
    sframe = tk.Frame(self.content)
    insdat = self.introsurveydata = {}
    inswid = self.introsurveywidgets = {}
    
    inswid['title'] = tk.Label(sframe, text='Intro Survey', font=self.fontlg)
    inswid['title'].grid(row=0, column=0)
    
    # Gender
    inswid['genderlab'] = tk.Label(sframe, text='Gender', font=self.fontmid)
    inswid['genderlab'].grid(row=1, column=0)
    
    insdat['gender'] = tk.StringVar()
    insdat['gender'].set('P')
    inswid['genderM'] = tk.Radiobutton(sframe, text='Male', variable=insdat['gender'], value='M', font=self.fontsm)
    inswid['genderF'] = tk.Radiobutton(sframe, text='Female', variable=insdat['gender'], value='F', font=self.fontsm)
    inswid['genderT'] = tk.Radiobutton(sframe, text='Transgender', variable=insdat['gender'], value='T', font=self.fontsm)
    inswid['genderP'] = tk.Radiobutton(sframe, text='Prefer not to answer', variable=insdat['gender'], value='P', font=self.fontsm)
    
    inswid['genderM'].grid(row=2, column=0, sticky='w')
    inswid['genderF'].grid(row=3, column=0, sticky='w')
    inswid['genderT'].grid(row=4, column=0, sticky='w')
    inswid['genderP'].grid(row=5, column=0, sticky='w')
    row = 6
    
    #College
    inswid['collegelab'] = tk.Label(sframe, text='College', font=self.fontmid)
    inswid['collegelab'].grid(row=row, column=0); row+=1
    
    insdat['college'] = tk.StringVar()
    insdat['college'].set('Other')
    colleges = ['Science', 'Engineering', 'Medical', 'Humanities', 'Business', 'Education', 'Other']
    for i,c in enumerate(colleges):
      inswid['college'+c] = tk.Radiobutton(sframe, text=c, variable=insdat['college'], value=c, font=self.fontsm)
      inswid['college'+c].grid(row=row+i, column=0, sticky='w')
    row = row+i+1
    
    # Status
    inswid['genderlab'] = tk.Label(sframe, text='Status', font=self.fontmid)
    inswid['genderlab'].grid(row=row, column=0); row+=1
    
    insdat['status'] = tk.StringVar()
    insdat['status'].set('Other')
    statuses = ['Undergraduate','Graduate','Other']
    for i,s in enumerate(statuses):
      insdat['status'+s] = tk.Radiobutton(sframe, text=s, variable=insdat['status'], value=s, font=self.fontsm)
      insdat['status'+s].grid(row=row+i, column=0, sticky='w')
    row = row+i+1
    
    inswid['submit'] = tk.Button(sframe, text='Submit', font=self.fontmed, command=self.submit_introsurvey)
    inswid['submit'].grid(row=20, column=0)
    
    return sframe
  
  def focus_next_window(event):
    event.widget.tk_focusNext().focus()
    return("break")
  
  def make_exitsurveyscreen(self):
    sframe = tk.Frame(self.content)
    exdat = self.exitsurveydata = {}
    exwid = self.exitsurveywidgets = {}
    
    questions = [
      "How did you decide which teams to apply to?",
      "How did you decide which applications to accept?",
      "How did you decide whether to join another team or not?",
      "Were some of the participants nicer than others, or did everyone behave about the same?",
      "If you noticed any differences, which participants were the nicest? Which were not?",
      "Was anything confusing to you about the experiment?",
      "Do you have any other feedback on the experiment?\n(Things you liked, didn't like, found helpful, thought were weird, etc.)"
    ]
    
    exwid['title'] = tk.Label(sframe, text='Exit Survey', font=self.fontmed)
    exwid['title'].grid(row=0,column=0)
    
    offs = 3
    #exwid['qtexts'] = {}
    exwid['qtexts'] = []
    for i,qtext in enumerate(questions):
      qlab = tk.Label(sframe, text=qtext, font=self.fontxsm, justify=tk.LEFT)
      qwid = tkst.ScrolledText(sframe, height=2, width=64, font=self.fontxsm)
      # exwid['qtexts'].append(qwid)
      qlab.grid(row=offs+i*2, column=0, sticky='w')
      qwid.grid(row=offs+i*2+1, column=0)
      #exwid['qtexts'][qtext] = qwid
      exwid['qtexts'].append( (qtext, qwid) )

    exwid['submit'] = tk.Button(sframe, text='Submit', font=self.fontmed, command=self.submit_exitsurvey)
    exwid['submit'].grid(row=len(questions)*2+offs+2, column=0)
    
    self.root.bind_class("Text", "<Tab>", self.focus_next_window)
    
    

    return sframe
  
  def m_setconfig(self, event):
    self.cfgdict = self.getdata(event)
    self.backend.sendqueue.put('send_done')
  
  def m_initratings(self, event):
    neighbors = self.getdata(event)
    self.make_ratings_sidebar(neighbors)
    self.backend.sendqueue.put('done')
  
  def m_introsurvey(self, event):
    self.getdata(event)
    self.show_screen(self.introsurveyscreen)
    self.setState(self.introsurveywidgets['submit'], tk.NORMAL)

  def m_exitsurvey(self, event):
    self.getdata(event)
    self.show_screen(self.exitsurveyscreen)
    self.setState(self.exitsurveywidgets['submit'], tk.NORMAL)
  
  def submit_introsurvey(self):
    inswid = self.introsurveywidgets
    insdat = self.introsurveydata
    
    # disable button 
    self.setState(inswid['submit'], tk.DISABLED)
    inswid['submit'].config(text='Waiting...')
    
    introdata = (insdat['gender'].get(), insdat['college'].get(), insdat['status'].get())
    self.backend.sendqueue.put(introdata)
    
    #self.backend.sendqueue.put('done') ## TEMP DEBUG
    
  def submit_exitsurvey(self):
    
    # We might have a lot of text to submit here; larger than the buffer size. 
    # May need to send piece-by-piece: send num of qs and then send each answer
    # But this might require hacking the backend.
    exwid = self.exitsurveywidgets
    
    # disable button
    self.setState(exwid['submit'], tk.DISABLED)
    
    # Hijack the backend's connection
    conn = self.backend.connection
    
    # Send number of questions
    n_qs = len(exwid['qtexts'])
    send_message(conn, n_qs)
    
    # Send each question 
    for qtext, qwid in exwid['qtexts']:#.iteritems():
      response = qwid.get(1.0, tk.END)
      rlen = BUFFER_SIZE - len(qtext) - 10
      shortresp = response[:rlen]
      send_message(conn, (qtext, shortresp) )
    
    # Unlock the message backend so we can continue processing messages
    #self.backend.sendqueue.put('done')
    
    # Send the final pay back to the server
    self.backend.sendqueue.put(self.totalpay)
    
    #self.show_screen(self.exitscreen)
    self.ratingbox.grid_remove()
    self.show_screen(self.make_conclusion())


  def m_ultimatum(self, event):
    self.getdata(event)
    #self.make_ultimatum()
    
    # Switch to generic ultimatum screen
    
    print "Done with m_ultimatum"
    self.backend.sendqueue.put('done')
    
  def m_u_instructions(self, event):
    self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_instructions()
    
  def m_u_makeoffer(self, event):
    other_player = self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_makeoffer(other_player)
    self.markstart()
    
  def m_u_waitoffer(self, event):
    other_player = self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_waitoffer(other_player, is_offer=True)
    self.backend.sendqueue.put('done')
    #self.markstart()
    
  def m_u_waitdecide(self, event):
    other_player = self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_waitoffer(other_player, is_offer=False)
    self.backend.sendqueue.put('done')
    #self.markstart()
    
  def m_u_decideoffer(self, event):
    other_player, amount = self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_decideoffer(other_player, amount)
    self.markstart()
    
  def m_u_conclusion(self, event):
    other_player, amount, result, role = self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_conclusion(other_player, amount, result, role)
    self.markstart()
    
  def m_u_review(self, event):
    self.getdata(event)
    self.show_screen(self.uscreen)
    self.u_review()

  def make_ultimatum(self):
    uframe = tk.Frame(self.content)
    self.uwidgets = {}
    uw = self.uwidgets
    #uw['content'] = uframe
    #uw['content'].grid()
    
    uw['title'] = tk.Label(uframe, text='Ultimatum!', font=self.fontlg, relief=tk.GROOVE, borderwidth=2)
    uw['history'] = tk.Frame(uframe, relief=tk.SUNKEN, borderwidth=2, width=200)
    uw['histlab'] = tk.Label(uw['history'], text='History', font=self.fontsm, relief=tk.GROOVE, borderwidth=2)
    uw['contentspacer'] = tk.Frame(uframe)
    uw['content'] = tk.Frame(uw['contentspacer'], height=400, width=650)
    uw['infobar'] = tk.Frame(uframe, relief=tk.GROOVE, borderwidth=2, height=100)

    uw['submit'] = None
    
    uw['title'].grid(row=0, column=0, columnspan=2, sticky='nsew')
    uw['history'].grid(row=1, column=0, sticky='nsew')
    uw['histlab'].grid(row=0, column=0, sticky='ew')
    uw['contentspacer'].grid(row=1,column=1)
    uw['infobar'].grid(row=2, column=0, columnspan=2, sticky='nsew')
    
    uw['content'].grid(row=1, column=1)
    uw['contentspacer'].grid_columnconfigure(0, weight=1)
    uw['contentspacer'].grid_columnconfigure(2, weight=1)
    #uw['contentspacer'].grid_rowconfigure(0, weight=1)
    uw['contentspacer'].grid_rowconfigure(0, minsize=12)
    uw['contentspacer'].grid_rowconfigure(2, weight=1)
    
    uframe.grid_rowconfigure(1, minsize=400)
    uframe.grid_columnconfigure(0, minsize=200)
    uframe.grid_columnconfigure(1, minsize=650, weight=1)
    
    uw['history'].grid_columnconfigure(0, minsize=200)
    
    uw['nhistory'] = 0
    uw['playerhistory'] = {}
    
    return uframe
    
  def u_instructions(self):
    # Give instructions on how to play
    uw = self.uwidgets
    
    self.hideratings()
    
    content = uw['content']
    #self.destroy_children(content)
    #self.remove_children(content)
    
    #uw['content'].grid_remove()
    
    uw['testy'] = tk.Label(uw['content'], text='test')
    uw['testy'].grid()
    
    uw['content'].grid()
    
    #uw['iplab'] = tk.Label(content, text='Playing with', font=self.fontmed)
    #uw['iavatar'] = tk.Label(content, image=self.avatars[0])
    if 'itext' not in uw:
      uw['itext'] = tk.Label(content, text="In this game, you and another player decide how to split "+CURR+"10.\nPlayer 1 will make an offer about how to split the money.\nPlayer 2 will accept or reject the offer.\nIf Player 2 accepts the offer, the money is split accordingly.\nIf Player 2 rejects the offer, neither player receives anything.\nYou will take turns being Player 1 or Player 2 with the other participants.", font=self.fontsm, justify=tk.LEFT)#, wraplength=600)
      uw['itext'].grid(row=0, column=0)
      uw['iok'] = tk.Button(content, text='OK', command=self.u_instructions_done, font=self.fontmed)
      uw['iok'].grid(row=1, column=0)
    else:
      self.setState(self.uwidgets['iok'], tk.NORMAL)
      uw['itext'].grid()
      uw['iok'].grid()
    
    
  def u_instructions_done(self):
    self.setState(self.uwidgets['iok'], tk.DISABLED)
    self.showratings()
    self.show_screen(self.introscreen)
    self.backend.sendqueue.put('done')
    
  def u_playingwith(self, other_player):
    uw = self.uwidgets
    infobar = uw['infobar']
    self.remove_children(infobar)
    
    ptext = 'Playing with '+self.aname(other_player)
    
    if 'playingwith' not in uw:
      pw = uw['playingwith'] = {}
      pw['lab'] = tk.Label(infobar, text=ptext, font=self.fontmid)
      pw['avatar'] = tk.Label(infobar, image=self.avatars[other_player])
      pw['lab'].grid(row=0, column=0)
      pw['avatar'].grid(row=0, column=1)
      
      pw['buffer'] = tk.Frame(infobar)
      pw['buffer'].grid(row=0, column=2, sticky='ew')
      
      infobar.grid_columnconfigure(2, weight=1)     # Make buffer expand between "playing with" and paybox
      
      pb = pw['paybox'] = tk.Frame(infobar, relief=tk.GROOVE, borderwidth=2)
      
      pw['paylab'] = tk.Label(pb, text="You've earned", font=self.fontxsm)
      pw['payamt'] = tk.Label(pb, text=CURR+str(self.totalpay), font=self.fontmid)
      pw['paylab'].grid(row=0,column=0,sticky='ew')
      pw['payamt'].grid(row=1,column=0,sticky='nsew')
      pb.grid(row=0, column=3, sticky=tk.E, ipadx=3, ipady=3)
      
    else:
      pw = uw['playingwith']
      pw['lab'].config(text=ptext)
      pw['avatar'].config(image=self.avatars[other_player])
      pw['payamt'].config(text=CURR+str(self.totalpay))
      self.grid_all(pw)
    
  def u_makeoffer(self, other_player):
    # Make an offer
    uw=self.uwidgets
    #if 'makeoffer' in uw:  uw['makeoffer'].destroy()
    
    content = uw['content']
    #infobar = uw['infobar']
    self.remove_children(content)
    #self.remove_children(infobar)

    self.u_playingwith(other_player)
    
    offertext = 'Make an offer to '+self.aname(other_player)
    resulttext = 'You get '+CURR+'10 and the other player gets '+CURR+'0'  #don't use real name
    
    if 'makeoffer_widgets' not in uw:
      mow = uw['makeoffer_widgets'] = {}
      
      uw['offervar'] = tk.IntVar()
      
      mow['motext1'] = tk.Label(content, text=offertext, font=self.fontmed)
      mow['moavatar'] = tk.Label(content, image=self.avatars[other_player])
      mow['mospin'] = tk.Spinbox(content, from_=0, to=10, font=self.fontlg, width=3, textvariable=uw['offervar'])
      mow['mook'] = tk.Button(content, text='OK', command=self.u_sendoffer, font=self.fontmed)
      mow['moresult'] = tk.Label(content, text=resulttext, font=self.fontsm)
      mow['motext1'].grid(column=0, row=0)#, columnspan=2)
      mow['moavatar'].grid(column=1, row=0, sticky='W')
      mow['mospin'].grid(column=0, row=1)
      mow['mook'].grid(column=1, row=1)
      mow['moresult'].grid(column=0, row=2, columnspan=2)
      # Set up a callback so update_result is called whenever mospin changes
      uw['offervar'].trace(mode='w', callback = self.update_result)
      
    else:
      mow = uw['makeoffer_widgets']
      mow['motext1'].config(text=offertext)
      mow['moavatar'].config(image=self.avatars[other_player])
      mow['moresult'].config(text=resulttext)
      #mow['moresult'].config(text='You get '+CURR+'10 and the other player gets '+CURR+'0')
      
      uw['offervar'].set(0)
      
      self.setState(mow['mook'], tk.NORMAL)
      
      self.grid_all(mow)

  def update_result(self, varname, elementname, mode):
    # Update the label to say how much $ each player gets
    amount = int(self.uwidgets['makeoffer_widgets']['mospin'].get())
    self.uwidgets['makeoffer_widgets']['moresult'].config(text='You get '+CURR+str(10-amount)+' and the other player gets '+CURR+str(amount))
        
    
  def u_sendoffer(self):
    self.markend()
    self.backend.sendqueue.put(self.uwidgets['offervar'].get())
    
  def u_waitoffer(self, other_player, is_offer=True):
    # Waiting for offer from player 1
    uw=self.uwidgets
    
    content = uw['content']
    self.remove_children(content)

    self.u_playingwith(other_player)
    
    event_type = 'an offer' if is_offer else 'a decision'
    waittext = 'Waiting for '+event_type+' from '+self.aname(other_player)
    
    if 'waitoffer_widgets' not in uw:
      wow = uw['waitoffer_widgets'] = {}
      wow['wotext1'] = tk.Label(content, text=waittext, font=self.fontmid)
      wow['woavatar'] = tk.Label(content, image=self.avatars[other_player])
      wow['wotext1'].grid(row=0, column=0)
      wow['woavatar'].grid(row=0, column=1, sticky='W')
      
    else:
      wow = uw['waitoffer_widgets']
      wow['wotext1'].config(text=waittext)
      wow['woavatar'].config(image=self.avatars[other_player])
      
      self.grid_all(wow)

    self.markstart()
    
    
  def u_decideoffer(self, other_player, amount):
    # Decide accept/reject
    uw=self.uwidgets
    
    content = uw['content']
    self.remove_children(content)

    self.u_playingwith(other_player)

    offertext = self.aname(other_player)+' offers you '+CURR+str(amount)
    notext = 'You get '+CURR+'0 and '+self.aname(other_player)+' gets '+CURR+'0'
    yestext = 'You get '+CURR+str(amount)+' and '+self.aname(other_player)+' gets '+CURR+str(10-amount)

    if 'decideoffer_widgets' not in uw:
      dow = uw['decideoffer_widgets'] = {}
      dow['dtext1'] = tk.Label(content, text='Decide on offer', font=self.fontmed)
      dow['dtext2'] = tk.Label(content, text=offertext, font=self.fontmed)
      dow['avatar'] = tk.Label(content, image=self.avatars[other_player])
      dow['nobutton'] = tk.Button(content, text='REJECT', command=self.u_nooffer, font=self.fontmed)
      dow['yesbutton'] = tk.Button(content, text='ACCEPT', command=self.u_yesoffer, font=self.fontmed)
      dow['nolab'] = tk.Label(content, text=notext, font=self.fontsm, wraplength=360)
      dow['yeslab'] = tk.Label(content, text=yestext, font=self.fontsm, wraplength=360)
      
      dow['dtext1'].grid(column=0, row=0, columnspan=4)
      dow['avatar'].grid(column=0, row=1, sticky=tk.E)
      dow['dtext2'].grid(column=1, row=1, columnspan=3)
      dow['nobutton'].grid(column=0, row=2, columnspan=2, pady=20)
      dow['yesbutton'].grid(column=2, row=2, columnspan=2, pady=20)
      dow['nolab'].grid(column=0, row=3, columnspan=2, ipadx=20)
      dow['yeslab'].grid(column=2, row=3, columnspan=2, ipadx=20)
      
    else:
      dow = uw['decideoffer_widgets']
      
      dow['dtext2'].config(text=offertext)
      dow['avatar'].config(image=self.avatars[other_player])
      dow['nolab'].config(text=notext)
      dow['yeslab'].config(text=yestext)
      
      self.grid_all(dow)
    
  def u_yesoffer(self):
    self.markend()
    self.backend.sendqueue.put(True)
    
  def u_nooffer(self):
    self.markend()
    self.backend.sendqueue.put(False)
    
  def u_conclusion(self, other_player, amount, result, role):
    # Summarize what happened
    uw=self.uwidgets
    
    content = uw['content']
    self.remove_children(content)
    
    if result:
      if role == 0:
        my_amount, their_amount = 10-amount, amount
      else:
        my_amount, their_amount = amount, 10-amount
    else:
      my_amount = their_amount = 0
    
    decision_strings = ['rejected', 'accepted']
    
    if role == 0:
      dtext = self.aname(other_player)+' '+decision_strings[result]+' your offer for '+CURR+str(amount)
    elif role == 1:
      dtext = 'You '+decision_strings[result]+' '+self.aname(other_player)+'\'s offer for '+CURR+str(amount)
    
    paytext = 'You receive '+CURR+str(my_amount)+'. '+self.aname(other_player)+' receives '+CURR+str(their_amount)+'.'
    
    self.totalpay += my_amount
    
    # Do this down here because it updates the pay label
    self.u_playingwith(other_player)

    if 'conclusion_widgets' not in uw:
      cw = uw['conclusion_widgets'] = {}
      cw['ctext1'] = tk.Label(content, text='Round Done', font=self.fontmed)
      cw['dlab'] = tk.Label(content, text=dtext, font=self.fontmid)
      cw['plab'] = tk.Label(content, text=paytext, font=self.fontmid)
      cw['ok'] = tk.Button(content, text='OK', command=self.u_conclusion_done, font=self.fontmed)

      cw['ctext1'].grid(column=0,row=0)
      cw['dlab'].grid(column=0,row=3)
      cw['plab'].grid(column=0,row=4)
      cw['ok'].grid(column=0,row=5)
      
    else:
      cw = uw['conclusion_widgets']
      cw['dlab'].config(text=dtext)
      cw['plab'].config(text=paytext)
      
      self.setState(cw['ok'], tk.NORMAL)
      cw['ok'].config(text='OK')
      
      self.grid_all(cw)
    
    self.add_history(other_player, amount, result, role)
  
  def u_conclusion_done(self):
    self.markend()
    self.setState(self.uwidgets['conclusion_widgets']['ok'], tk.DISABLED)
    self.uwidgets['conclusion_widgets']['ok'].config(text='Waiting...')
    self.backend.sendqueue.put('send_done')
  
  
  def add_history(self, other_player, amount, result, role):
    uw = self.uwidgets
    # uw['playerhistory'][other_player] = {}
    #   avatar, label of "Player X"
    #   sent: history
    #   received: history
    #   history is top row your action, bottom row theirs
    if other_player not in uw['playerhistory']:
      # add necessary frame etc.
      pw = uw['playerhistory'][other_player] = {}
      pw['pframe'] = tk.Frame(uw['history'], relief=tk.GROOVE, borderwidth=2)
      pw['labframe'] = tk.Frame(pw['pframe'])
      pw['histframe'] = tk.Frame(pw['pframe'])
      pw['avatar'] = tk.Label(pw['labframe'], image=self.avatars_sm[other_player])
      pw['label'] = tk.Label(pw['labframe'], text=self.aname(other_player), font=self.fontsm)
      pw['avatar'].grid(row=0, column=0, sticky='w')
      pw['label'].grid(row=0, column=1, sticky='w')
      
      pw['labframe'].grid(row=0, column=0, sticky='w')
      pw['histframe'].grid(row=1, column=0, sticky='w')
      pw['pframe'].grid(row=len(uw['playerhistory']), column=0, sticky='ew')
      
      pw['youlab'] = tk.Label(pw['histframe'], text='You:')
      pw['themlab'] = tk.Label(pw['histframe'], text='They:')
      pw['youlab'].grid(row=0,column=0)
      pw['themlab'].grid(row=1,column=0)
      
      pw['nhist'] = 1
    else:
      pw = uw['playerhistory'][other_player]
      
    resulticons = [self.xno, self.checkyes]
    
    sendlab = tk.Label(pw['histframe'], text=amount)
    reslab = tk.Label(pw['histframe'], image=resulticons[result])
    
    sendlab.grid(row=role, column=pw['nhist'])
    reslab.grid(row=(1-role), column=pw['nhist'])
                 
    pw['nhist'] += 1
    
  def u_review(self):
    uw = self.uwidgets
    content = uw['content']
    self.remove_children(content)
    
    if 'review_widgets' not in uw:
      rw = uw['review_widgets'] = {}
      rw['lab1'] = tk.Label(content, text='Ultimatum Done', font=self.fontmed)
      rw['lab2'] = tk.Label(content, text='Please press Done when you are ready to go\nto the next phase of the experiment', font=self.fontmid)
      rw['Done'] = tk.Button(content, text='Done', command=self.u_review_done, font=self.fontmed)
      
      rw['lab1'].grid(row=0, column=0)
      rw['lab2'].grid(row=1, column=0)
      rw['Done'].grid(row=2, column=0)
    else:
      rw = uw['review_widgets']
      self.grid_all(rw)
    
  def u_review_done(self):
    self.setState(self.uwidgets['review_widgets']['Done'], tk.DISABLED)
    self.uwidgets['review_widgets']['Done'].config(text='Please Wait')
    #time.sleep(5)
    #self.show_screen(self.introscreen)
    self.backend.sendqueue.put('done')
    
  #def ultimatum_switch(self, screen, unblock=False):
    #if self.uwidgets['active']:
      #self.uwidgets['active'].grid_remove()
    #self.uwidgets[screen].grid()
    #self.uwidgets['active'] = self.uwidgets[screen]
    #if unblock:
      #self.backend.sendqueue.put('done')
    

  
  
  
  
  def update_instruction_text(self):
    longtext = "In this game, you will try to form a team with the other players. Your payoff will depend on which players you have on your team. The payoff your current team will receive is always shown in the upper-right corner of the screen.\n\nThis game has "+('4' if self.cfgdict['expel_agents'] else '3') +" stages:\n1. Apply: you can apply to join any neighboring teams. The amount you will earn on each team is shown.\n2. Accept: your team will receive applications from neighboring players. You can vote on which you would like to accept (if any) to join your team. The amount of money your team will make if each of the other players joins is shown.\n3. Join: if you receive any acceptances from other teams, you may choose which team to join.\n"
    if self.cfgdict['expel_agents']:
      longtext += "4. Expel: in some games, you may vote for a player to be expelled from your team.\n"
    longtext += "\nThe game will continue until no one changes teams for a round, or until "+str(self.cfgdict['nsteps'])+" rounds have passed.\nThese instructions will be repeated throughout the game for reference. Have fun!\n"
    
    self.instruction_text.config(text=longtext)
    
  
  def make_instructions(self):
    instrframe = tk.Frame(self.content)
    instr1 = tk.Label(instrframe, text='Team formation game', font=self.fontmed)
    longtext = 'These are the instructions' # Placeholder
    instr2 = tk.Label(instrframe, text=longtext, font=self.fontsm, wraplength=800, justify=tk.LEFT)
    self.instruction_text = instr2
    if not self.infobutton:
      self.infobutton = tk.Button(instrframe, text='OK', font=self.fontmed, command=self.submit_information_blocking)
    self.infobutton.grid(row=2, column=0)
    instr1.grid(row=0, column=0)
    instr2.grid(row=1, column=0)
    self.widgetrefs.extend([instrframe, instr1, instr2])
    return instrframe
    
  def make_conclusion(self):
    cframe = tk.Frame(self.content)
    c1 = tk.Label(cframe, text='The experiment is done!', font=self.fontmed)
    c2 = tk.Label(cframe, text='You earned '+CURR+str(round(self.totalpay,2))+'.', font=self.fontsm)
    exrate = self.cfgdict['exchange_rate']
    c3 = tk.Label(cframe, text=u'At the exchange rate of {}{:.2f}/$1, this converts to ${:.2f}.'.format(CURR, exrate, self.totalpay/exrate), font=self.fontsm)
    
    #self.infobutton = tk.Button(cframe, text='OK', font=self.fontmed, command=self.submit_information)
    c1.grid(row=0, column=0)
    c2.grid(row=1, column=0)
    c3.grid(row=2, column=0)
    #self.infobutton.grid(row=2, column=0)
    self.widgetrefs.extend([cframe, c1, c2, c3])
    return cframe
    
  def update_pubgoods_instruction_text(self):
    titletext = 'Teamwork stage' if not self.cfgdict['_hide_publicgoods'] else 'Bonus stage'
    self.pubgoods_title_text.config(text=titletext)
    
    if not self.cfgdict['_hide_publicgoods']:
      longtext = "Now, you can work together as a team to earn additional pay. Each team member may contribute as much of their potential pay as they like to a shared pot. The pot will be increased by "+str(self.cfgdict['pubgoods_mult'])+"% and split evenly among everyone on your team. Each team member's contribution will be shown publicly to the other members of the team.\n"
    else:
      longtext = "Your team has been entered into a lottery. You may contribute as much of your pay as you would like to the lottery. The amount you contribute determines the amount you are eligible to win."
    
    self.pubgoods_instruction_text.config(text=longtext)
    
  def make_publicgoods_instructions(self):
    instrframe = tk.Frame(self.content)
    titletext = 'Next Stage'    # Placeholder
    instr1 = tk.Label(instrframe, text=titletext, font=self.fontmed)
    self.pubgoods_title_text = instr1
    
    #longtext = "Now, you can work together as a team to earn additional pay. Each team member may contribute as much of their potential pay as they like to a shared pot. The pot will be increased by "+str(int((self.cfgdict['pubgoods_mult']-1)*100))+"% and split evenly among everyone on your team.\n"
    
    longtext = 'These are the instructions for public goods'    # Placeholder
    instr2 = tk.Label(instrframe, text=longtext, font=self.fontsm, wraplength=800, justify=tk.LEFT)
    self.pubgoods_instruction_text = instr2
    
    if not self.infobutton:
      self.infobutton = tk.Button(instrframe, text='OK', font=self.fontmed, command=self.submit_information_blocking)
    self.infobutton.grid(row=2, column=0)
    instr1.grid(row=0, column=0)
    instr2.grid(row=1, column=0)
    self.widgetrefs.extend([instrframe, instr1, instr2])
    return instrframe
    
  def make_mainscreen(self):
    mainframe = tk.Frame(self.content)
    mainframe.grid_columnconfigure(1, minsize=self.sidebarwid)  # keep the sidebar size constant
    mainframe.grid_rowconfigure(1, minsize=self.sidebarheight)
    mainframe.grid_rowconfigure(2, minsize=150) # keep the instructions row from changing sizes
    
    mw = self.mwidgets = {}
    mw['title'] = tk.Label(mainframe, text='TITLE', font=self.fontlg, relief=tk.GROOVE, borderwidth=2)
    mw['neighbors'] = tk.Frame(mainframe, height=400, width=400)
    mw['paybox'] = tk.Frame(mainframe, relief=tk.GROOVE, borderwidth=2)
    paybox = mw['paybox']
    mw['paylab'] = tk.Label(paybox, text='Currently earning:', font=self.fontmid)
    mw['nowpay'] = tk.Label(paybox, text=CURR+'0', justify=tk.RIGHT, font=self.fontmed)
    mw['sidebar'] = tk.Frame(mainframe, relief=tk.SUNKEN, borderwidth=2, width=self.sidebarwid)
    
    infobar = mw['infobar'] = tk.Frame(mainframe, relief=tk.GROOVE, borderwidth=2, height=100)
    
    mw['instructions'] = tk.Label(infobar, text='Instructions here', font=self.fontsm, justify=tk.LEFT)
    mw['instructions'].grid(row=0, column=0, sticky='ew')
    
    mw['buffer'] = tk.Frame(infobar)
    mw['buffer'].grid(row=0, column=1, sticky='ew')
      
    infobar.grid_columnconfigure(1, weight=1)   # weight the buffer to make it expand between instr and pay
      
    #eb = mw['earnbox'] = tk.Frame(infobar, relief=tk.GROOVE, borderwidth=2)
    eb = mw['earnbox'] = tk.Frame(mainframe, relief=tk.GROOVE, borderwidth=2)
    mw['earnlab'] = tk.Label(eb, text="You've earned", font=self.fontxsm)
    mw['earnamt'] = tk.Label(eb, text=CURR+str(self.totalpay), font=self.fontmid)
    mw['earnlab'].grid(row=0,column=0,sticky='ew')
    mw['earnamt'].grid(row=1,column=0,sticky='nsew')
    #eb.grid(row=0, column=2, sticky=tk.E, ipadx=3, ipady=3)
    eb.grid(row=2, column=2, sticky='news', ipadx=3, ipady=3)
    
    mw['title'].grid(row=0, column=0, sticky='nsew')
    mw['paybox'].grid(row=0, column=1, sticky='nsew')
    mw['paylab'].grid(row=0, column=0, sticky='ew')
    mw['nowpay'].grid(row=1, column=0, sticky='ew')
    mw['neighbors'].grid(row=1, column=0)
    mw['sidebar'].grid(row=1, column=1, sticky='nsew')
    mw['infobar'].grid(row=2, column=0, columnspan=2, sticky='news')
    
    self.sb = None
    self.teamview = None
    
    self.make_neighborview()
    
    return mainframe
    
  def update_sidebar_size(self):
    mw = self.mwidgets
    # For complete graphs, remove the neighbor view entirely
    if self.cfgdict['graph_type'] == 'complete_graph':
      mw['neighbors'].grid_remove()
      mw['sidebar'].grid(row=1,column=0, sticky='nsew', columnspan=2)
      mw['sidebar'].config(height=self.csize)
    else:
      mw['neighbors'].grid(row=1, column=0)
      mw['sidebar'].grid(row=1, column=1)
    
  def make_sidebar(self, gdata, chooseone=False):
    if self.sb is not None:
      self.sb.destroy()
    
    # Controls number of rows before we start a new column in the list of groups
    MAX_GROUP_ROWS = 6
    
    # Controls rows of avatar icons within the group button
    maxgsize = max(len(g[3]) for g in gdata)
    ROW_MAX_ICONS = 3 if maxgsize <= 6 else 4
    
    sb = tk.Frame(self.mwidgets['sidebar'],width=self.sidebarwid)
    sb.grid(row=0, column=0, sticky='ew')
    self.opts = []
    opts = self.opts
    
    self.choice = tk.IntVar()
    self.choice.set(-1)
    self.choices = {}
    sb.grid_columnconfigure(0, weight=1)
    sb.grid_columnconfigure(1, weight=1)
    
    grow = 0; gcol = 0  # row and column of the current group button
    def nextspot(r, c):
      r += 1
      if r >= MAX_GROUP_ROWS:
        r = 0; c += 2
      return r, c
    
    for i,(gid, gsize, pay, gmembers) in enumerate(gdata):
      #gframe = tk.Frame(sb, relief=tk.GROOVE, borderwidth=2)
      if gsize == 0:
        continue
      
      #gframe = tk.Frame(sb) #, relief=tk.GROOVE, borderwidth=2)
      
      ### Create the label(s), checkbox/radio button
      #tk.Label(gframe, text='Team '+self.gname(gid)+' ('+str(gsize)+' members)', font=self.fontsm).grid(row=0)
      grouptext = 'Team '+self.gname(gid)
      if not self.cfgdict['_show_other_team_members']:
        grouptext += ' ('+str(gsize)+' member'+('s' if gsize != 1 else '')+')'
      grouptext += '\nEarn: '+CURR+str(round(pay,2))
      
      if chooseone:
        gbutton = tk.Radiobutton(sb, text=grouptext, font=self.fontsm, variable=self.choice, value=gid, indicatoron=0, 
                      activebackground=self.colors[gid], background=self.colors[gid])
        #tk.Radiobutton(gframe, text='Pay: $'+str(pay), font=self.fontsm, variable=self.choice, value=gid).grid(row=1)  #indicatoron=0
      else:
        chosen = tk.BooleanVar()
        gbutton = tk.Checkbutton(sb, text=grouptext, font=self.fontsm, variable=chosen, 
                      activebackground=self.colors[gid], background=self.colors[gid], borderwidth=0)
        self.choices[gid] = chosen
        
      #gbutton.grid(row=0, column=0, sticky='ew')
      #gbutton.grid(row=i, column=0, sticky='ew')  
      gbutton.grid(row=grow, column=gcol, sticky='ew')  
      
      if self.cfgdict['_show_other_team_members']:    # Add view of other team members
        #tframe = tk.Frame(gframe, background=self.colors[gid])
        tframe = tk.Frame(sb, background=self.colors[gid])
        tr = 0; tc = 0
        for aid in gmembers:
          tk.Label(tframe, image=self.avatars_sm[aid], background=self.colors[gid]).grid(row=tr,column=tc)
          tc += 1
          if tc >= ROW_MAX_ICONS:
            tc = 0; tr += 1
        #tframe.grid(row=0, column=1, sticky='nsew', ipadx=5)
        #tframe.grid(row=i, column=1, sticky='nsew', ipadx=5)
        tframe.grid(row=grow, column=gcol+1, sticky='nsew', ipadx=5)
      
      #gframe.grid(row=i, column=0, sticky='ew')
      sb.grid_rowconfigure(grow, weight=1)
      
      grow, gcol = nextspot(grow, gcol)
      
    if chooseone:
      #grow, gcol = nextspot(grow, gcol)
      #gframe = tk.Frame(sb, relief=tk.GROOVE, borderwidth=2)
      #gframe.grid(row=i, column=0, sticky='ew')
      tk.Radiobutton(sb, text='Stay with Team '+self.gname(self.myteam)+'\nEarn: '+self.mwidgets['nowpay']['text'], font=self.fontsm, variable=self.choice, value=-1, indicatoron=0).grid(row=grow, column=gcol, sticky='ew', columnspan=2)
      grow, gcol = nextspot(grow, gcol)
      self.submit = tk.Button(sb, text='Submit', font=self.fontmid, command=self.submit_accept)
    else:
      self.submit = tk.Button(sb, text='Submit', font=self.fontmid, command=self.submit_propose)
    
    self.submit.grid(row=grow, column=gcol, sticky='ew', columnspan=2)
    
    self.sb = sb
    
  ###TODO: make_sidebar_agent for voting on agents to accept
  ###It is dumb to have copied the make_sidebar code, but it would change several things to adapit it.
  def make_sidebar_agent(self, adata, groupmerge=False, expelstep=False):
    if self.sb is not None:
      self.sb.destroy()
    
    # if groupmerge:
    #   adata, gdata = adata
    
    sb = tk.Frame(self.mwidgets['sidebar'],width=self.sidebarwid)
    sb.grid(row=0, column=0, sticky='ew')
    self.opts = []
    opts = self.opts
    
    self.choice = tk.IntVar()
    self.choice.set(-1)
    r = 0
    c = 0
    MAXROWS = 5
    
    def nextspot(r,c):
      r += 1
      if r >= MAXROWS:
        r = 0; c += 1
      return r, c
    
    for i,(aid, pay) in enumerate(adata):
      aframe = tk.Frame(sb, relief=tk.GROOVE, borderwidth=2)
      
      ### Create the label(s), checkbox/radio button
      alab = tk.Label(aframe, image=self.avatars_sm[aid])
      abtn = tk.Radiobutton(aframe, text=self.aname(aid)+'\nEarn: '+CURR+str(round(pay,2)), font=self.fontsm, variable=self.choice, value=aid, indicatoron=0)
      alab.grid(row=0, column=0, sticky='nsew')
      #avlab.grid(row=0, column=1)
      abtn.grid(row=0,column=1, sticky='nsew')
      
      aframe.grid(row=r, column=c, sticky='ew')
      r,c = nextspot(r,c)
    
    # if groupmerge:
    #   for i, (gid, pay) in enumerate(gdata):
    #     ...
    #     variable=self.choice, value=-gid-2
    #     same logic of columns and rows
    
    if self.cfgdict['allow_leaving'] and expelstep:
      # Add a button to leave the group
      # TEMPORARY: assume you get $0 on your own
      tk.Radiobutton(sb, text='Leave Team '+self.gname(self.myteam)+'\nEarn: '+CURR+'0.0', font=self.fontsm, variable=self.choice, value=self.myid, indicatoron=0).grid(row=r, column=c, sticky='ew')
      r,c = nextspot(r,c)
    
    #gframe = tk.Frame(sb, relief=tk.GROOVE, borderwidth=2)
    #gframe.grid(row=i, column=0, sticky='ew')
    tk.Radiobutton(sb, text='None\nEarn: '+self.mwidgets['nowpay']['text'], font=self.fontsm, variable=self.choice, value=-1, indicatoron=0).grid(row=r, column=c, sticky='ew')
    self.submit = tk.Button(sb, text='Submit', font=self.fontmid, command=self.submit_accept)
    self.submit.grid(row=MAXROWS+1, column=0, columnspan=c+1, sticky='ew')
    
    self.sb = sb
    
  def make_neighborview(self):
    self.nsize = 50
    self.canvas = tk.Canvas(self.mwidgets['neighbors'], height=self.csize, width=self.csize)
    can = self.canvas
    
    # Also set up colors or avatars for the neighbors
    #self.update_neighbors(gdata)
    if MAX_TEAMS <= 9:
      self.colors = COLORS9
    elif MAX_TEAMS <= 11:
      self.colors = COLORS11
    elif MAX_TEAMS <= 12:
      self.colors = COLORS12
    elif MAX_TEAMS <= 16:
      self.colors = COLORS16
    elif MAX_TEAMS <= 22:
      self.colors = COLORS22
    else:
      raise Exception("Not enough colors")
    
    self.canvas.grid(row=0, column=0)
    
  def make_teamview(self, neighbors):
    if self.teamview is not None:
      self.teamwords.destroy()
      self.teamview.destroy()
    
    self.teamwords = tk.Frame(self.mainscreen, borderwidth=2, relief=tk.GROOVE)
    self.teamview = tk.Frame(self.mainscreen, borderwidth=2, relief=tk.SUNKEN, background=self.colors[self.myteam])
    
    if max(neighbors) > len(self.avatars):
      raise IndexError('Not enough avatars!')
    
    tk.Label(self.teamwords, text='Your team', font=self.fontmid).grid(row=0,column=0)
    tk.Label(self.teamwords, text='(Team '+self.gname(self.myteam)+')', font=self.fontsm).grid(row=1,column=0)
    
    neighbors.remove(self.myid)
    neighbors.insert(0,self.myid)
    
    # pack with one entry for each team member, with their avatar
    for i, aid in enumerate(neighbors):
      frame = tk.Frame(self.teamview, borderwidth=2, relief=tk.GROOVE)
      img = tk.Label(frame, image=self.avatars[aid], height=64)
      lab = tk.Label(frame, text=('You' if aid == self.myid else self.aname(aid)), font=self.fontmed)
      img.grid(row=0, column=0)
      lab.grid(row=0, column=1)
      frame.grid(row=i, column=0, sticky='nsew')
    
    self.teamwords.grid(row=0, column=2, sticky='nsew')
    self.teamview.grid(row=1, column=2, sticky='nsew')
    
    self.nteam = len(neighbors)
    
  def make_teamview_publicgoods(self, neighbors, contribs):
    if self.teamview is not None:
      self.teamwords.destroy()
      self.teamview.destroy()
    
    self.teamwords = tk.Frame(self.mainscreen, borderwidth=2, relief=tk.GROOVE)
    self.teamview = tk.Frame(self.mainscreen, borderwidth=2, relief=tk.SUNKEN, background=self.colors[self.myteam])
    
    if max(neighbors) > len(self.avatars):
      raise IndexError('Not enough avatars!')
    
    tk.Label(self.teamwords, text='Your team', font=self.fontmid).grid(row=0,column=0)
    tk.Label(self.teamwords, text='(Team '+self.gname(self.myteam)+')', font=self.fontsm).grid(row=1,column=0)
    
    #neighbors.remove(self.myid)
    #neighbors.insert(0,self.myid)  # THIS BREAKS SYNCHRONIZATION WITH CONTRIBS
    
    if not self.cfgdict['_hide_publicgoods']:
      tk.Label(self.teamview, text='Contributions:', font=self.fontsm).grid(row=0, column=0, sticky='nsew')
    
    rowoffset = 1
    # pack with one entry for each team member, with their avatar and contribution
    for i, (aid, contrib) in enumerate(zip(neighbors, contribs)):
      frame = tk.Frame(self.teamview, borderwidth=2, relief=tk.GROOVE)
      img = tk.Label(frame, image=self.avatars[aid], height=64)
      #lab = tk.Label(frame, text=CURR+str(contrib), font=self.fontmed)
      lab = tk.Label(frame, text=(' You' if aid == self.myid else ' '+self.aname(aid)), font=self.fontsm, justify=tk.LEFT)
      ctext = ' '+CURR+str(contrib) if not self.cfgdict['_hide_publicgoods'] else ''
      lab2 = tk.Label(frame, text=ctext, font=self.fontsm, justify=tk.LEFT)
      img.grid(row=0, rowspan=2, column=0)
      lab.grid(row=0, column=1, sticky='ew')
      lab2.grid(row=1, column=1, sticky='ew')
      frame.grid(row=i+rowoffset, column=0, sticky='nsew')
    
    self.teamwords.grid(row=0, column=2, sticky='nsew')
    self.teamview.grid(row=1, column=2, sticky='nsew')
    
    self.nteam = len(neighbors)
    
  def no_close(self):
    pass
  
  def make_ratings_sidebar(self, neighbors):
    MAXROWS = int((len(neighbors)+1)/2)
    
    # new Toplevel window
    #rb = self.ratingbox = tk.Toplevel()
    #rb.title("Participant ratings")
    #rb.protocol( 'WM_DELETE_WINDOW', self.no_close() )
    #rb.transient(self.root)
    
    # As a frame instead
    rp = self.ratingpad = tk.Frame(self.content, width=32)
    rp.grid(row=0, column=3, rowspan=3, sticky='ns')
    
    rb = self.ratingbox = tk.Frame(self.content, relief=tk.SUNKEN)
    rb.grid(row=0, column=4, rowspan=3, sticky='nsew')
    rb.grid_remove()
    
    self.ratingwidgets = {}
    self.ratingvars = {}
    self.ratinglog = []
    
    #titlelabel = tk.Label(rb, text='Player ratings', font=self.fontsm)
    if not self.cfgdict['_hide_publicgoods']:
      titletext = 'Here, you can rate the other players.\nThese ratings are for your reference\nand will not be shown to the other players'
    else:
      titletext = 'Here is a list of the other players.'
    instrlabel = tk.Label(rb, text=titletext, font=self.fontxsm)
    ratingframe = tk.Frame(rb)
    #titlelabel.grid(row=0, column=0)
    instrlabel.grid(row=0, column=0)
    ratingframe.grid(row=2, column=0, sticky='nsew')
    
    r = 0
    c = 0
    for i,aid in enumerate(neighbors):
      frame = tk.Frame(ratingframe, borderwidth=2, relief=tk.GROOVE)
      img = tk.Label(frame, image=self.avatars[aid], height=64)
      labtext = ('You' if aid == self.myid else self.aname(aid))
      lab = tk.Label(frame, text=labtext, font=self.fontsm, justify=tk.LEFT)
      img.grid(row=0, rowspan=2, column=0)
      lab.grid(row=0, column=1, sticky='ew')
      
      rw = self.ratingwidgets[aid] = []
      v = self.ratingvars[aid] = tk.IntVar()
      bframe = tk.Frame(frame)
      if aid != self.myid and not self.cfgdict['_hide_publicgoods']:  ## Do not allow you to rate yourself!
        for j in range(5):
          button=tk.Radiobutton(bframe, image=self.staroff, relief=tk.FLAT, indicatoron=False, variable=v, value=j+1)
          #button.bind("<Enter>", lambda e, aid=aid: self.star_enter(e,aid))
          #button.bind("<Leave>", lambda e, aid=aid: self.star_leave(e,aid))
          button.bind("<Button-1>", lambda e, aid=aid: self.star_click(e,aid))
          button.grid(row=0, column=j)
          rw.append(button)
        v.trace('w', lambda x,y,z,aid=aid, *args: self.rating_change(aid))    ## THIS IS KIND OF A HACK
      
      bframe.grid(row=1, column=1, sticky='nsew')
      frame.grid(row=r, column=c, sticky='nsew')
      r += 1
      if r >= MAXROWS:
        r = 0; c += 1
      
  def star_enter(self, event, aid):
    w = event.widget
    if w['state'] == tk.DISABLED:
      return
    imgs = [self.staroff, self.staron]
    active = True
    # Activate stars up to the currently moused-over button
    for b in self.ratingwidgets[aid]:
      b.config(image=imgs[active])
      if b == w:
        active = False
  
  def star_leave(self, event, aid):
    w = event.widget
    if w['state'] == tk.DISABLED:
      return
    imgs = [self.staroff, self.staron]
    active = False
    # Activate stars up to the currently active button
    for i,b in enumerate(reversed(self.ratingwidgets[aid])):
      #if b['state'] == tk.ACTIVE:
      #if b['relief'] == tk.SUNKEN:
      if i == self.ratingvars[aid].get():
        active = True
      b.config(image=imgs[active])
  
  def star_click(self, event=None, aid=None, button=None):
    w = event.widget
    if w['state'] == tk.DISABLED:
      return
    imgs = [self.staroff, self.staron]
    active = True
    # Activate stars up to the currently moused-over button
    for b in self.ratingwidgets[aid]:
      b.config(image=imgs[active])
      if b == w:
        active = False
  
  def rating_change(self, aid=None):
    if self.vidrec:
      eframe, etime = self.vidrec.queryframetime()
    else:
      eframe = -1; etime = time.time()
    #print "Ratings:", [(aid, rv.get()) for aid,rv in self.ratingvars.items()]
    print "Rating:", aid, self.ratingvars[aid].get()
    self.ratinglog.append( [self.myid, aid, self.ratingvars[aid].get(), eframe, etime] )
    
    
    
  def m_getratinglog(self, event):
    self.getdata(event)
    ratinglog = copy.copy(self.ratinglog)
    self.ratinglog = []
    self.backend.sendqueue.put(ratinglog)
    
  def m_getratings(self, event):
    self.getdata(event)
    ratings = {aid:ratingvar.get() for aid, ratingvar in self.ratingvars.iteritems()}
    self.backend.sendqueue.put(ratings)
    
  def m_showratings(self, event):
    self.getdata(event)
    self.showratings()
    self.backend.sendqueue.put('done')
  
  def m_hideratings(self, event):
    self.getdata(event)
    self.hideratings()
    self.backend.sendqueue.put('done')
    
  def showratings(self):
    self.ratingbox.grid()
    
  def hideratings(self):
    self.ratingbox.grid_remove()
    
  def m_disableratings(self, event):
    self.getdata(event)
    #self.ratingbox.grid_remove()
    self.setState(self.ratingbox, tk.DISABLED)
    self.backend.sendqueue.put('done')
  
  def m_enableratings(self, event):
    self.getdata(event)
    #self.ratingbox.grid_remove()
    self.setState(self.ratingbox, tk.NORMAL)
    self.backend.sendqueue.put('done')
  
  def m_updateratings(self, event):
    rdata = self.getdata(event)
    ## TODO: implement
    self.backend.sendqueue.put('done')
  
  
  def update_neighbors(self, gdata):
    # Draw the graphical representation of the social network
    if not len(gdata):    return
    if self.cfgdict['graph_type'] == 'complete_graph':   return     # No sense drawing if we can't see it.
    # gdata is (nbrid, gid) pairs
    # 400 x 400 drawing area
    can = self.canvas
    csize = self.csize
    nsize = self.nsize
    cent = csize/2
    rad = 150
    centtl = cent - nsize/2
    centbr = cent + nsize/2
    
    nnbr = len(gdata)
    theta = 2*math.pi/nnbr
    posns = [(rad*math.sin(i*theta), rad*math.cos(i*theta)) for i in range(nnbr)]
    
    can.delete(tk.ALL)
    
    # Draw 'spokes' to neighbors
    for x,y in posns:
      can.create_line(cent, cent, cent+x, cent+y, width=4)
    
    # Draw oval for self
    self.myoval = can.create_oval(centtl, centtl, centbr, centbr, fill=self.colors[self.myteam], width=2)
    can.create_text(cent, cent, text='You', font=self.fontsm)
    self.canvas.create_image(centtl, centtl, image=self.avatars_sm[self.myid])
    if self.myskill != -1:
      self.canvas.create_text(centbr, centtl, text=str(self.myskill), font=self.fontsm)
    
    #print gdata
    #print self.colors
    if max([g[1] for g in gdata]) >= len(self.colors):
      print "NOT ENOUGH COLORS"
      print "Requested", max([g[1] for g in gdata]), "but only", len(self.colors), "available"
    
    # Draw ovals for neighbors
    for (nbrid, gid, skill), (x,y) in zip(gdata,posns):
      can.create_oval(centtl+x, centtl+y, centbr+x, centbr+y, fill=self.colors[gid], width=2)
      
      can.create_image(centtl+x, centtl+y, image=self.avatars_sm[nbrid])
      can.create_text(cent+x, cent+y, text=self.gname(gid), font=self.fontsm)
      #can.create_text(cent+x, cent+y, text=str(nbrid), font=self.fontsm)
      #can.create_image(cent+x, cent+y, image=self.avatars_sm[nbrid])
      
      if skill != -1:
        can.create_text(centbr+x, centtl+y, text=str(skill), font=self.fontsm)
        
    self.canvas.grid(row=0, column=0)
    
  def update_myteam(self):
    csize = self.csize
    nsize = self.nsize
    cent = csize/2
    centtl = cent - nsize/2
    centbr = cent + nsize/2
    self.myoval = self.canvas.create_oval(centtl, centtl, centbr, centbr, fill=self.colors[self.myteam], width=2)
    self.canvas.create_image(centtl+x, centtl+y, image=self.avatars_sm[self.myid])
    
  def show_screen(self, screen):
    self.activescreen.grid_remove()
    screen.grid(row=0, column=0)
    self.activescreen = screen
    
  def getdata(self, event):
    #print event.type, event.x, self.dataqueue.qsize()
    while True:   # Cycle through events in the queue in case the one we want is not first
      qdat = self.dataqueue.get(block=True, timeout=None)
      msgnum, command, data = qdat
      #print qdat, event.x
      if msgnum != event.x and not self.dataqueue.empty():
        self.dataqueue.put(qdat)
      else:
        break
    return data
  
  def m_intro(self, event):
    self.getdata(event)
    self.show_screen(self.introscreen)
    print "Show intro"
    self.backend.sendqueue.put('done')
  
  def m_exit(self, event):
    self.getdata(event)
    self.show_screen(self.exitscreen)
    self.backend.sendqueue.put('done')
    
  def m_instructions(self, event):
    self.getdata(event)
    self.update_instruction_text()
    self.show_screen(self.instructions)
    if self.infobutton:
      self.infobutton.destroy()
    self.infobutton = tk.Button(self.instructions, text='OK', font=self.fontmed, command=self.submit_information_blocking)
    self.infobutton.grid(row=2, column=0)
    # Update anything else that needs to change based on the current configuration
    self.update_sidebar_size()
    
  def m_publicgoods_instructions(self, event):
    self.getdata(event)
    self.update_pubgoods_instruction_text()
    self.show_screen(self.publicgoods_instructions)
    #self.infobutton.grid()
    if self.infobutton:
      self.infobutton.destroy()
    self.infobutton = tk.Button(self.publicgoods_instructions, text='OK', font=self.fontmed, command=self.submit_information_blocking)
    self.infobutton.grid(row=2, column=0)

  
  def m_setmyid(self, event):
    self.myid = self.getdata(event)
    print "My ID:", self.myid
    self.backend.sendqueue.put('done')
  
  
  def m_initvideo(self, event):
    vdata = self.getdata(event) #vdata = (cfg._do_video, cfg._dblog.sessionid, self.id)

    self.do_video, self.sessionid, self.userid = vdata

    today = datetime.date.today()
    
    
    if self.do_video:
      self.vidfile = '../data/ses_{sessionid:02d}_{date}/user_{userid:02d}/cap_{sessionid:02d}-{userid:02d}'.format(
        sessionid=self.sessionid, userid=self.userid, date=today.strftime('%Y-%m-%d'))
      self.vidrec = vidcapture(self.vidfile)
    else:
      self.vidrec = None
      self.sframe = self.stime = self.eframe = self.etime = -1

    if self.cfgdict['_capture_screenshots']:
      self.scrprefix = '../data/ses_{sessionid:02d}_{date}/user_{userid:02d}/scr_{sessionid:02d}-{userid:02d}'.format(
        sessionid=self.sessionid, userid=self.userid, date=today.strftime('%Y-%m-%d'))
      if not os.path.exists(os.path.dirname(self.scrprefix)):
        os.makedirs(os.path.dirname(self.scrprefix))
    

    print "Done starting video"
    self.backend.sendqueue.put('done')
  
  def m_startpreview(self, event):
    self.getdata(event)
    if self.do_video:
      self.vidrec.preview = True
    self.backend.sendqueue.put('done')
  
  def m_endpreview(self, event):
    self.getdata(event)
    if self.do_video:
      self.vidrec.preview = False
    self.backend.sendqueue.put('done')
  
  def save_screen(self, stime, sframe):
    if self.cfgdict['_capture_screenshots']:
      filename = self.scrprefix+"_{}_{}_scrcap.png".format(stime, sframe)
      try:
        subprocess.call("import -window root "+filename, shell=True)   # Note that shell=True is dangerous, but should be ok because we're creating the filename right here
      except OSError as e:
        # ImageMagick must not be installed
        print "ERROR calling ImageMagick function; is ImageMagick installed?"
        print e
  
  def markstart(self):
    if self.vidrec:
      self.sframe, self.stime = self.vidrec.queryframetime()
    else:
      self.stime = time.time()
      
    self.save_screen(self.stime, self.sframe)
      
  def markend(self):
    if self.vidrec:
      self.eframe, self.etime = self.vidrec.queryframetime()
    else:
      self.etime = time.time()

    self.save_screen(self.etime, self.eframe)
      
  def m_getframetimes(self, event):
    self.getdata(event)
    self.backend.sendqueue.put( (self.sframe, self.eframe, self.stime, self.etime) )
  
  def m_startcapture(self, event):
    self.getdata(event)
    if self.do_video:
      self.vidrec.start()
    self.backend.sendqueue.put('done')
  
  def m_stopcapture(self, event):
    self.getdata(event)
    if self.do_video:
      self.vidrec.stop()
    self.backend.sendqueue.put('done')
  
  def m_endcapture(self, event):
    self.getdata(event)
    if self.do_video:
      self.vidrec.stop()
      self.vidrec.quit()
    self.backend.sendqueue.put('done')  
  
  
  def m_updatepay(self, event):
    nowpay = self.getdata(event)
    ## Update nowpay tk widget
    self.mwidgets['nowpay'].config(text=CURR+str(round(nowpay,2)))
    print "Updated pay"
    self.backend.sendqueue.put('done')
    
  def m_updatenbrs(self, event):
    data = self.getdata(event)  # (nbrid, gid) pairs
    
    # for nbrid, gid, ... in data
    self.update_neighbors(data)
    
    self.backend.sendqueue.put('done')
    
  def m_updatemyteam(self, event):
    (myteam, myskill) = self.getdata(event)
    self.myteam = myteam
    self.myskill = myskill
    #self.update_myteam()  ### ????
    self.backend.sendqueue.put('done')
  
  def m_updateteam(self, event):
    team_members = self.getdata(event)
    self.make_teamview(team_members)
    self.backend.sendqueue.put('done')
  
  def m_propose(self, event):
    data = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Apply', bg='dark green')
    # create neighbor group propose checkboxes
    self.make_sidebar(data, chooseone=False)
    # update neighbor view?
    #self.update_neighbors()
    self.mwidgets['instructions'].config(text='At this stage, you may send applications to join neighboring teams.\nChoose whichever teams you would like to apply to (if any)\nfrom the center bar, and select "Submit"')
    self.markstart()
    
  def m_acceptvote(self, event):
    data = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Accept', bg='yellow')
    # create neighbor group propose checkboxes
    self.make_sidebar_agent(data)
    # update neighbor view?
    #self.update_neighbors()
    itext = 'Your team has received '+str(len(data))+' application'+('s' if len(data)!=1 else '')+'.\nCast your vote for at most one agent to accept to join your team.'
    self.mwidgets['instructions'].config(text=itext)
    self.markstart()
  
  def m_acceptvote_groupmerge(self, event):
    data = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Accept', bg='orange')
    # create neighbor group propose checkboxes
    self.make_sidebar_agent(data, groupmerge=True)
    napps = len(data[0])+len(data[1])
    itext = 'Your team has received '+str(napps)+' application'+('s' if napps!=1 else '')+'.\nCast your vote for at most one agent or team to accept to join your team.'
    self.mwidgets['instructions'].config(text=itext)
    self.markstart()
  
  def m_consider(self, event):
    data = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Join', bg='blue')
    # create neighbor group propose checkboxes
    self.make_sidebar(data, chooseone=True)
    # update neighbor view?
    #self.update_neighbors()
    #naccepts = str(len(data))
    naccepts = str(len([1 for d in data if d[1] > 0]))
    itext = 'You have received '+naccepts+' acceptance'+('s' if len(data)!=1 else '')+' from other teams.\nChoose one team to join, or "Stay" to stay with your current team.'
    self.mwidgets['instructions'].config(text=itext)
    self.markstart()

  def m_expelvote(self, event):
    data = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Expel', bg='red')
    # create neighbor group propose checkboxes
    self.make_sidebar_agent(data, expelstep=True)
    # update neighbor view?
    #self.update_neighbors()
    itext = 'Cast your vote for at most one agent to accept to expel from your team.'
    self.mwidgets['instructions'].config(text=itext)
    self.markstart()
        
  def m_turndone(self, event):
    information = self.getdata(event)
    self.show_screen(self.mainscreen)
    if self.sb is not None:
      self.sb.destroy()
    self.mwidgets['title'].config(text='Turn Done', bg=self.bgdefault)
    self.mwidgets['instructions'].config(text=information)
    if self.infobutton:
      self.infobutton.destroy()
    #self.infobutton = tk.Button(self.mainscreen, text='OK', command=self.submit_information_blocking_disappear, font=self.fontmed)
    #self.infobutton.grid(row=2, column=2)
    self.infobutton = tk.Button(self.mwidgets['infobar'], text='OK', command=self.submit_information_blocking_disappear, font=self.fontmed)
    self.infobutton.grid(row=0, column=2)
    #self.root.after(5000, self.submit_information)
    
  def m_postprocess(self, event):
    information = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Round Done', bg=self.bgdefault)
    #if not self.cfgdict['_do_ratings']:
    #  self.sb.destroy()
    self.mwidgets['instructions'].config(text=information)
    if self.infobutton:
      self.infobutton.destroy()
    #self.infobutton = tk.Button(self.mainscreen, text='OK', command=self.submit_postprocess, font=self.fontmed)
    #self.infobutton.grid(row=2, column=2)
    self.infobutton = tk.Button(self.mwidgets['infobar'], text='OK', command=self.submit_postprocess, font=self.fontmed)
    self.infobutton.grid(row=0, column=2)
    self.markstart()
    
    
  def m_publicgoods(self, event):
    nowpay = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Teamwork', bg='white')
    
    #self.pg_nowpay = int(nowpay)
    #self.pg_nowpay = round(nowpay,2)
    self.pg_nowpay = nowpay
    if 'pgwidgets' not in self.mwidgets:
      pgw = self.mwidgets['pgwidgets'] = {}
      content = pgw['content'] = tk.Frame(self.mwidgets['sidebar'],width=self.sidebarwid)
      cdesc = 'the shared pot' if not self.cfgdict['_hide_publicgoods'] else 'the lottery'
      pgw['offerlab'] = tk.Label(content, text='How much do you contribute\nto '+cdesc+'?', font=self.fontmid)
      pgw['offerlab'].grid(row=0, column=0)
      pgw['offervar'] = tk.IntVar()
      #pgw['offerspin'] = tk.Spinbox(content, from_=0, to=nowpay, font=self.fontmed, width=3, textvariable=pgw['offervar'])
      pgw['offerspin'] = tk.Scale(content, from_=0, to=nowpay, font=self.fontmid, variable=pgw['offervar'], tickinterval=nowpay/5, orient=tk.HORIZONTAL) #width=3,
      pgw['offerspin'].grid(row=1, column=0, sticky='ew')
      pgw['offervar'].trace(mode='w', callback = self.update_pay_publicgoods)
      if self.cfgdict['_hide_publicgoods']:
        pgw['winnings'] = tk.Label(content, text='You could win between '+CURR+'0 and '+CURR+'0', font=self.fontsm)
        pgw['winnings'].grid(row=2, column=0)
      pgw['submit'] = tk.Button(content, text='Submit', font=self.fontmid, command=self.submit_publicgoods)
      pgw['submit'].grid(row=3, column=0)
    else:
      pgw = self.mwidgets['pgwidgets']
      pgw['offerspin'].grid()
      pgw['offervar'].set(0)
      pgw['offerspin'].config(to=nowpay)
      if self.cfgdict['_hide_publicgoods']:
        pgw['winnings'].config(text='You could win between '+CURR+'0 and '+CURR+'0')
      pgw['submit'].config(text='Submit')
      self.setState(pgw['submit'], tk.NORMAL)
      
    if self.sb is not None:
      self.sb.destroy()
    
    pgw['content'].grid(row=0,column=0)
      
    self.mwidgets['paylab'].config(text='You keep:')
    
    # update neighbor view with team members
    # -- this is done by the humanagent on the server before this function is called

    if not self.cfgdict['_hide_publicgoods']:
      longtext = 'At this stage, choose how much of your potential pay you\nwould like to contribute to the shared pot and select "Submit"\nThe pot will be increased by '+str(self.cfgdict['pubgoods_mult'])+"% and split evenly among everyone on your team.\nEach team member's contribution will be shown publicly to the other members of the team."
    else:
      longtext = "Choose how much of your pay you would like to enter in the lottery.\nThe amount you contribute determines the amount you are eligible to win."

    self.mwidgets['instructions'].config(text=longtext)
    
    self.canvas.grid_remove()
    
    self.markstart()
  
  
  def update_pay_publicgoods(self, varname, elementname, mode):
    amount = int(self.mwidgets['pgwidgets']['offerspin'].get())
    self.mwidgets['nowpay'].config(text=CURR+str(self.pg_nowpay - amount))
    if self.cfgdict['_hide_publicgoods']:
      minwin = amount*1.2 / self.nteam
      maxwin = (amount + self.pg_nowpay*(self.nteam-1))*1.2 / self.nteam
      self.mwidgets['pgwidgets']['winnings'].config(text='You could win between '+CURR+str(minwin)+' and '+CURR+str(maxwin))
    
  def submit_publicgoods(self):
    self.markend()
    submitbutton = self.mwidgets['pgwidgets']['submit']
    self.setState(submitbutton, tk.DISABLED)
    submitbutton.config(text='Waiting...')
    
    offer = int(self.mwidgets['pgwidgets']['offerspin'].get())
    self.backend.sendqueue.put(offer)
  
  def m_publicgoods_conclusion(self, event):
    data = self.getdata(event)
    self.show_screen(self.mainscreen)
    self.mwidgets['title'].config(text='Teamwork', bg='white')
    
    mypay, (neighbors, contribs) = data
    
    #self.update_neighbors(xxx) # This is done by the human_agent
    
    print zip(neighbors, contribs)
    neighbors, contribs = zip(*sorted(zip(neighbors, contribs), key=operator.itemgetter(1), reverse=True))
    print zip(neighbors, contribs)
    
    self.mwidgets['pgwidgets']['content'].grid_remove()
    
    self.make_teamview_publicgoods(neighbors, contribs)
    
    self.mwidgets['paylab'].config(text='Currently earning:')
    self.mwidgets['nowpay'].config(text=CURR+str(round(mypay,2)))
    
    self.canvas.grid_remove()
    
    self.backend.sendqueue.put('done')
    
  
  def m_addpay(self, event):
    addpay = self.getdata(event)
    self.totalpay += addpay
    self.mwidgets['earnamt'].config(text=CURR+str(self.totalpay))
    self.backend.sendqueue.put('done')
    
  def m_conclusion(self, event):
    data = self.getdata(event)
    self.show_screen(self.endscreen)
    self.backend.sendqueue.put('done')  
  
  def submit_information(self):
    print "SUBMIT INFORMATION"
    self.setState(self.infobutton, tk.DISABLED)
    self.infobutton.grid_remove()
    self.backend.sendqueue.put('done')
  
  def submit_information_blocking(self):
    self.setState(self.infobutton, tk.DISABLED)
    #self.infobutton.grid_remove()
    self.infobutton.config(text='Waiting...')
    self.backend.sendqueue.put('send_done')
  
  def submit_information_blocking_disappear(self):
    print "SUBMIT INFORMATION BLOCKING"
    self.infobutton.grid_remove()
    #self.infobutton.config(text='Waiting...')
    self.backend.sendqueue.put('send_done')
    
  def submit_propose(self):
    self.markend()
    # Send the list of groups that this agent applies to
    # look at the array of variables
    applications = [gid for gid, chosen in self.choices.items() if chosen.get()]
    #self.submit['state'] = tk.DISABLED
    self.setState(self.sb, tk.DISABLED)
    self.submit.config(text='Waiting...')
    self.backend.sendqueue.put(applications)
  
  def submit_accept(self):
    self.markend()
    # this handles accepting a new agent to a team, and joining a new team
    # look at the single variable
    #self.submit['state'] = tk.DISABLED
    self.setState(self.sb, tk.DISABLED)
    self.submit.config(text='Waiting...')
    self.backend.sendqueue.put(self.choice.get())
    
  def submit_postprocess(self):
    self.markend()
    self.infobutton.grid_remove()
    self.backend.sendqueue.put('send_done')
    
    if self.sb:
      self.sb.destroy()
    

    
  def setState(self, widget, state=tk.DISABLED):
    try:
      widget.configure(state=state)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        self.setState(child, state=state)
    

class messageTester(threading.Thread):
  def __init__(self, tb):
    threading.Thread.__init__(self)
    self.tkroot = tb.root
    self.dataqueue = tb.dataqueue
    self.msgnum = 5
    
  def guisend(self, cmd, data):
    self.dataqueue.put( (self.msgnum, cmd, data) )
    self.tkroot.event_generate('<<'+cmd+'>>', x=self.msgnum, when='tail')
    self.msgnum += 1
    
  def run(self):
    cmd = None
    msgnum = 10
    
    #self.guisend('exitsurvey', 0)
    
    #k=raw_input()
    
    self.guisend('setmyid', 0)
    self.guisend('updatemyteam', (3,2))
    
    self.guisend('updatenbrs', [(1,1,0), (2,4,1), (3,7,2), (7,4,3), (8,8,2)])
    self.guisend('updateteam', [0, 4, 7, 12])
    
    #self.guisend('propose', [(0, 1, 10), (1, 5, 100), (7, 2, 50)])
    #self.guisend('acceptvote', [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9)])
    
    self.guisend('initvideo', (False, 0, 0))
    
    self.guisend('publicgoods', 10)
    self.guisend('publicgoods_conclusion', (10, ( (0,4,7,12), (2,3,4,5) ) ) )
    
    self.guisend('postprocess', 'here is some text')
    
    self.guisend('exitsurvey', 0)
    
    # General event generator
    while cmd != 'quit':
      cmd = raw_input("Enter an event or quit: ")
      if cmd == 'quit':
        continue
      cmd, data = cmd.split('\t')
      data = eval(data)
      self.dataqueue.put( (msgnum, cmd, data) )
      self.tkroot.event_generate('<<'+cmd+'>>', x=msgnum, when='tail')
      msgnum += 1

if __name__=='__main__':
  # Testing functions
  if len(sys.argv) == 1:
    tb = TFGui()
    
    mt = messageTester(tb)
    mt.start()
    
    tb.run()
  elif len(sys.argv) == 2:
    tb = TFGui(sys.argv[1])
    tb.run()
    
