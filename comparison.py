'''This is the comparison algorithm'''
# -*- coding: utf-8 *-*
from GetDataFromGoogleAPI import *
from NSE_Analytics_for_validation.util import great_circle_dist
from resample import *
import pygmaps
import math
import os

class Comparison(object):
	'''This is the class for routes comparison'''
	def __init__(self, ID, origin, destin, gold_route, distance, duration, mode, current_date):
		self.ID = ID
		self.origin = origin
		self.destin = destin
		self.confidence = {}
		self.maps = pygmaps.maps(0,0,4)
		self.maps_for_report = None
		self.path_vis = []
		self.gold_route = gold_route
		self.distance = distance[0]
		self.duration = duration[0]
		self.sorted_result = None
		self.mode = mode
		self.date = current_date

	def confidence_calc(self, myroute, googleroute):
		'''
		confidence calculation
		return the average distance
		'''
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
		gold_route = self.gold_route
		# Resample the gold route
		#sample = Resample(gold_route, 100)
		#gold_route = sample.parse()

		# visualization for the gold route
		# color green
		self.visualization_for_point(gold_route, "#00FF00")
		
		# get information from Google API
		map_instance = MapInfo(self.ID, self.origin, self.destin)
		
		# get the walking route
		# color red
		routes = map_instance.get_walking_mode_route()
		self.confidence["WALKING"] = []
		for route in routes:
			conf = self.confidence_calc(gold_route,route.overview_polyline)
			self.visualization(route.overview_polyline, "#FF0000")
			self.confidence["WALKING"].append({"dis":conf,"route":route})
		print self.confidence["WALKING"]

		# get the driving route
		# color blue
		routes = map_instance.get_driving_mode_route()
		self.confidence["DRIVING"] = []
		for route in routes:
			conf = self.confidence_calc(gold_route,route.overview_polyline)
			self.visualization(route.overview_polyline, "#0000FF")
			self.confidence["DRIVING"].append({"dis":conf,"route":route})
		print self.confidence["DRIVING"]

		# get the transit route
		# color black
		routes = map_instance.get_transit_mode_route()
		self.confidence["TRANSIT"] = []
		for route in routes:
			conf = self.confidence_calc(gold_route,route.overview_polyline)
			self.visualization(route.overview_polyline, "#111111")
			self.confidence["TRANSIT"].append({"dis":conf,"route":route})
		print self.confidence["TRANSIT"]

		result_list = self.confidence["WALKING"] + self.confidence["DRIVING"] + \
				self.confidence["TRANSIT"]
		# sort the result by distance
		self.sorted_result = sorted(result_list, key=lambda k: k["dis"])

		# decide true or false and return the parameter
		return self.decisition_tree(self.sorted_result)

	def decisition_tree(self, result):
		print result[0]["route"].query_mode
		if result[0]["route"].query_mode == "walking":
			# walking
			if all(3 == item for item in self.mode):
				'''
				if not os.path.exists("map"):
					os.makedirs("map")
				self.maps_for_report = pygmaps.maps(0,0,4)
				self.maps_for_report.addpath(result[0]["route"].overview_polyline)
				.draw('map/'+self.ID+'_'+str(self.date)+'_report.html')
				'''
				return {"result":True, 
						"mode": "walking",
						"predict": self.mode,
						"dist_diff":result[0]['dis'], 
						"dura_diff":abs(result[0]["route"].duration-self.duration)}
			else:
				return {"result":False, 
						"mode": "walking",
						"predict": self.mode,
						"dist_diff":result[0]['dis'], 
						"dura_diff":abs(result[0]["route"].duration-self.duration)}

		if result[0]["route"].query_mode == "driving":
			# driving
			if any(6 == item for item in self.mode):
				'''
				if not os.path.exists("map"):
					os.makedirs("map")
				self.maps.draw('map/'+self.ID+'_'+str(self.date)+'_report.html')
				'''
				return {"result":True, 
						"mode": "driving",
						"predict": self.mode,
						"dist_diff":result[0]['dis'], 
						"dura_diff":abs(result[0]["route"].duration-self.duration)}
			else:
				return {"result":False, 
						"mode": "driving",
						"predict": self.mode,
						"dist_diff":result[0]['dis'], 
						"dura_diff":abs(result[0]["route"].duration-self.duration)}

		if result[0]["route"].query_mode == "transit":
			# Bus only
			if any(5 == item for item in self.mode) and \
					not any(4 == item for item in self.mode):
				if any("BUS" == item.vehicle for item in result[0]["route"].steps) and \
						not any("SUBWAY" == item.vehicle for item in result[0]["route"].steps):
					return {"result":True,
							"mode": "bus",
							"predict": self.mode,
							"dist_diff":result[0]['dis'],
							"dura_diff":abs(result[0]["route"].duration-self.duration)}
			# subway only
			if any(4 == item for item in self.mode) and \
					not any(5 == item for item in self.mode):
				if any("SUBWAY" == item.vehicle for item in result[0]["route"].steps) and \
						not any("BUS" == item.vehicle for item in result[0]["route"].steps):
					return {"result":True,
							"mode":"subway",
							"predict": self.mode,
							"dist_diff":result[0]['dis'],
							"dura_diff":abs(result[0]["route"].duration-self.duration)}

			# subway and bus
			else:
				return {"result":False,
						"mode": "BUS SUBWAY",
						"predict": self.mode,
						"dist_diff":result[0]['dis'],
						"dura_diff":abs(result[0]["route"].duration-self.duration)}



	def visualization_for_point(self, point_list, color):
		'''For gold route visualization'''
		points = point_list + []
		for point in points:
			self.maps.addpoint(point[0],point[1],color)

	def visualization(self,path, color):
		'''For google API route visualization'''
		self.path_vis = path + []
		self.maps.addpath(self.path_vis,color)

	def export_map(self):
		'''export the map'''
		if not os.path.exists("map"):
			os.makedirs("map")
		self.maps.draw('map/'+self.ID+'_'+str(self.date)+'.html')

