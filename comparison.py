'''This is the comparison algorithm'''
# -*- coding: utf-8 *-*
from GetDataFromGoogleAPI import *
from NSE_Analytics_for_validation.util import great_circle_dist
from databaseAccess import *
from resample import *
import pygmaps

class Comparison(object):
	'''This is the class for routes comparison'''
	def __init__(self, ID, origin, destin):
		self.ID = ID
		self.origin = origin
		self.destin = destin
		self.confidence = {}
		self.maps = pygmaps.maps(0,0,4)
		self.path_vis = []


	def confidence_calc(self, myroute, googleroute):
		dist = []
		for point1 in myroute:
			dist_min = float('inf')
			for point2 in googleroute:
				current_dist = great_circle_dist(point1, point2, unit="meters")
				if dist_min > current_dist:
					dist_min = current_dist
			dist.append(dist_min)
		ave = float(sum(dist))/len(dist)
		return ave



	def comparison(self):
		'''Compare the route of Driving, Walking, Transit'''
		gold_route = []
		gold_route = connect2database()
		sample = Resample(gold_route, 100)
		gold_route = sample.parse()
		self.visualization_for_point(gold_route, "#00FF00")
		map_instance = MapInfo(self.ID, self.origin, self.destin)
		routes = map_instance.get_walking_mode_route()
		self.confidence["WALKING"] = []
		for route in routes:
			conf = self.confidence_calc(gold_route,route.overview_polyline)
			self.visualization(route.overview_polyline, "#FF0000")
			self.confidence["WALKING"].append(conf)
		print self.confidence["WALKING"]
		routes = map_instance.get_driving_mode_route()
		self.confidence["DRIVING"] = []
		for route in routes:
			conf = self.confidence_calc(gold_route,route.overview_polyline)
			self.visualization(route.overview_polyline, "#0000FF")
			self.confidence["DRIVING"].append(conf)
		print self.confidence["DRIVING"]
		routes = map_instance.get_transit_mode_route()
		self.confidence["TRANSIT"] = []
		for route in routes:
			conf = self.confidence_calc(gold_route,route.overview_polyline)
			self.visualization(route.overview_polyline, "#111111")
			self.confidence["TRANSIT"].append(conf)
		print self.confidence["TRANSIT"]

	def visualization_for_point(self, point_list, color):
		points = point_list + []
		for point in points:
			self.maps.addpoint(point[0],point[1],color)

	def visualization(self,path, color):
		self.path_vis = path + []
		self.maps.addpath(self.path_vis,color)

	def export_map(self):
		self.maps.draw('./400002.html')
		

def main():
	comparison = Comparison("400002","1.3482,103.8532","1.3646,103.834")
	comparison.comparison()
	comparison.export_map()


if __name__=="__main__":
	main()

