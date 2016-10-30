# -*- coding: utf-8 -*-
"""
Created on Sat Oct 15 14:51:36 2016

@author: nightduck
"""

from math import floor
from itertools import ifilter
from time import time

#Generic node object that retains all attributes in k/v dictionary. Keys are 
#read from the initial node line. Edges are stored similarly

#Two functions, one to store gdf file in graph format, the other to convert
#a weighted graph into an approximate unweighted graph. This second function
#can be passed a function pointer to populate newly generated node's attributes
#The default function just copies the keys and sets the values to null

class Node:
    def __init__(self, name, attrib):
        self.name = name
        self.attrib = attrib
        
class Edge:
    def __init__(self, n1, n2, attrib):
        self.n1 = n1
        self.n2 = n2
        self.attrib = attrib

#Returns tuple contains dictionary of nodes and list of edges
def parseGDF(filename):
    f = open(filename, 'r')
    nodeDef = f.readline()  #Get node definition line
    if nodeDef[0:20] != 'nodedef>name VARCHAR': #Throw error if formatted incorrectly
        raise Exception("Invalid node template: " + nodeDef)
    nodeDefKeys = [x.split(' ')[-2] for x in nodeDef[8:].split(',')] #Extract list of attribute names
    nodes = []
    edges = []
    
    line = f.readline()
    while(line[0:8] != 'edgedef>'): #Parse all the nodes (see node class for format)
        attrib = line.split(",")
        if (len(attrib) != len(nodeDefKeys)):
            raise Exception("Invalid number of values: " + line)
        node = Node(attrib[0],dict(zip(nodeDefKeys[1:],attrib[1:])))            
        nodes.append(node)
        line = f.readline()
    
    edgeDef = line #Get edge definition line
    if edgeDef[0:35] not in ['edgedef>node1 VARCHAR, node2 VARCHAR', 'edgedef>node1 VARCHAR,node2 VARCHAR']:
        raise Exception("Invalid edge template: " + edgeDef[0:35])
    edgeDefKeys = [x.split(' ')[-2] for x in edgeDef[8:].split(',')]
    if "weight" not in edgeDefKeys:
        raise Exception("Graph already unweighted")

    line = f.readline()    
    while(line != ""): #Parse edges
        attrib = line.split(",")
        if (len(attrib) != len(edgeDefKeys)):
            raise Exception("Invalid number of values: " + line)
        edge = Edge(attrib[0], attrib[1], dict(zip(edgeDefKeys[2:],attrib[2:])))
        edges.append(edge)
        line = f.readline()
    
    f.close()        
    return (nodes,edges,nodeDef,edgeDef,nodeDefKeys,edgeDefKeys)
    
def saveGDF(filename, graph):
    f = open(filename, 'w')
    
    f.write(graph[2]) #Write node definition line
    for n in graph[0]: #Traverse through nodes. NOTE: this won't be in the order they were read
        f.write(n.name)   #Write name
        for k in graph[4][1:]:      #Write attributes using the nodeDefKeys list, so all node attribute print in same order
                f.write("," + n.attrib[k])
                
    f.write(graph[3]) #Write edge definition line
    for e in graph[1]:     #Traverse trough edges
        f.write(e.n1 + "," + e.n2)    #Write node1 and node2
        for k in graph[5][2:]:  #Traverse through edgeDefKeys
            f.write("," + e.attrib[k]) #Write attributes
        
    f.close()
    
def nullifier(e, graph, quanta):
    name = 0
    nullDict = {k:'' for k in graph[0][0].attrib}
    nullDict[graph[4][-1]]='\n'
    while(True):
        while str(name) in (n.name for n in graph[0]):
            name += 1
        yield Node(str(name),nullDict)
        name += 1
        
def distCenter(e, graph, quanta):
    name = 0
    n1 = next(ifilter(lambda n: n.name == e.n1, graph[0]),None)
    n2 = next(ifilter(lambda n: n.name == e.n2, graph[0]),None)
    try:
        startx = float(n1.attrib["x"])
        starty = float(n1.attrib["y"])
    except KeyError:
        print "No coordinate attributes found"
        raise
    diffx = float(n2.attrib["x"]) - startx
    diffy = float(n2.attrib["y"]) - starty
    segments = int(float(e.attrib["weight"])/quanta)
    diffx = diffx/segments
    diffy = diffy/segments
    nullDict = {k:"" for k in n1.attrib}
    nullDict[graph[4][-1]]='\n'
    for segment in range(1,segments):
        #Note that if the input dataset has consecutive integers sorted in
        ##decreasing order for node names, this will run VERY SLOWLY. Reccomend
        ##sorting nodes in ascending order if this is the case
        oldName = -1
        while oldName != name:
            oldName = name
            for n in graph[0]:
                if n.name == str(name):
                    name += 1
        
        node = Node(str(name),nullDict.copy())
        node.attrib["x"] = str(startx + segment*diffx)
        node.attrib["y"] = str(starty + segment*diffy)
        yield node
    
    
#Quantum is the minimum divisor to split edges. If quantum = 1, then edges with
#weight between 0 and 2 are untouched. Edges with weight 2-3 are split in 2,
#weight 3-4 are split in 3, etc. If youre edges have non-integer or large
#weights, try specifying quanta
#You can specify a function to generate nodes as edges are split. It must be
#implemented as a generator that takes an edge object. It must generate at
#least edgeweight/quanta nodes each with the same attributes keys as the
#argument nodes. By default, the function is nullifier, which returns a node
#with a unique integer for a name and null values in its attribute dictionary
#It msut also take the graph (in it's 6-element tuple form) and the quanta
#value
#To get node objects, use graph[0][e.n1] and graph[0][e.n2]
#Graph tuple formatted like:
#   (node dict, edge list, node header def, edge header def, node attrib list, edge attrib list)
def weighToUnweigh(graph,quanta=1,function=nullifier):
    newEdges = []
    newNodes = []
    for e in graph[1]:
        #print e.n1 + "->" + e.n2
        weight = float(e.attrib["weight"])
        if (weight/quanta < 2):
            e.attrib["weight"] = "1"
        else:
            gen = function(e,graph,quanta)
            prevNode = next(ifilter(lambda n: n.name == e.n1, graph[0]),None)
            for i in range(int(floor(weight/quanta)) - 1):
                nextNode = next(gen)   #Generate new node     
                #print nextNode.name + str(nextNode.attrib) 
                graph[0].append(nextNode)
                newEdge = Edge(prevNode.name, nextNode.name, e.attrib)
                newEdge.attrib["weight"]="1"
                newEdges.append(newEdge)
                prevNode = nextNode
            newEdge = Edge(prevNode.name, e.n2, e.attrib)
            newEdge.attrib["weight"]="1"
            newEdges.append(newEdge)
            
    #Remove all edges with a weight greater than 0 and replace with their divisions
    newEdges.extend(filter(lambda e: e.attrib["weight"] == "1", graph[1]))
    #print "Node 4126: " + str(next(ifilter(lambda n: n.name == "4126", graph[0]),None).attrib)

    return (graph[0], newEdges, graph[2], graph[3], graph[4], graph[5])
