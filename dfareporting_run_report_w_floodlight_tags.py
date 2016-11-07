#!/usr/bin/python
__author__ = 'agoss'

import argparse
from csv import reader, writer
from datetime import date, timedelta, datetime
import os
import sys
from time import sleep

import dfareporting_utils
import gen_utils
from oauth2client import client
import psycopg2
import yaml

class struct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

# declare command-line flags
argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('profile_id', type=int, help='ID of DCM profile')
argparser.add_argument('report_id', type=int, help='ID of DCM report to run')
argparser.add_argument('insert_table', type=str, help='PostgreSQL table where data will be inserted')
argparser.add_argument('col_num', type=int, help='Number of columns in insert table')

def value_string(insert_number):
    val_str = '%s'
    while insert_number > 1:
        val_str = val_str + ', %s'
        insert_number -= 1
    return val_str

def load_data(csv_data, conn, table, col):
    cur = conn.cursor()
    csv_data = list(csv_data)
    insert_date = str(datetime.now().date())
    trip = 0

    for row in csv_data:
        if trip == 0: # skip over report rows until raw data values are reached
            if len(row) == 0:
                pass
            elif row[0] == 'Date':
                trip += 1
                continue
            else:
                continue
        else:
            if row[0] == 'Grand Total:': # final report row, do not insert
                pass
            else:
                insert_query = "insert into " + table + " VALUES ("+ value_string(col) + ")"
				activity = '(not set)' # default value
                activity_headers = csv_data[9][11:] # only store floodlight headers (adjust array references)
                floodlights = {} # initialize dict
                floodlights = {key: str(value) for key, value in zip(activity_headers, row[11:])}
                
                grouping_list = []
                for header in activity_headers:
                    d = str(header).split(':')
                    if len(d) == 4:
                        grouping_list.append(str(d[1]).lstrip() + ': ' + str(d[2]).lstrip())
                    else:
                        grouping_list.append(str(d[0]).lstrip() + ': ' + str(d[1]).lstrip())
                grouping_list = list(set(grouping_list))

                no_tag = True
                for tag in floodlights:
                    if abs(float(floodlights[tag])) != 0.0:
                        no_tag = False
				
				if no_tag:
					insert_data = (insert_date, str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), str(row[6]), str(row[7]), str(row[8]), str(row[9]), str(row[10]), str(row[11]), str(row[12]), str(row[13]), str(row[14])) # adjust per number of columns needed
					print insert_data
					try:
						cur.execute(insert_query, insert_data)
						conn.commit()
					except psycopg2.Error, e:
						print 'line skipped: ' + str(e)
						conn.rollback()
						with open('./badLines_' + str(date.today())+ '.csv', 'ab') as csvout:
							outfile = writer(csvout, delimiter=',')
							outfile.writerow(insert_data)
				else:
                    floodlight_tagging(grouping_list, floodlights, cur, conn, insert_query, insert_date, row)
					
    cur.close()

def floodlight_tagging(grouping_list, floodlights, cur, conn, insert_query, insert_date, row):
    for group in grouping_list:
        ftag1 = 0 # default value
        ftag2 = 0 # default value
        ftag3 = 0 # default value
        counter = 0 # reset counter
        for tag in floodlights:
            if str(tag).startswith(group):
                if 'Floodlight tag1' in tag: # (optionally add to config.yml)
                    ftag1 = floodlights[tag]
                    counter += 1
                    continue
                if 'Floodlight tag2' in tag: # (optionally add to config.yml)
                    ftag2 = floodlights[tag]
                    counter += 1
                    continue
                if 'Floodlight tag3' in tag: # (optionally add to config.yml)
                    ftag3 = floodlights[tag]
                    counter += 1
                    continue
            else:
                if counter == 3 and abs(float(ftag1)) == 0.0 and abs(float(ftag2)) == 0.0 and abs(float(ftag3)) == 0.0:
                    break # do not store untagged rows
                elif counter == 3:
                    a = str(group).split(':') # DCM naming convention
                    activity = str(a[1]).lstrip()
                    insert_data = (insert_date, str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), str(row[6]), str(row[7]), str(row[8]), str(row[9]), str(row[10]), activity, 0, ftag1, ftag2, ftag3)
                    print insert_data
                    try:
                        cur.execute(insert_query, insert_data)
                        conn.commit()
                    except psycopg2.Error, e:
                        print 'line skipped: ' + str(e)
                        conn.rollback()
                        with open('./badLines_' + str(date.today()) + '.csv', 'a') as csvout:
                            outfile = writer(csvout, delimiter=',')
                            outfile.writerow(insert_data)
                    break
	
def main(argv):
  flags = dfareporting_utils.get_arguments(argv, __doc__, parents=[argparser]) # retrieve command line arguments
  global cfg
  with open("config.yml", 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile) # find and read config file
  cfg = struct(**cfg)

  try:
    conn = psycopg2.connect(database=cfg.postgres['database'], user=cfg.postgres['username'], password=cfg.postgres['password'], host=cfg.postgres['host'], port=cfg.postgres['port'])
  except:
    raise
  else:
    print "Opened database successfully"

  # authenticate and construct service
  service = dfareporting_utils.setup(flags)

  profile_id = flags.profile_id
  report_id = flags.report_id

  try:
    
    # construct a get request for the specified report
    request = service.reports().run(profileId=profile_id, reportId=report_id)
    result = request.execute()
    file_id = result['id']

    # check status of report file
    request = service.reports().files().list(profileId=profile_id, reportId=report_id)
    response = request.execute()

    while response['items'][0]['status'] != 'REPORT_AVAILABLE':
        print 'Report/File IDs: ', report_id, ': ', file_id, ': ', response['items'][0]['status'], '\nWaiting for report to generate...'
        sleep(30) # delay for 30 seconds before checking again
        request = service.reports().files().list(profileId=profile_id, reportId=report_id)
        response = request.execute()

    print 'Report/File IDs: ', report_id, ': ', file_id, ': ', response['items'][0]['status']
    print 'Browser: ', response['items'][0]['urls']['browserUrl']
    print 'API: ', response['items'][0]['urls']['apiUrl']

    request = service.files().get_media(reportId=report_id, fileId=file_id) # construct request to download file
    report_file = request.execute()
    csv_data = reader(report_file.splitlines(), delimiter=',')
    load_data(csv_data, conn, flags.insert_table, flags.col_num)

  except client.AccessTokenRefreshError:
    print ('The credentials have been revoked or expired, please re-run the application to re-authorize')

  conn.close()

  print '\n**********DONE**********\n'

if __name__ == '__main__':
  try:
    main(sys.argv)
  except:
    gen_utils.error_logging('main() handler exception:', str(os.path.basename(__file__)))
    raise