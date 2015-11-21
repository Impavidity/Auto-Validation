# -*- coding: utf-8 *-*

import datetime
import xlrd
from colored import bg,fg,attr
import NSE_Analytics_for_validation.process
import logging

def read_file(file_name):
    try:
        print ("%s%s[FILE]%s" % (fg(1), bg(15), attr(0))), "Reading file now ..."
        data = xlrd.open_workbook(file_name)
        table = data.sheets()[0]
        num = table.nrows - 1
        ID = [int(item) for item in table.col_values(0)[1:]]
        Date = [str(int(item)) for item in table.col_values(1)[1:]]
        if len(ID) == len(Date) == num:
            print ("%s%s[FILE]%s" % (fg(1), bg(15), attr(0))), "Read file successfully"
        else:
            print ("%s%s[FILE]%s" % (fg(15), bg(1), attr(0))),"File length error"
        return ID, Date
    except IOError, error:
        print ("%s%s[FILE]%s" % (fg(15), bg(1), attr(0))), "File IO error", error
 


def main():
    # initialization
    # create one dict for nodes that are skipped with the skipping reasons

    # create one dict for nodes that are recommended for manual check

    # create one dict for nodes that with a valid judgement

    # parameters
    url="https://data.nse.sg" # API to call
    isAM = True # only check the am trips

    nodeID, nodeDate = read_file("nodes for testing auto-validation.xlsx")
    # print "[QUERY] Node ID :", nodeID
    # print "[QUERY] Node Date :", nodeDate
    # print 'Type of nodeDate[0]: ', type(nodeDate[0])
    numNodes = len(nodeID)
    numNodes = 5;

    # go through each node
    for inode in xrange(0,numNodes):
        print "******** processing: "+str(nodeID[inode])+"********"
        # checking am trips, jump if the date is Monday
        current_date_tuple = datetime.datetime.strptime(nodeDate[inode], "%Y%m%d")
        current_date = current_date_tuple.strftime("%Y-%m-%d")
        analysis_date_tuple = datetime.datetime.strptime(current_date, "%Y-%m-%d") - datetime.timedelta(days=1)
        analysis_weekday = analysis_date_tuple.weekday() # 0 for Monday, 6 for Sunday
        if analysis_weekday==0:
            # append to the skipped node dict

            logging.warning('Analysis day is a Monday! Skip the node.')
            continue

        # call process.main() to get the analytic results
        ana_result = NSE_Analytics_for_validation.process.main(url,nodeID[inode],current_date)
        if ana_result == None:
            # append to the skipped node dict

            logging.warning('No analytic results gotten! Skip the node.')
            continue

        # valid analytic results
        # am_track: list of coordinates along track of am trip
        # pm_track: list of coordinates along track of pm trip
        # trips: json string/python dict including trip information, such as am_distance, am_duration, am_mode
        # home/school location
        am_track, pm_track, trips, home_loc, school_loc = ana_result

        print "length of am track: ", len(am_track)
        print "am_track: ", am_track
        if len(am_track)>0:
            print "type of am_track", type(am_track)
            print "type of am_track[0]", type(am_track[0])
        print "length of pm track: ", len(pm_track)
        print "home location: ", home_loc
        print "school location: ", school_loc
        print "trip information: ", trips

        # check the length of am track, total am distance and am duration, jump if too small



        # apply the quick judgement method



        # apply the general track comparison



if __name__=="__main__":
    main()