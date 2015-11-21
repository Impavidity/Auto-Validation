import psycopg2
import time
from datetime import datetime

conn = None



def connect2database():
	path = []
	try:
		conn=psycopg2.connect("dbname='nse' user='postgres' password='Pa8LpCxW' host='54.179.172.158'")
		print "Connected"
		cur = conn.cursor()
		cur.execute("Select * FROM week1_new LIMIT 0")
		colnames = [desc[0] for desc in cur.description]
		print colnames
		cur.execute("Select * FROM week1_new where nid=400002 AND (ts < '2015-09-29 00:00:00' AND ts >= '2015-09-28 00:00:00')")
		result = cur.fetchall()
		for line in result:
			if line[13]!=92.0 and line[14]!=182.0:
				path.append((line[13],line[14]))
		'''
		for coor in path:
			print coor
		'''
	except Exception,error:
		print "Connect faild:",error
	finally:
		return path

if __name__=="__main__":
	connect2database()