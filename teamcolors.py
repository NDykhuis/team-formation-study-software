#
# teamcolors.py - provides sets of distinct colors
# 
# Copyright (C) 2015  Nathan Dykhuis
# with colors from various online sources
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
This module provides sets of visually distinct colors, in HTML hex format.

Five sets of colors are provided, for 9, 11, 12, 16, and 22 items.
Color sets are named "COLORSxx" where xx is the number of colors, and
are Python lists of HTML colors, of the form "#XXXXXX"

When run on its own, this module creates a Tk window showing a set of
colors. Clicking a button will rearrange the colors; mousing over
shows the hex value of the color.
"""

import random

# Kenneth Kelly's 22 colors of maximum contrast
COLORS22 = [    
    "#FFB300", #Vivid Yellow
    "#803E75", #Strong Purple
    "#FF6800", #Vivid Orange
    "#A6BDD7", #Very Light Blue
    "#C10020", #Vivid Red
    "#CEA262", #Grayish Yellow
    "#817066", #Medium Gray
    "#007D34", #Vivid Green
    "#F6768E", #Strong Purplish Pink
    "#00538A", #Strong Blue
    "#FF7A5C", #Strong Yellowish Pink
    "#53377A", #Strong Violet
    "#7F180D", #Strong Reddish Brown
    #"#232C16", #Dark Olive Green
    "#3f4f27", #Less Dark Olive Green
    "#FF8E00", #Vivid Orange Yellow
    "#B32851", #Strong Purplish Red
    "#F4C800", #Vivid Greenish Yellow
    "#93AA00", #Vivid Yellowish Green
    "#8E5121",
    #"#593315", #Deep Yellowish Brown
    "#F13A13", #Vivid Reddish Orange
]
#random.shuffle(COLORS22)

# From
# http://prestopnik.com/warfish/colors/    
COLORS16 = [
  #"#262626",
  "#0000bd",
  "#f20019",
  "#008000",
  "#fefe00",
  "#fe8420",
  "#00fefe",
  "#910022",
  "#827848",#"#827800", # was too close to 008000
  "#8f00c7",
  "#0086fe",
  "#fe68fe",
  #"#70fe00",
  "#60ee00",
  "#fed38b",
  "#808080",
  "#a0d681",
  "#5b5b8b"
  #"ffffff"
]
    
COLORS9 = [
  "#e41a1c",
  "#377eb8",
  "#4daf4a",
  "#984ea3",
  "#ff7f00",
  "#ffff33",
  "#a65628",
  "#f781bf",
  "#999999"
]

# Boynton's list of 11 colors
COLORS11 = [
  '#0000FF',
  '#FF0000',
  '#009900',
  '#FFFF00',
  '#FF00FF',
  '#FF8080',
  '#808080',
  '#800000',
  '#FF8000'
]

COLORS12 = [
"#a6cee3",
"#1f78b4",
"#b2df8a",
"#33a02c",
"#fb9a99",
"#e31a1c",
"#fdbf6f",
"#ff7f00",
"#cab2d6",
"#6a3d9a",
"#ffff99",
"#b15928"
]

def colortest_app(testcolors):
  """ Displays a set of colors to help assess visual distinctness
  
  User can mouse over colors to show hex string, or click a button
  to rearrange the colors.
  
  Args:
    testcolors: a list of colors in "#XXXXXX" format
  """
  
  import Tkinter as tk
  import math
  root = tk.Tk()
  m = tk.Frame(root, background='#000000')
  m.grid(column=0, row=0, sticky="NSEW")
  m.columnconfigure(0, weight=1)
  m.rowconfigure(0, weight=1)
  
  # Colors should be arranged roughly in a square;
  # number of columns should be sqrt of number of colors
  cols = math.ceil(math.sqrt(len(testcolors)))
  
  r = 0
  c = 0
  labels = []   # List of color patch widgets
  locs = []     # List of locations
  for i, color in enumerate(testcolors):
    # Create new widget to display color
    #l = tk.Frame(m, background=color, width=64, height=64)
    l = tk.Label(m, background=color, width=12, height=4, text='')
    
    # Bind handlers to show/hide text on mouseover
    l.bind("<Enter>", lambda e, bnum=i: textchange(bnum, True))
    l.bind("<Leave>", lambda e, bnum=i: textchange(bnum, False))
    
    labels.append(l)
    l.grid(row=r, column=c)
    locs.append((r, c))
    c += 1
    if c >= cols:
      # move to the next row
      c = 0; r += 1
    
  def rearrange():
    """Shuffles the color locations"""
    random.shuffle(locs)
    for lab, loc in zip(labels, locs):
      lab.grid_forget()
      lab.grid(column=loc[1], row=loc[0])
    
  def textchange(i, active):
    """Shows/hides hex string text"""
    text = (str((i, testcolors[i])) if active else '')
    labels[i].config(text=text)
    
  reset = tk.Button(m, text='Shuffle', command=rearrange)
  reset.grid(row=r+1, column=0)
                    
  root.mainloop()

if __name__ == '__main__':
  colortest_app(COLORS16)
