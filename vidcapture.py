import numpy as np
import threading
import time
import os

try:
  import cv2
except ImportError:
  print "Error importing OpenCV - are the libraries installed?"

FRAME_DELAY = 0.01

IMG_WIDTH = 800
IMG_HEIGHT = 600

class vidcapthread(threading.Thread):
  def __init__(self, filename):
    threading.Thread.__init__(self)
    self.frame = 0
    self.nowtime = time.time()
    
    if not os.path.exists(os.path.dirname(filename)):
      os.makedirs(os.path.dirname(filename))
    
    self.cap = cv2.VideoCapture(200)
    self.cap.read()
    print 'fps'; self.cap.set(cv2.cv.CV_CAP_PROP_FPS, 60)
    print 'height'; self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, IMG_WIDTH)
    print 'width'; self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, IMG_HEIGHT)
    self.fourcc = cv2.cv.CV_FOURCC(*'XVID')
    #self.fourcc = cv2.cv.CV_FOURCC(*'MP42')
    self.out = cv2.VideoWriter(filename+'.avi',self.fourcc, 30.0, (IMG_WIDTH,IMG_HEIGHT))   
    #self.fourcc = cv2.cv.CV_FOURCC(*'JPEG')
    #self.out = cv2.VideoWriter(filename+'_%08d.jpg',self.fourcc, 60.0, (IMG_WIDTH,IMG_HEIGHT))
    self.outfile = open(filename+'_frametimes.txt','w')
    self.outfile.write('frame\ttime\n')
    self.capture = False  ## Switch this on and off from outside the thread
    self.alive = True
    self.preview = False
    self.windowsup = False

  def run(self):
    print "Starting video capture thread"
    tstart = time.time()
    fstart = self.frame
    while self.alive and self.cap.isOpened():
      if self.capture or self.preview:
        ret, frame = self.cap.read()
        if ret==True:
          if self.capture:
            # write frame to video file
            self.out.write(frame)
            # set current time and frame in a thread-safe(?) way
            self.nowtime, self.frame = time.time(), self.frame + 1
            # write timestamp to file
            self.outfile.write('{frame:08d}\t{time:.16f}\n'.format(frame=self.frame, time=self.nowtime))
          
          if self.preview:
            cv2.imshow('preview',frame)
            cv2.moveWindow('preview', 0,0)
            self.windowsup = True
          elif self.windowsup:
            cv2.destroyAllWindows()
          
          if self.capture and not self.frame % 120:
            tnow = time.time()
            print "FPS: ", (self.frame - fstart)/(tnow - tstart)
            tstart = tnow
            fstart = self.frame
        else:
          print "RET BAD"
          break
      time.sleep(FRAME_DELAY)   # Allow other threads to process!
      if cv2.waitKey(1) & 0xFF == ord('q'):
          break

    print "Video cleaning up!"
    self.alive = False
    # clean up
    self.outfile.close()
    # Release everything if job is finished
    self.cap.release()
    #self.out.release()
    cv2.destroyAllWindows()



class vidcapture(object):
  def __init__(self, filename):
    self.vidcap = vidcapthread(filename)
    self.vidcap.daemon = True
    self.vidcap.start() # Start the video capture thread, but don't start recording
    
  def start(self):
    self.vidcap.capture = True
    
  def stop(self):
    self.vidcap.capture = False
    
  def quit(self):
    self.vidcap.capture = False
    self.vidcap.alive = False
    self.vidcap.join()
    
  def setpreview(self, preview):
    self.vidcap.preview = preview
  
  def queryframetime(self):
    if self.vidcap.alive:
      return self.vidcap.frame, self.vidcap.nowtime
    else:
      return 0, time.time()
    
  def mark_event(self, event_description):
    # event_description is a dictionary of column:value pairs
    if self.vidcap.alive:
      timestamp, frame = self.vidcap.nowtime, self.vidcap.frame
    else:
      timestamp, frame = time.time(), 0
    
    # write to file:
    # timestamp,frame,all_other_columns_in_event_description
  
  
if __name__=='__main__':
  vc = vidcapture('../testdata/testfile')
  vc.start()
  print "Vid cap started"
  x = 0
  #for i in range(10000):
  #  x += 1
    #print x
  time.sleep(1)
  print vc.queryframetime()
  #for i in range(10000):
  #  x += 1
    #print x
  time.sleep(1)
  print vc.queryframetime()
  for i in range(10000):
    x += 1
  time.sleep(1)
  print vc.queryframetime()
  time.sleep(1)
  vc.quit()
  time.sleep(1)
  print "Done"
  
