# -*- coding: utf-8 -*-
"""
Created on Sun Oct  2 20:27:47 2016

@author: nightduck
"""

import posixpath
import colorGen

##Get filename
valid = False
while not valid:
    filename = raw_input("Enter input filename: ")
    if(posixpath.isfile(filename)):
        valid = True
    else:
        print "Please enter valid file"

##Get filename    
valid = False
while not valid:
    outFilename = raw_input("Enter output filename: ")
    if(posixpath.isfile(outFilename)):
        reply = raw_input("File exists. Overwrite? (y or n)")
        while (reply != 'y') and (reply != 'n'):
            reply = raw_input("(y or n)")
        if reply == 'y':
            valid = True
    else:
        valid = True
 
c = colorGen.colorGen()
f = open(filename, 'r')
o = open(outFilename, 'w')
line = f.next()[0:-1]

o.write(line + ",color VARCHAR\n")

cities = {'null' : (186,186,186)}

line = f.next()[0:-1]
while line[0:4] != 'edge':
    if line.split(',')[-1] in cities:
        color = cities[line.split(',')[-1]]
    else:
        color = c.next()
        cities[line.split(',')[-1]] = color
        
    o.write(line + ",'" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + "'\n")
    line = f.next()[0:-1]

o.write(line+'\n')
for line in f:
    o.write(line)

f.close()
o.close()
