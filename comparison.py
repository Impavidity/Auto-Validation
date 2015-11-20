'''This is the comparison algorithm'''
# -*- coding: utf-8 *-*
from GetDataFromGoogleAPI import *
from NSE_Analytics_for_validation.util import great_circle_dist

class Comparison(object):
	'''This is the class for routes comparison'''
	def __init__(self, ID, origin, destin):
		self.ID = ID
		self.origin = origin
		self.destin = destin
		self.confidence = {}


	def confidence_calc(self, myroute, googleroute):
		dist = []
		for point1 in myroute:
			dist_min = float('inf')
			for point2 in googleroute:
				current_dist = great_circle_dist(point1, point2)
				if dist_min > current_dist:
					dist_min = current_dist
			dist.append(dist_min)
		ave = float(sum(dist))/len(dist)
		return ave



	def comparison(self):
		'''Compare the route of Driving, Walking, Transit'''
		gold_route = []
		map_instance = MapInfo(self.ID, self.origin, self.destin)
		routes = map_instance.get_walking_mode_route()
		self.confidence["WALKING"] = []
		for route in routes:
			conf = self.confidence_calc(route.overview_polyline,route.overview_polyline) 
			self.confidence["WALKING"].append(conf)
		print self.confidence["WALKING"]
		routes = map_instance.get_driving_mode_route()
		self.confidence["DRIVING"] = []
		for route in routes:
			conf = self.confidence_calc(route.overview_polyline,route.overview_polyline)
			self.confidence["DRIVING"].append(conf)
		print self.confidence["DRIVING"]
		routes = map_instance.get_transit_mode_route()
		self.confidence["TRANSIT"] = []
		for route in routes:
			conf = self.confidence_calc(route.overview_polyline,route.overview_polyline)
			self.confidence["TRANSIT"].append(conf)
		print self.confidence["TRANSIT"]

def main():
	comparison = Comparison("400002","1.3166,103.9449","1.3291,103.9416")
	comparison.comparison()


if __name__=="__main__":
	main()

