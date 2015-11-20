# -*- coding: utf-8 *-*
import googlemaps
import json
from datetime import datetime,date,time
from decodeMapPolyline import *
import xlrd
from colored import bg,fg,attr
import pygmaps
import os


class Step(object):
    '''This is the class for saving steps'''
    def __init__(self, step_dict):
        self.step_dict  = step_dict
        self.distance = None
        self.travel_mode = None
        self.start_location = None
        self.end_location = None
        self.polyline = None
        self.duration = None
        self.vehicle = None
        self.departure_stop = None
        self.arrival_stop = None
        self.short_name = None
        self.parse()


    def parse(self):
        '''parse the step information'''
        try:
            self.distance = self.step_dict["distance"]["value"]
            self.duration = self.step_dict["duration"]["value"]
            self.start_location = self.step_dict["start_location"]
            self.end_location = self.step_dict["end_location"]
            self.travel_mode = self.step_dict["travel_mode"]
            self.polyline = decode(self.step_dict["polyline"]["points"])
            if "transit_details" in self.step_dict:
                self.vehicle = self.step_dict["transit_details"]["line"]["vehicle"]["type"]
                self.short_name = self.step_dict["transit_details"]["line"]["short_name"]
                # the format of bus stop
                # {"location": {"lat":1.3, "lng": 103.9}, "name": "Opp"}
                self.departure_stop = self.step_dict["transit_details"]["departure_stop"]
                self.arrival_stop = self.step_dict["transit_details"]["arrival_stop"]
        except Exception, error:
            print ("%s%s[PARSE]%s" % (fg(1), bg(15), attr(0))), "Parse error:",error


class RouteInfo(object):
    '''This is the class for saving route information'''
    def __init__(self, route_info_dict):
        self.route_info_dict = route_info_dict
        self.overview_polyline = None
        self.distance = None
        self.duration = None
        self.start_location = None
        self.end_location = None
        self.steps = []
        self.parse()

    def parse(self):
        '''parse the route information'''
        try:
            self.overview_polyline = decode(
                self.route_info_dict["overview_polyline"]["points"])
            # If there is no waypoint when you query
            # there will be only one leg in legs
            # we assume that we do not give waypoints when we query
            # If you need, please motify the query and the code here
            leg = self.route_info_dict["legs"][0]
            # distance unit meter
            self.distance = leg["distance"]["value"]
            # duration unit second
            self.duration = leg["duration"]["value"]
            # location format
            # {"lat": 1.3289998, "lng": 103.940036}
            self.start_location = leg["start_location"]
            self.end_location = leg["end_location"]
            for step_dict in leg["steps"]:
                step = Step(step_dict)
                self.steps.append(step)
        except Exception, error:
            print ("%s%s[PARSE]%s" % (fg(1), bg(15), attr(0))), "Parse error", error





class MapInfo(object):
    '''This is the class for get google map API'''
    def __init__(self, ID, origin, destin, key="AIzaSyAL7sZ6Ctqk71mZxiDPDjurdWtMCln3lyo"):
        '''
        You need an API key to access the API
        For more information, please refer to Google Development
        '''
        self.ID = ID
        self.origin = origin
        self.destin = destin
        self.gmaps = googlemaps.Client(key, queries_per_second=10)
        d = date(2015,12,15)
        t = time(12,30)
        self.time = datetime.combine(d,t)
        self.transit_routes = []
        self.driving_routes = []
        self.walking_routes = []

    def get_info(self, mode):
        '''
        Please set the origin and the destination.
        You can use the lat/lon or address.
        The mode can be set as "transit", "driving" and "walking"
        The time is set as 2015/12/15 12:30:00
        alternatives = True
        '''
        try:
            if not os.path.exists("data"):
                os.makedirs("data")
            if not os.path.exists("data/"+self.ID):
                os.makedirs("data/"+self.ID)
            if not os.path.exists("data/"+self.ID+"/"+mode):
                file_write = open("data/"+self.ID+"/"+mode, "w")
                directions_result = self.gmaps.directions(self.origin,
                                    self.destin,
                                    mode=mode,
                                    departure_time=self.time,
                                    alternatives=True)
                file_write.write(json.dumps(directions_result,indent=4))
            else:
                print ("%s%s[FILE]%s" % (fg(1), bg(15), attr(0))), "Reading json data from file now ..."
                with open("data/"+self.ID+"/"+mode) as file_read:
                    directions_result = json.load(file_read)
                print ("%s%s[FILE]%s" % (fg(1), bg(15), attr(0))), "Reading json data from file finished"
            return directions_result
        except IOError, error:
            print ("%s%s[FILE]%s" % (fg(15), bg(1), attr(0))), "Load data from file error:", error
        except Exception, error:
            print ("%s%s[API]%s" % (fg(15), bg(1), attr(0))), "Get data from API error:", error

    def get_transit_mode_route(self):
        query_result = self.get_info("transit")
        if not query_result:
            print ("%s%s[API]%s" % (fg(15), bg(1), attr(0))), "Get transit data failed"
            print "ID:", self.ID
        for route_dict in query_result:
            route = RouteInfo(route_dict)
            self.transit_routes.append(route)
        return self.transit_routes

    def get_driving_mode_route(self):
        query_result = self.get_info("driving")
        if not query_result:
            print ("%s%s[API]%s" % (fg(15), bg(1), attr(0))), "Get driving data failed"
            print "ID:", self.ID
        for route_dict in query_result:
            route = RouteInfo(route_dict)
            self.driving_routes.append(route)
        return self.driving_routes

    def get_walking_mode_route(self):
        query_result = self.get_info("walking")
        if not query_result:
            print ("%s%s[API]%s" % (fg(15), bg(1), attr(0))), "Get walking data failed"
            print "ID:", self.ID
        for route_dict in query_result:
            route = RouteInfo(route_dict)
            self.walking_routes.append(route)
        return self.walking_routes


def read_file(file_name):
    try:
        print ("%s%s[FILE]%s" % (fg(1), bg(15), attr(0))), "Reading file now ..."
        data = xlrd.open_workbook(file_name)
        table = data.sheets()[0]
        num = table.nrows - 1
        ID = [str(int(item)) for item in table.col_values(0)[1:]]
        home_lat = table.col_values(2)[1:]
        home_lon = table.col_values(3)[1:]
        school_lat = table.col_values(4)[1:]
        school_lon = table.col_values(5)[1:]
        if len(ID) == len(home_lat) == len(home_lon) \
            == len(school_lat) == len(school_lon) == num:
            print ("%s%s[FILE]%s" % (fg(1), bg(15), attr(0))), "Read file successfully"
        else:
            print ("%s%s[FILE]%s" % (fg(15), bg(1), attr(0))),"File length error"
        node = []
        for i in range(num):
            node.append({ID[i]:[str(home_lat[i])+","+str(home_lon[i]), str(school_lat[i])+","+str(home_lon[i])]})
        return node
    except IOError, error:
        print ("%s%s[FILE]%s" % (fg(15), bg(1), attr(0))), "File IO error", error
 


def main():
    node =read_file("picked_data_analysed_01_Nov_2015.xlsx")
    nodeID = node[0].keys()[0]
    print "[QUERY] Node ID :", nodeID
    origin = node[0].values()[0][0]
    destin = node[0].values()[0][1]
    model = MapInfo(nodeID, origin, destin)
    routes = model.get_walking_mode_route()
    maps = pygmaps.maps(0,0,4)
    
    for route in routes:
        print route.start_location
        print route.end_location
        print route.duration
        print route.distance
        print route.overview_polyline
        for step in route.steps:
            print "    ",step.start_location
            print "    ",step.end_location
            print "    ",step.duration
            print "    ",step.distance
            print "    ",step.polyline
            print "    ",step.travel_mode
    routes = model.get_driving_mode_route()
    for route in routes:
        print route.start_location
        print route.end_location
        print route.duration
        print route.distance
        print route.overview_polyline
        for step in route.steps:
            print "    ",step.start_location
            print "    ",step.end_location
            print "    ",step.duration
            print "    ",step.distance
            print "    ",step.polyline
            print "    ",step.travel_mode
    routes = model.get_transit_mode_route()
    for route in routes:
        print route.start_location
        print route.end_location
        print route.duration
        print route.distance
        print route.overview_polyline
        for step in route.steps:
            print "    ",step.start_location
            print "    ",step.end_location
            print "    ",step.duration
            print "    ",step.distance
            print "    ",step.polyline
            print "    ",step.travel_mode
            print "    ",step.vehicle
            print "    ",step.departure_stop
            print "    ",step.arrival_stop
            print "    ",step.short_name 
        maps.addpath(route.overview_polyline,"#00FF00")
        break
    maps.draw('./mymap.html')

if __name__=="__main__":
    main()