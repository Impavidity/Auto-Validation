#Start of route comparison

#actualLocList = 


def routeCompare(gMapRouteDict, actualLocList, actualTripTime): # an example of actualLocList = [(1.5,1.5),(2.5,2.5),(3.5,3.5),(4.5,4.5)] which is the actual detected locations of SENSg devices
    for travelMode in gMapRouteDict:

        for route in travelMode:

            for latlonPair in actualLocList:

                for step

                great_circle_dist(latlonPair, b)

                #find min distance between lat lng pair and points on google routes






if __name__=="__main__":
    #main()
    gMapRouteList = main()
    actualLocList = actualRoute = [(1.5,1.5),(2.5,2.5),(3.5,3.5),(4.5,4.5)]
    actualTripTime = 600 #inseconds


    confidence = routeCompare(gMapRouteList, actualLocList, actualTripTime)
    print confidence