# -*- coding: utf-8 -*-
# OSM to GDF conversion script

#Bugs:
# Generates parallel edges
# Node 158038553 is removed when it shouldn't be. Fixing this should fix similar cases

#Todo:
# Implement filtering where if node only has 2 edges both with same street name, merge them

from imposm.parser import OSMParser
import posixpath
import math
import shapegeocode   #Requires pyshp as import
from timeit import default_timer as timer
import sys
reload(sys)
sys.setdefaultencoding('utf8')


#Specially adapted for this circumstance, but also compatible with general
#edge-vertex implementations of graphs
class Node:
    def __init__(self, ref, lon=0, lat=0, city="null", waysnum=1):
        self.ways = waysnum
        self.ref = ref #id is a keyword :/
        self.lon = lon
        self.lat = lat
        self.city = city
        self.edges = []
        self.valid = True   #For BFS
        self.end = False
    def addWay(self):
        self.ways += 1
    def connectEdge(self, edgeNum):
        self.edges.append(edgeNum)

#Edge data type for graph          
class Edge:
    def __init__(self, n1ref, n2ref, weight, street="null"):
        self.n1 = n1ref     #Holds the ref number of a node instead of the
        self.n2 = n2ref     #actual reference, reducing the recursion depth
        self.weight = weight
        self.street = street
        self.valid = True   #For BFS and correcting segmented highways
    def setStreet(self, street):
        self.street = street
    def getPair(self, nodeRef):
        if nodeRef == self.n1:
            return self.n2
        elif nodeRef== self.n2:
            return self.n1
        else:
            return None
        
#Returns true if elem is a way and not a walkway, waterway, etc#This is a wrapper class for a dictionary of ways and nodes. Implementing it
#this way allows getWays, getCoords, and geocode to be used as callback functions
#and still access theses dictionaries
class Elems:
    ways = []
    nodes = {}
    whitelist = set(('highway', 'ref', 'name', 'access'))
    blacklist = ('bus_guideway', 'raceway', 'footway', 'bridleway', 'steps', 'path', 'track')

    def getWays(self, parsedWays):
        for way in parsedWays:
            if self.isRoad(way):
                way[1].clear()
                self.ways.append(way)
                for ref in way[2]:
                    if not ref in self.nodes:
                        self.nodes[ref] = Node(ref)
                    else:
                        self.nodes[ref].addWay() #Increment way count
                self.nodes[way[2][0]].end = True
                self.nodes[way[2][-1]].end = True
            
    def tag_filter(tags):
      for key in tags.keys():
        if key not in whitelist:
          del tags[key]
      
    def getCoords(self, coords):
        for c in filter(lambda c: c[0] in self.nodes, coords):
            n = self.nodes[c[0]]  #c[0] holds the node ID of the coordinate
            n.lon = c[1]
            n.lat = c[2]
            
    def getNodes(self, nodes):
        for n in nodes:
            if n[0] in self.nodes:
                self.nodes[n[0]] = Node(n[0], n[2][0], n[2][1])
                
    
    def geocode(self, geocoder):
        for k in self.nodes:
            n = self.nodes[k]
            try:
                n.city = geocoder.geocode(n.lat, n.lon)['NAME']
            except:
                n.city = 'null'
      
    def getStreetName(self, way):
        try:
            return way[1]['ref']
        except KeyError:
            try:
                return way[1]['name']
            except KeyError:
                return 'null'
        except TypeError: #DEBUGGING
            print way  #DEBUGGING
            input("Done looking?")  #DEBUGGING
            
    def isRoad(self, elem):
        #If it's a road, but not the ignorable roads and not a private way, return true
        return 'highway' in elem[1] and elem[1]['highway'] not in self.blacklist and not ('access' in elem[1] and elem[1]['access'] == 'private')
    
#Returns the geographic distance betweeen 2 nodes. Instead of using the Orthodomic
#distance formula, it uses the computationally less complex Pythagorean theorem,
#a satisfactory approximation over short distances. Returns distance in km
def orthoDist(n1, n2):   
    dx = n1.lon - n2.lon
    dy = n1.lat - n2.lat
    dr = math.sqrt(dx**2 + dy**2)
    
    #Difference in degrees converted to radians and multiplied by earth's radius
    return dr * math.pi * 35.394 


##Start of program-------------------------------------------------------------

##Get filename
valid = False
while not valid:
    filename = raw_input("Enter input filename: ")
    if(posixpath.isfile(filename)):
        valid = True
    else:
        print "Please enter valid file"
edges = []
elems = Elems()
   
#This generates an initial list of streets as well as the nodes on them
print "Getting original list of ways"  #DEBUGGING
start = timer()  #DEBUGGING
p = OSMParser(concurrency=4, ways_callback=elems.getWays)
p.parse(filename)
end = timer()  #DEBUGGING
print "Time: " + str(end - start)  #DEBUGGING
     
#This fetches the coordinates of each node
print "Getting coordinates of nodes"  #DEBUGGING
start = timer()  #DEBUGGING
p = OSMParser(concurrency=2, coords_callback=elems.getCoords)
p.parse(filename)    
end = timer()  #DEBUGGING
print "Time: " + str(end - start)  #DEBUGGING

#This will find the nodes that are intersections/deadends and create edges
##TODO: Rewrite this loop to account for the new imposm objects
print "Finding intersections"  #DEBUGGING
start = timer()  #DEBUGGING
rem = []
while len(elems.ways) > 0:  
    way = elems.ways.pop()
    
    #Keep track of the last point in the way (lastPoint) and the last intersection (lastInter)
    lastInter = elems.nodes[way[2][0]]
    lastPoint = lastInter
    distance = 0
    street = elems.getStreetName(way)
    
    #Iterate through the ref numbers of the nodes on way
    children = way[2]
        
    
    for ref in children[1:-1]:
        if ref != lastPoint.ref:    #Sometimes the way will list duplicate nodes. This is a problem
            
            #Find the node object corresponding to the ref number
            n = elems.nodes[ref]
            #Follow along the street and add up the distance until the next intersection        
            distance += orthoDist(lastPoint, n)
            
            #Sometimes an way loops back on itself and creates redundant edges.
            #The big-ass filter(lambda) thing check to see if a similar edge has already been created
            #If an intersection, create edge. Unless that edge is redundant (thats what the filter-lambda thing checks)
            edgeExists = lambda x, yref: len(filter(lambda e: edges[e].getPair(x.ref) == yref, x.edges)) > 0 #TODO: Implement this
            if n.ways > 1 and not edgeExists(lastInter,n.ref): #If an intersection, create edge. Unless that edge is redundant
                e = Edge(lastInter.ref, n.ref, distance, street)
                edges.append(e)
                lastInter.connectEdge(len(edges)-1) #POTENTIALBUG: Parallelizing can cause problems with this
                n.connectEdge(len(edges)-1)
            
                lastInter = n
                distance = 0
            elif not edgeExists(lastInter, n.ref) and n.ways == 1:  #If it's not an intersection, mark the id for removal,
                rem.append(ref)   #unless we're skipping it because of edge redundancy
                
            lastPoint = n
        
    #The last node is either a deadend or a T-intersection. Either way, add it. Also, check for edge redundancy
    if children[-1] != lastPoint.ref or edgeExists(lastInter,children[-1]):
        distance += orthoDist(lastPoint, elems.nodes[children[-1]])
        e = Edge(lastInter.ref, children[-1], distance, street)
        edges.append(e)    
        lastInter.connectEdge(len(edges)-1)
        elems.nodes[children[-1]].connectEdge(len(edges)-1)
        
for n in rem:
    del elems.nodes[n]
rem = []
end = timer()  #DEBUGGING
print "Time: " + str(end - start)  #DEBUGGING

rem = []
print "Concatenating segmented highways"  #DEBUGGING
start = timer()  #DEBUGGING
for k in filter(lambda k: len(elems.nodes[k].edges) == 2, elems.nodes):
    node = elems.nodes[k]   #This is a node object
    e1 = node.edges[0]      #These are ref numbers, not edge objects
    e2 = node.edges[1]
    if edges[e1].street == edges[e2].street: #If a node is connected to only 2 edges that are the same street,
        n1 = edges[e1].getPair(node.ref)   #These are ref numbers
        n2 = edges[e2].getPair(node.ref)
        newEdge = Edge(n1, n2, edges[e1].weight + edges[e2].weight, edges[e1].street)
        edges.append(newEdge)       #Add new edges
        edges[e1].valid = False            #Invalidate other edges
        edges[e2].valid = False
        #Replace references to e1 and e2 in n1 and n2 both to newEdge
        elems.nodes[n1].edges = [len(edges)-1 if x==e1 else x for x in elems.nodes[n1].edges]
        elems.nodes[n2].edges = [len(edges)-1 if x==e2 else x for x in elems.nodes[n2].edges]
        rem.append(node.ref)    #Cut out the middleman
for n in rem:
    del elems.nodes[n]
del rem
end = timer() #DEBUGGING
print "Time: " + str(end - start) #DEBUGGING

##Get central node
#print "This script sometimes generates groups of back country roads that are"
#print "disconnected from the rest of the road network. To counteract this, a"
#print "breadth-first-search is performed starting at a central node to check"
#print "the validity of every node in the graph. Please study the database and"
print "specify this central node, or to leave disjointed groups, enter 0, to"
centralNode = int(raw_input("guess, enter 1 Lombard is 65362185: "))
#65362185 is Lombard and Leavenworth

print "Filtering out rouge street groups"   #DEBUGGING
start = timer()  #DEBUGGING
if centralNode != 0:
    for k in elems.nodes:
        elems.nodes[k].valid = False
    for e in edges:
        e.valid = False
    
    if centralNode == 1:
        centralNode = elems.nodes.keys()[0]
    q = [centralNode]
    while len(q) > 0:
        current = q.pop()
        elems.nodes[current].valid = True
        for e in elems.nodes[current].edges:
            if not edges[e].valid:
                edges[e].valid = True
                pair = edges[e].getPair(current)
                elems.nodes[pair].valid = True
                q.append(pair)
                
end = timer()  #DEBUGGING
print "Time: " + str(end - start)   #DEBUGGING

print "Geocoding"  #DEBUGGING
start = timer()  #DEBUGGING
gc = shapegeocode.geocoder("./SHP/tl_2013_06_place.shp") #USER: Edit shapefile name here
elems.geocode(gc)
end = timer()  #DEBUGGING
print "Time: " + str(end - start)  #DEBUGGING

##DEBUGGING
#for n in map(lambda k: elems.nodes[k], elems.nodes):
#    invalidEdges = len(filter(lambda e: not edges[e].valid, n.edges))
#    if invalidEdges > 0:
#        print "Node " + n.ref + " connected to " + invalidEdges + " invalidEdges"
    

##Get filename    
valid = False
while not valid:
    filename = raw_input("Enter output filename: ")
    if(posixpath.isfile(filename)):
        reply = raw_input("File exists. Overwrite? (y or n)")
        while (reply != 'y') and (reply != 'n'):
            reply = raw_input("(y or n)")
        if reply == 'y':
            valid = True
    else:
        valid = True
  
print "Edges: " + str(len(filter(lambda e: e.valid, edges)))
print "Nodes: " + str(len(filter(lambda n: elems.nodes[n].valid, elems.nodes)))
        
f = open(filename, 'wb')
f.write("nodedef>name VARCHAR,x DOUBLE,y DOUBLE,city VARCHAR\n")
for n in filter(lambda n: n.valid, map(lambda k: elems.nodes[k], elems.nodes)):
    try:
        f.write(str(n.ref) + "," + str(n.lon) + "," + str(n.lat) + "," + n.city + "\n")
    except:
        print "Exception Occured"
	print 'ref: ' + str(n.ref)
        print 'city: ' + str(n.city)
	print 'lon, lat: ' + str(n.lon) + "," + str(n.lat)
        raise
    
f.write("edgedef>node1 VARCHAR,node2 VARCHAR,weight DOUBLE,directed BOOLEAN,street VARCHAR\n")
for e in filter(lambda e: e.valid, edges):
    try:
        f.write(str(e.n1) + "," + str(e.n2) + "," + str(e.weight) + ",false," + e.street.replace(',','') + "\n")
    except:
        print "Exception Occured."
	print "ref n1: " + str(n1.ref)
	print 'ref n2: ' + str(e.n2.ref)
        print 'street: ' + str(e.street)
	raise
    
f.close()

print "Done"
