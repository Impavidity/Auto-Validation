#Start of route comparison

#actualLocList = 

from util import *


def routeCompare(gMapRouteDict, actualLocList, actualTripTime): # an example of actualLocList = [(1.5,1.5),(2.5,2.5),(3.5,3.5),(4.5,4.5)] which is the actual detected locations of SENSg devices
    for actualCoordinates in actualLocList:

        for walkingRoute in gMapRouteDict["Walking"]:

            for coordinates in walkingRoute:

                dist = great_circle_dist(actualCoordinates, coordinates)






