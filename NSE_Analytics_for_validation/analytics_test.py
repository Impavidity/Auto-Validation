"""Main test script for the analytics functions with given parameters.

Usage: analytics_test.py

"""
import requests
import logging
import sys
import pandas as pd
import numpy as np
import os
import sys
import base64
import datetime
import calendar

import process
from util import great_circle_dist




def getGroundTruthTrips(url, nid, table):
    """Retrieve ground truth trips for device nid for the specified table.
    Return a pandas data frame of trip informations.

    """
    payload = {'nid' : nid, 'table': table}
    req = requests.get("%s/getgroundtruth" % url, params=payload)
    logging.debug("getGroundTruthTrips url: %s" % str(req.url))
    if req.status_code != requests.codes.ok:
        raise Exception("getGroundTruthTrips returned http status %d" % req.status_code)
    resp = req.json()
    if not resp["success"]:
        raise Exception("getGroundTruthTrips returned error message %s" % resp["error"])
    data_frame = pd.DataFrame(resp["data"])
    return data_frame


def main():
    # create logger to save
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    ## parameters
    #API to call
    url="https://data.nse.sg"
    nse_directory = os.path.dirname(os.path.realpath(__file__))
    #device_file="%s/nse1_devices_short.csv" % nse_directory  # for 90000X data - synthetic
    #device_file="%s/pilot2_devices.csv" % nse_directory  # for pilot 2
    device_file="%s/test_devices.csv" % nse_directory  # for pilot 3
    # API for ground truth
    gt_url="http://54.251.119.96:3000"

    #current_date="2015-08-10" # for 90000X data - synthetic
    #current_date="2015-07-10" # for pilot 2
    current_date="2015-11-04" # for pilot 3
    # determine which date to process data for which is two days before the current date
    analysis_date_tuple = datetime.datetime.strptime(current_date, "%Y-%m-%d") - datetime.timedelta(days=1)
    analysis_date =  analysis_date_tuple.strftime("%Y-%m-%d")
    # convert analysis_date into unix timestamp in UTC time
    analysis_unix = calendar.timegm(analysis_date_tuple.timetuple())
    start_get = int(process.getFirstSecondOfDay(analysis_unix)) #first second of the analysis day
    end_get = int(start_get+24*3600-1) #last second of the analysis day

    # database table for the test API. If the table attribute is None,
    # the parameter will not be included in the REST call
    # can be two different tables depending on the test scenario
    #ground_truth_trips_table="IHPC_server_test_nodes"  # for 90000X data - synthetic
    #ground_truth_trips_table="new_pilot2" # for pilot 2
    ground_truth_trips_table="new_pilot3" # for pilot 3

    # Compare with ground truth
    # load list of device IDs from file
    logging.info("Load device IDs")
    try:
        with open(device_file, 'r') as csvfile:
            devices = [ int(line.strip()) for line in csvfile if line.strip() ]
    except IOError as e:
        logging.error("Failed to load device IDs: %s" %  e.strerror)
        sys.exit(10)

    #reset the analysis status of the devices to 0
#    for nid in devices:
#        logging.info("Clearing data for: %s" % analysis_date)
#        process.setStatus(url, nid, analysis_date, 0)
#        if process.setStatus(url, nid, analysis_date, 0):
#            logging.info("SUCCESS in resetting process status for device: %s" % nid)
#        else:
#            logging.info("FAIL in resetting process status for device: %s" % nid)

    #return results from process
    results = process.main(url, device_file,
                           current_date=current_date, testing=True)

    # comparisons
    compare = 0
    if compare:
        for nid in devices:
            logging.info("Process device ID = %s" % nid)
            # retrieve unprocessed device data from the backend
            logging.info("Get ground truth data for device %s" % nid)
    
            # Get the ground truth table
            data_frame_GT = getGroundTruthTrips(gt_url, nid, table=ground_truth_trips_table)
    
            # Get the ground truth mode list from the table
            GTMODE_data_frame = process.getData(url, nid,start_get,end_get)
    
            #Compare identified and true home distance
            lat_home = results['Home'][(int(nid), analysis_date)][0] if results['Home'] and results['Home'].has_key((int(nid), analysis_date)) else None
            lon_home = results['Home'][(int(nid), analysis_date)][1] if results['Home'] and results['Home'].has_key((int(nid), analysis_date)) else None
            print "Home lat: "+str(lat_home)
            print "Home lon: "+str(lon_home)
            if lat_home is not None and lon_home is not None:
                delta_dist = great_circle_dist(data_frame_GT[['HOME_LAT', 'HOME_LON']].values[0,:], [lat_home,lon_home])
    
                print "Difference in distance between identified and ground truth home is: "
                print delta_dist
            else:
                print "Identification failed"
    
            #Compare identified and true home/school distance
            if lat_home is not None:
                lat_school = results['School'][(int(nid), analysis_date)][0] if results['School'] and results['School'].has_key((int(nid), analysis_date)) else None
                lon_school = results['School'][(int(nid), analysis_date)][1] if results['School'] and results['School'].has_key((int(nid), analysis_date)) else None
                print "School lat: "+str(lat_school)
                print "School lon: "+str(lon_school)
    
                ident_home_school_dist = great_circle_dist([lat_school, lon_school], [lat_home,lon_home])
                print "identified school distance  is: " +str(ident_home_school_dist)
                gt_home_school_dist = great_circle_dist(data_frame_GT[['HOME_LAT', 'HOME_LON']].values[0,:], data_frame_GT[['SC_LAT', 'SC_LON']].values[0,:])
                print "ground truth school distance  is: " +str(gt_home_school_dist)
    
                print "For the node " + str(nid)
                print "Absolute difference between identified and ground truth home/school distance is (meaning school is also accurate): "
                print abs(ident_home_school_dist-gt_home_school_dist)
    
            # Compare ground truth mode to predicted mode
            if results['Modes'].has_key((nid, analysis_date)):
                gt_modes = GTMODE_data_frame[['CMODE']].values[:,0]
                gt_modes_only = [x for x in gt_modes]
                ident_modes = results['Modes'][(nid, analysis_date)]      #this is ugly - there must be a better way
                ident_modes_only = [x[1] for x in ident_modes]  #this is ugly - there must be a better way
    
                equal_modes = np.equal(gt_modes_only, ident_modes_only)
                accuracy = float(sum(equal_modes))/len(equal_modes)
    
                print "The mode identification is accurate to this fraction: "
    
                print accuracy


if __name__ == "__main__":

    main()
