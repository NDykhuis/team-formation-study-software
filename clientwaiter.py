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