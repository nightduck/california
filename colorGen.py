# -*- coding: utf-8 -*-
"""
Created on Sun Oct  2 14:10:38 2016
Generator that returns an endless stream of random colors. Does not return
white, black or any shades of gray. To use, just do:

var = colorGen().next()

Where rgb_tuple is a tuple with RGB coordinates
Dependencies: colorsys
@author: nightduck
"""

from colorsys import hls_to_rgb as conv

def colorGen():
    h = 0.62
    s = 0.7
    l = 0.5
    while True:
        for i in range(3):
            h += 0.38197
            if h > 1: h -= 1
            rgb = conv(h,l,s)
            yield (int(rgb[0]*256), int(rgb[1]*256), int(rgb[2]*256))
        if l >= 0.8:
            l = 0.5
        else:
            l + 0.05
    