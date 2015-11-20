#!/usr/bin/env python

"""Main driver for the analytics functions. This script orchestrates
the process of retrieving the raw device data from the database, call
the mode prediction modules to improve the prediction, do trip
segmentation, and write the results back.

Usage: process.py --deviceIDs=DEVICEFILE [--current_date=DATE] [--verbose] URL

Arguments:
 URL            Base URL for the backend API, for example 'http://sensg.ddns.net/api/'

Options:
 --deviceIDs=DEVICEFILE    mandatory option with the filename with device IDs. Format is one ID per line.

 --current_date=DATE       option to specify today's date for test purposes (%Y-%m-%d), otherwise the local server time is used to determine the date. The data to be processed is 2 days before today's date

 --verbose       option to print verbose output for debugging

"""

import psycopg2
import requests
import json
import httplib
import time
import logging
import pandas as pd
import sys
import base64
import datetime
import traceback
from itertools import izip
import numpy as np
import calendar
import os
import timeit

import modeSmoother
import TransitHeuristic
import tripParse
from util import great_circle_dist, aveWithNan

API_key = "sutd-nse_api:dj6M9RAxynrjw9aWztzprfh5AKHssgVj4qKXiKSfHRyGKeoX92wmwmEJKpHMIB5"

def getDataIHPC(url, nid, start_time=0, end_time=int(time.time()), table=None):
    """Retrieve raw hardware data for device nid for the specified time
    frame and specified table if specified.  Return a pandas data frame of
    measurements or None if no data was returned.

    """
    # note: int 'ts' is added in order to work around API caching issue
    payload = {'nid' : nid, 'start' : start_time, 'end' : end_time, 'ts':int(time.time())}
    if table:
        payload['table'] = table

    header = {"Content-Type": "application/json", 'Authorization' : 'Basic %s' % base64.b64encode(API_key)}
    req = requests.get("%s/getdata" % url, params=payload, headers=header)
    logging.debug("getdata url: %s" % str(req.url))
    if req.status_code != requests.codes.ok:
        raise Exception("getData returned http status %d" % req.status_code)
    resp = req.json()
    # resp["success"] has type bool
    if resp["success"]:
        return pd.DataFrame(resp["data"])
    else:
        logging.warning("getData for " +str(nid) + " for end: " + str(end_time) + " returned %s" % resp["error"])
        return None

def getDataPostgres(tablename, nid, analysis_date, current_date):
    """ Retrieve raw hardware data for device nid for the specified time in the
        given data table in postgres DB
    """

    try:
        conn=psycopg2.connect("dbname='nse' user='postgres' password='Pa8LpCxW' host='54.179.172.158'")
        print "DB Connected"
        cur = conn.cursor()
    
    	allQuery = """SELECT * from """+tablename+""" WHERE nid="""+str(nid)+""" AND (ts>='"""+analysis_date+""" 00:00:00' AND ts<'"""+current_date+""" 00:00:00') """
    	cur.execute(allQuery)
        dataAll = cur.fetchall()
        if len(dataAll)>0:
            rawColumns = zip(*dataAll)
            raw_ts = rawColumns[2]
            unix_ts = []
            for ts in raw_ts:
                unix_ts.append(calendar.timegm(ts.timetuple())-8*3600) # convert SGT to unix timestamps

            df = pd.DataFrame.from_items([('TIMESTAMP',unix_ts),('MODE',rawColumns[5]),('CMODE',rawColumns[6]), \
            ('STEPS',rawColumns[9]),('WLATITUDE',rawColumns[13]),('WLONGITUDE',rawColumns[14]),('ACCURACY',rawColumns[15])])
            return df
        else:
            logging.warning('No data!')
            return None

    except psycopg2.DatabaseError, e:
            print e
            return None

def calculate_features(data_frame, high_velocity_thresh=40):
    """Calculate additional features and attributes from the raw hardware
    data. New attributes are added as new columns in the data frame in
    place.

    high_velocity_thresh : maximum threshold for velocities in m/s,
                           higher values are rejected. Default 40m/s
                           (= 144 km/h)
    """
    
    # calculate time delta since the last measurement, in seconds
    # sort the data frame based on timestamps to get ascending timestamps
    data_frame=data_frame.sort(['TIMESTAMP'],ascending=[1])
    consec_timestamps = izip(data_frame[['TIMESTAMP']].values[:-1], data_frame[['TIMESTAMP']].values[1:])
    delta_timestamps = map(lambda x: x[1][0]-x[0][0], consec_timestamps)
    # add a zero value for the first measurement where no delta is available
    delta_timestamps = [0] + delta_timestamps
    data_frame['TIME_DELTA'] = pd.Series(delta_timestamps)
    # ts_series = pd.Series(delta_timestamps)
    # print ts_series[ts_series<=0]
    # print data_frame
    
    # calculate steps delta since the last measurement
    consec_steps = izip(data_frame[['STEPS']].values[:-1], data_frame[['STEPS']].values[1:])
    delta_steps = map(lambda x: x[1][0]-x[0][0], consec_steps)
    # add a zero value for the first measurement where no delta is available
    data_frame['STEPS_DELTA'] = pd.Series([0] + delta_steps)
    
    # select rows in data frame that have valid locations
    df_validloc = data_frame.loc[~np.isnan(data_frame['WLATITUDE']) & ~np.isnan(data_frame['WLONGITUDE'])]
    # calculate distance delta from pairs of valid lat/lon locations that follow each other
    valid_latlon = df_validloc[['WLATITUDE', 'WLONGITUDE']].values
    dist_delta = map(lambda loc_pair: great_circle_dist(np.round(loc_pair[0],4), np.round(loc_pair[1],4), unit="meters"), izip(valid_latlon[:-1], valid_latlon[1:]))
    # calculate time delta from pairs of valid timestamps
    valid_times = df_validloc['TIMESTAMP'].values
    time_delta = valid_times[1:] - valid_times[:-1]
    # calculate velocity, m/s
    velocity = dist_delta / time_delta

    # create new columns for delta distance, time delta and velocity, initialzied with NaN
    data_frame['DISTANCE_DELTA'] = pd.Series(dist_delta, df_validloc.index[1:])
    data_frame['VELOCITY'] = pd.Series(velocity, df_validloc.index[1:]) # velocity in m/s

    # replace very high velocity values which are due to wifi
    # localizations errors with NaN in VELOCITY column
    label_too_high_vel = data_frame['VELOCITY'] > high_velocity_thresh
    idx_too_high = label_too_high_vel[label_too_high_vel==True].index.tolist()
    idx_bef_too_high = (np.array(idx_too_high)-1).tolist()
    data_frame.loc[idx_too_high,['WLATITUDE', 'WLONGITUDE','DISTANCE_DELTA','VELOCITY']] = np.nan
    data_frame.loc[idx_bef_too_high,['WLATITUDE', 'WLONGITUDE','DISTANCE_DELTA','VELOCITY']] = np.nan

    # calculate the moving average of velocity, m/s
    LARGE_TIME_JUMP = 60
    window_size = 5
    velocity_all = data_frame['VELOCITY'].values
    ave_velocity_all = []
    for idx in xrange(0,len(velocity_all)):
        if idx<window_size:
            ave_velocity_all.append(aveWithNan(velocity_all[0:idx]))
        else:
            ave_velocity_all.append(aveWithNan(velocity_all[idx-window_size+1:idx]))
    ave_velocity_all = np.array(ave_velocity_all)
    idx_large_jump = np.where(np.array(delta_timestamps)>LARGE_TIME_JUMP)[0].tolist()
    ave_velocity_all[idx_large_jump] = velocity_all[idx_large_jump]
    data_frame['AVE_VELOCITY'] = pd.Series(ave_velocity_all.tolist()) # velocity in m/s

    return data_frame

def getFirstSecondOfDay(timestamp):
    """get a unix timestamp in UTC time and return the timestamp for first second of
    that day in Singapore time

    """
    f = timestamp - timestamp % 86400 - 28800
    if timestamp - f >= 86400:
         f = f + 86400
    return f


def clean_data(data_frame, valid_lat_low=1.0,
               valid_lat_up=2.0,valid_lon_low=103.0,valid_lon_up=105.0,
               location_accuracy_thresh=1000):
    """Clean data frame by replacing entries with impossible values with
    'null values'. The method does not remove rows to keep the
    original data intact. Each predictor that is using the fetures is
    responsible for checking that the features are valid. Changes are
    made in-place. There is no return value.


    valid_lat_low : float value to signal a possible minimum latitude. Default 1.0

    valid_lat_up : float value to signal a possible maximum latitude. Default 2.0

    valid_lon_low : float value to signal a possible minimum longitude. Default 103.0

    valid_lon_up : float value to signal a possible maximum longitude. Default 105.0

    location_accuracy_thresh : upper threshold on the location
                               accuracy in meters beyond which we
                               treat the location as
                               missing. Default 1000

    """
    def invalid_location(acc):
        """Select rows with invalid accuracy. acc is a data frame column,
        returns a data frame of boolean values."""
        return (acc < 0) | (acc > location_accuracy_thresh)


    # replace invalid lat/lon values with NaN
    data_frame.loc[(data_frame['WLATITUDE'] < valid_lat_low) | (data_frame['WLATITUDE'] > valid_lat_up),
                   ['WLATITUDE', 'WLONGITUDE']] = np.nan
    data_frame.loc[(data_frame['WLONGITUDE'] < valid_lon_low) | (data_frame['WLONGITUDE'] > valid_lon_up),
                   ['WLATITUDE', 'WLONGITUDE']] = np.nan

    # replace locations with poor accuracy or negative accuracy values
    # (signal for invalid point) with NaN and set velocity as invalid
    if 'ACCURACY' in data_frame.columns:
        data_frame.loc[invalid_location(data_frame['ACCURACY']) ,
                       ['WLATITUDE', 'WLONGITUDE']] = np.nan

def main(url, nid, current_date =
         datetime.date.today().strftime("%Y-%m-%d"), log_level=logging.WARNING):
    """Main processing function, it takes in a nid and provides desired analytic results,
    including raw coordinates along the real track, home/school locations, modes/distance/duration of the am/pm trip
    """
    def process(nid, analysis_date, current_date):
        """Process device nid for given date (%Y-%m-%d) and save the results
        to the backend API. Return pandas data frame with the device
        data, the predicted travle modes, identified trips, home
        location and school location

        """

        # convert analysis_date into unix timestamp in UTC time
        # analysis_unix = calendar.timegm(analysis_date_tuple.timetuple())

        # get the starting and end indices for querying the data, UTC timestamps
#        start_get = int(getFirstSecondOfDay(analysis_unix))+12*3600 #12 pm of the analysis day
#        end_get = int(start_get+24*3600-1) #12 pm of the day after the analysis day
        # start_get = int(getFirstSecondOfDay(analysis_unix)) #0 am of the analysis day
        # end_get = int(start_get+24*3600-1) #24 pm of the analysis day

        print "current_date: ", current_date
        print "previous_date: ", analysis_date
        # print "start unix: ",start_get
        # print "end unix: ",end_get

        # retrieve unprocessed device data from the backend
        logging.info("Get data for device %d on the day %s" % (nid, analysis_date))
        # data_frame = getDataIHPD(url, nid, start_get, end_get)
        tablename='week1_new'
        data_frame = getDataPostgres(tablename, nid, analysis_date, current_date)

        if data_frame is None:
            logging.info("No data returned for device %d, skip." % nid)
            return None
        elif len(data_frame)<30:
            # if the data frame size is smaller than a certain threshold, then abandon the data
            logging.warning("Too little data returned for device %d, skip." % nid)
            return None

        # clean data to reduce noise
        logging.info("Clean data for device %d" % nid)
        clean_data(data_frame,
                   valid_lat_low=valid_lat_low,
                   valid_lat_up=valid_lat_up,
                   valid_lon_low=valid_lon_low,
                   valid_lon_up=valid_lon_up,
                   location_accuracy_thresh=location_accuracy_thresh)
        # calculate additional features
        logging.info("Calculate features for device %d" % nid)
        data_frame = calculate_features(data_frame, high_velocity_thresh=high_velocity_thresh)
        # print 'df after feature calculation'
        # print data_frame
        # predict the travel mode for each measurement
        logging.info("Predict modes for device %d" % nid)
        hw_modes = data_frame['MODE'].values
        smooth_modes = smooth_heuristic.predict(data_frame, hw_modes)
        predicted_modes = train_heuristic.predict(data_frame, smooth_modes)
        predicted_modes = bus_heuristic.predict(data_frame, predicted_modes)
        # identify trips from the data
        trips, home_loc, school_loc, pois, am_track, pm_track = tripParse.process(predicted_modes, data_frame,
                                                      stopped_thresh=stopped_thresh,
                                                      poi_dwell_time=poi_dwell_time,
                                                      school_start=school_start,
                                                      school_end=school_end,
                                                      home_start=home_start,
                                                      home_end=home_end,
                                                      max_school_thresh = max_school_thresh,
                                                      home_school_round_decimals=home_school_round_decimals,
                                                      mode_thresh=mode_thresh,
                                                      poi_cover_range = poi_cover_range)

        # logging in .err
        num_pt = len(data_frame)
        time_span = (data_frame['TIMESTAMP'][num_pt-1]-data_frame['TIMESTAMP'][0])/3600 % 24
        logging.warning("NID: " + str(nid) + "; TIME SPAN: " + str(time_span) + "; NUM of PTS: " + str(num_pt))
        logging.warning("NID: " + str(nid) + "; HOME: " + str(home_loc))
        logging.warning("NID: " + str(nid) + "; SCHOOL: " + str(school_loc))
        logging.warning("NID: " + str(nid) + "; TRIPS: " + str(trips))
        logging.warning("NID: " + str(nid) + "; POIS: " + str(pois))

        return am_track, pm_track, trips, home_loc, school_loc
        

    # stopped_thresh is the speed in m/s below which we consider the
    # user to be non-moving. Default 0.1 m/s (= 0.4km/h)
    stopped_thresh = 0.6
    # high_velocity_thresh : maximum threshold for velocities in m/s,
    #                       higher values are rejected. Default 40m/s
    #                           (= 144 km/h)
    high_velocity_thresh = 40
    # location_accuracy_thresh : upper threshold on the location
    # accuracy in meters beyond which we treat the location as
    # missing. Default 1000
    location_accuracy_thresh = 1000
    # float value to signal a possible minimum latitude. Default 1.0
    valid_lat_low = 1.0
    # float value to signal a possible maximum latitude. Default 2.0
    valid_lat_up = 2.0
    # float value to signal a possible minimum longitude. Default 103.0
    valid_lon_low = 103.0
    # float value to signal a possible maximum longitude. Default 105.0
    valid_lon_up = 105.0
    # school_start is the hour of the day when school starts. Default 9am.
    school_start = 9
    # school_end is the hour of the day when school end. Default 1pm.
    school_end = 13
    # home_start is the first hour of the day when students are assumed to be
    # home at night. Default 10pm.
    home_start = 22
    # home_end is the last hour of the day when students are assumed to be
    # home at night. Default 5am.
    home_end = 5
    #  threshold for the minimum distance between home and school. Default 300m
    max_school_thresh = 100
    # round_decimals is the number of decimals used in the max_freq
    # heuristic for rounding lat / lon values before taking the most
    # frequent value to indetify the home or school location
    home_school_round_decimals = 4
    # time_offset is the offset in hours to add to each
    # timestamp for identifying home and school locations
    SGT_time_offset = 8
    # poi_dwell_time is the time in seconds above which a stopped
    # location is considered a point of interest. Default 900 sec (=
    # 15min)
    poi_dwell_time = 480
    # mode_thresh is the number of seconds which the mode should be held before
    # it is considered a real mode. Deafault = 240 sec (=4 min)
    mode_thresh = 120 # 240
    # poi_cover_range is a distance which decides whether the other location
    # points are considered as belonging to the poi. Default = 30 meter
    poi_cover_range = 30
    # number of dates that maximaly be re-attempted to process if they
    # have previously faild. Default 0 (no re-attempts).
    max_attempts_pending = 0

    # create logger
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT, level=log_level)

    # remember start time for performance analysis
    start_time = time.time()

    # determine which date to process data for which is one day before the current date
    analysis_date_tuple = datetime.datetime.strptime(current_date, "%Y-%m-%d") - datetime.timedelta(days=1)
    analysis_date =  analysis_date_tuple.strftime("%Y-%m-%d")
    analysis_weekday = analysis_date_tuple.weekday() # 0 for Monday, 6 for Sunday
    if analysis_weekday==0:
        home_end = 0
        logging.debug('It is a Monday! home_end='+str(home_end))
    elif analysis_weekday==4:
        home_start = 24
        logging.debug('It is a Friday! home_start='+str(home_start))
    

    # create predictors, load trained model if necessary
    logging.info("Load predictor model")
    smooth_heuristic = modeSmoother.SmoothingPredictor()
    train_heuristic = TransitHeuristic.TrainPredictor()
    bus_heuristic = TransitHeuristic.BusMapPredictor()

    logging.info("== Process device ID = %d ==" % nid)
    try:
        result = process(nid, analysis_date, current_date)
        if result==None:
            logging.warning('No analytic results gotten!')
            return None
    except:
        e = traceback.format_exc()
        logging.error("Processing nid %d failed: %s" % (nid, e))
        return None
    
    logging.info("---Processed data for node %d in %.2f seconds ---" % (nid, time.time() - start_time))
    
    return result


if __name__ == "__main__":
    from docopt import docopt
    # parse arguments
    arguments = docopt(__doc__)

    # nid is a mandatory option
    device_file = arguments['--nid']
    log_level = logging.DEBUG if arguments['--verbose'] else logging.WARNING
    current_date = arguments['--current_date'] if arguments['--current_date'] else datetime.date.today().strftime("%Y-%m-%d")

    main(arguments['URL'], device_file, current_date=current_date,  log_level=log_level)
