#
# clientwaiter.py - server class that waits for connections from
#                   participant UIs on client computers
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


import socket
import threading

from utils import *

def log(text, level=0):
  print text
  # write text to file

ADDRESS = ''  # '' for anything


class clientwaiter(object):
  def __init__(self):
    self.clientsockets = []
    self.clientaddrs = []
    
    # start thread to wait_for_clients
    self.waiting = True
    wait_thread = threading.Thread(target=self.wait_for_clients)
    wait_thread.daemon = True
    wait_thread.start()
    
    # ask user for when to start
    print "Waiting for clients..."
    raw_input("Press ENTER to start game\n")
    log("Waiting for wait thread to terminate...")
    # Kill wait for clients thread
    self.waiting = False
    wait_thread.join()
    log("Wait thread ended")
  
  def wait_for_clients(self):
    log("Server waiting for clients")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket = s
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ADDRESS, SERVER_PORT))
    s.listen(1)
    s.settimeout(2.0)
    while self.waiting:
      #log("Waiting for a connection")
      try:
        connection, client_address = s.accept()
      except socket.error, strerror:
        if str(strerror) != 'timed out':
          print strerror
      else:
        i = len(self.clientsockets)
        if self.client_setup(connection, i):
          log("Client "+str(i)+" connected!")
          self.clientsockets.append(connection)
        else:
          log("Client "+str(i)+" at "+str(client_address)+" connection failed!", ERROR)
    s.settimeout(None)
    self.nclients = len(self.clientsockets)
  
  def client_setup(self, connection, clientnum):
    return send_message(connection, ("client_number", clientnum) )
  
  def getclients(self):
    return self.clientsockets