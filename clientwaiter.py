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
"""
ClientWaiter class waits for connections from client computers 
running frontend.py.
"""

import socket
import threading

from utils import send_message, SERVER_PORT

def log(text, level=0):
  """Dummy method to print logging text"""
  print text
  # write text to file

ADDRESS = ''  # '' for anything


class ClientWaiter(object):
  """Waits for connections from client computers running frontend.py.
  
  Waits for clients until server user presses ENTER. 
  Listens on SERVER_PORT from utils.py.
  Use getclients() to return the client connections
  """
  def __init__(self):
    """Starts the wait thread, and terminates when user presses ENTER"""
    self.clientsockets = []
    self.clientaddrs = []
    self.nclients = 0
    self.socket = None
    
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
    """Waits for clients until self.waiting is False. Used in a thread."""
    log("Server waiting for clients")
    sock = self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ADDRESS, SERVER_PORT))
    sock.listen(1)
    sock.settimeout(2.0)
    while self.waiting:
      #log("Waiting for a connection")
      try:
        connection, client_address = sock.accept()
      except socket.error, strerror:
        if str(strerror) != 'timed out':
          print strerror
      else:
        i = len(self.clientsockets)
        if self.client_setup(connection, i):
          log("Client "+str(i)+" connected!")
          self.clientsockets.append(connection)
        else:
          log("Client {0} at {1} connection failed!".format(i, client_address), 0)
    sock.settimeout(None)
    self.nclients = len(self.clientsockets)
  
  def client_setup(self, connection, clientnum):
    """Dummy method to initialize a client once it's connected."""
    return send_message(connection, ("client_number", clientnum) )
  
  def getclients(self):
    """Returns the list of client connections"""
    return self.clientsockets
