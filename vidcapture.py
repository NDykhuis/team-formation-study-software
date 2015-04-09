#
# vidcapture.py - provides OpenCV video capture with frame timestamping
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

"""Simple OpenCV video capture module.

Use the VidCapture class to start recording video in a new thread.
Call "start", "stop", and "quit" to control video recording.
Video will be dumped to an avi file, and frame timestamps to a txt file.
"""

import threading
import time
import os

try:
  import cv2
  import cv
except ImportError:
  print "Error importing OpenCV - are the libraries installed?"

FRAME_DELAY = 0.01

IMG_WIDTH = 800
IMG_HEIGHT = 600

class VidCapThread(threading.Thread):
  """OpenCV video capture thread.
  
  Private: should only be used within this module
  
  Sets up video capture, and starts a loop that continuously
  captures frames.
    
  Outputs video to the given file name + '.avi',
  outputs frame timestamps to file name + '_frametimes.txt'
  
  Attributes:
    alive: boolean; set to False to end capture and kill the thread
    capture: boolean indicating whether to dump frames to the file
    preview: boolean indicating whether to show a preview window
  """
  def __init__(self, filename):
    """Inits video capture to record to file 'filename'"""
    threading.Thread.__init__(self)
    self.frame = 0
    self.nowtime = time.time()
    
    if not os.path.exists(os.path.dirname(filename)):
      os.makedirs(os.path.dirname(filename))
    
    # Set up video capture
    self.cap = cv2.VideoCapture(200)
    self.cap.read()
    
    self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, IMG_WIDTH)
    self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, IMG_HEIGHT)
    
    # FPS property probably does not work
    self.cap.set(cv2.cv.CV_CAP_PROP_FPS, 60)
    
    # Set up video file writer
    self.fourcc = cv2.cv.CV_FOURCC(*'XVID')
    #self.fourcc = cv2.cv.CV_FOURCC(*'MP42')
    self.out = cv2.VideoWriter(filename+'.avi', 
                               self.fourcc, 30.0, (IMG_WIDTH,IMG_HEIGHT))   
    #self.fourcc = cv2.cv.CV_FOURCC(*'JPEG')
    #self.out = cv2.VideoWriter(filename+'_%08d.jpg', 
    #                           self.fourcc, 60.0, (IMG_WIDTH,IMG_HEIGHT))
    
    # File to output frame timestamps
    self.outfile = open(filename+'_frametimes.txt','w')
    self.outfile.write('frame\ttime\n')
    
    # Set up the status parameters
    self.capture = False  ## Switch this on and off from outside the thread
    self.alive = True
    self.preview = False
    self.windowsup = False

  def run(self):
    """Start the video capture loop
    
    Video capture will run as long as self.alive is True,
    and the capture device is still open.
    
    Setting self.capture will dump frames to the video file
    Setting self.preview will open a preview window
    """
    print "Starting video capture thread"
    tstart = time.time()
    fstart = self.frame
    while self.alive and self.cap.isOpened():
      if self.capture or self.preview:
        ret, frame = self.cap.read()
        if ret == True:
          if self.capture:
            # write frame to video file
            self.out.write(frame)
            # set current time and frame in a thread-safe(?) way
            self.nowtime, self.frame = time.time(), self.frame + 1
            # write timestamp to file
            self.outfile.write('{frame:08d}\t{time:.16f}\n'.format(
              frame=self.frame, time=self.nowtime))
          
          if self.preview:
            cv2.imshow('preview', frame)
            cv.MoveWindow('preview', 0, 0)
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



class VidCapture(object):
  """OpenCV video capture class.
  
  Starts video recording in a separate thread, and controls it
  through the start, stop, and quit methods.
  
  Takes a filename without extension; extension will be '.avi' for
  the captured video, and '_frametimes.txt' for frame timestamps
  """
  def __init__(self, filename):
    self.vidcap = VidCapThread(filename)
    self.vidcap.daemon = True
    # Start the video capture thread, but don't start recording
    self.vidcap.start() 
    
  def start(self):
    """Start video recording"""
    self.vidcap.capture = True
    
  def stop(self):
    """Pause video recording"""
    self.vidcap.capture = False
    
  def quit(self):
    """Stop video recording and end capture thread"""
    self.vidcap.capture = False
    self.vidcap.alive = False
    self.vidcap.join()
    
  def setpreview(self, preview):
    """Show/hide capture preview.
    
    Args:
      preview: boolean for show or hide
    """
    self.vidcap.preview = preview
  
  def queryframetime(self):
    """Get the current frame and time from the capture thread.
    
    Returns:
      Tuple of (current frame, current time)
      If video capture is not active, current frame will be zero
    """
    if self.vidcap.alive:
      return self.vidcap.frame, self.vidcap.nowtime
    else:
      return 0, time.time()
  
def testvidcapture():
  """Open video capture and test frame rate."""
  vc = VidCapture('../testdata/testfile')
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
  
if __name__ == '__main__':
  testvidcapture()
  
