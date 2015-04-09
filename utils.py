#
# utils.py - provides basic TCP send/receive functionality
# 
# Copyright (C) 2015  Nathan Dykhuis
# with portions from
# http://stupidpythonideas.blogspot.com/2013/05/sockets-are-byte-streams-not-message.html
#

"""
This module provides basic TCP send/receive functionality
"""

import json
import struct

BUFFER_SIZE = 4096
SERVER_PORT = 1234

DEBUG_COMM = False

def send_message(connection, message):
  """Sends a message to a connection.
  
  First sends an int with length of the message, 
  then sends the message in string format with JSON.
  
  Args:
    connection: a socket connection object
    message: any JSON-compatible object smaller than BUFFER_SIZE
  
  Returns:
    True if successful
  
  Raises:
    IOError if the message is too large to send
  """
  
  if DEBUG_COMM:
    print "Sending", message
  msg_string = json.dumps(message)
  if len(msg_string) >= BUFFER_SIZE:
    raise IOError("Message too large to send!")
    #return False
  connection.sendall(struct.pack('!I', len(msg_string)))
  connection.sendall(msg_string)
  return True

## http://stupidpythonideas.blogspot.com/2013/05/sockets-are-byte-streams-not-message.html
def recvall(sock, count):
  """Receive a specified number of bytes from a socket
  
  Not intended for use outside of this module
  
  Args:
    sock: a socket
    count: number of bytes to receive
    
  Returns:
    None if receive fails
    a buffer of size [count] if successful
  """
  buf = b''
  while count:
    newbuf = sock.recv(count)
    if not newbuf: return None
    buf += newbuf
    count -= len(newbuf)
  return buf

def receive_message(connection):
  """Receives a message from a connection
  
  First receives an int with length of the message,
  then receives the message and unpacks it with JSON.
  
  Args:
    connection: a socket connection object
  
  Returns:
    a Python object received from the connection
  
  Raises:
    ValueError: could not load the object with JSON  
  """
  msg_len_raw = recvall(connection, 4)
  msg_len = struct.unpack('!I', msg_len_raw)[0]
  msg_string = recvall(connection, msg_len)
  try:
    data = json.loads(msg_string)
  except ValueError:
    print "JSON error on message:", msg_string
    print "message length:", msg_len
    raise
  if DEBUG_COMM:
    print "Received", msg_string
  return data

def send_and_receive(connection, message):
  """Convenience function to send a message, and receive a response.
  
  Calls:
    send_message(connection, message)
    return receive_message(connection)
  """
  send_message(connection, message)
  return receive_message(connection)