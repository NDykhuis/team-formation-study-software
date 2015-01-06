import cPickle as pickle 
import json
import struct

BUFFER_SIZE = 1024
SERVER_PORT = 1234

DEBUG_COMM = False

def send_message(connection, message):
  if DEBUG_COMM:
    print "Sending", message
  s = json.dumps(message)
  if len(s) >= BUFFER_SIZE:
    return False
  connection.sendall(struct.pack('!I', len(s)))
  connection.sendall(s)
  return True

## http://stupidpythonideas.blogspot.com/2013/05/sockets-are-byte-streams-not-message.html
def recvall(sock, count):
  buf = b''
  while count:
    newbuf = sock.recv(count)
    if not newbuf: return None
    buf += newbuf
    count -= len(newbuf)
  return buf

def receive_message(connection):
  s1 = recvall(connection, 4)
  msg_len = struct.unpack('!I', s1)[0]
  s2 = recvall(connection, msg_len)
  try:
    data = json.loads(s2)
  except ValueError:
    print "JSON error on message:", s2
    print "message length:", s1
    raise
  if DEBUG_COMM:
    print "Received", s2
  return data
