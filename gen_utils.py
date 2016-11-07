#!/usr/bin/python
__author__ = 'agoss'

from datetime import datetime
import logging
from os import path

import pytz

def error_logging(message, filename):
    """Creates errorlog file.

    Returns:
        Errorlog file in working directory.
    """
    ERRORLOG = './' + str(datetime.today().strftime('%Y%m%d_%H%M%S_')) + filename + '_errorlog.txt'
    if path.exists(ERRORLOG):
        pass # skip creating new error log if it already exists
    else:
        logging.basicConfig(filename=ERRORLOG, level=logging.DEBUG, format='%(asctime)s [%(filename)s:%(lineno)s - %(funcName)2s()] %(message)s', datefmt='%Y%m%d %I:%M:%S %p')
    logging.exception(message)
    return

def convert_tz_date(date_in, tz_in, tz_out):
    """Converts date in current timezone (tz_in) to desired timezone output (tz_out).

    Returns:
        Converted date based on desired timezone output (tz_out). 
    """
    naive = datetime.strptime(date_in, "%d/%m/%Y") # naive object does not contain enough information to unambiguously locate itself relative to other date objects
    tz_in = pytz.timezone(tz_in)
    tz_out = pytz.timezone(tz_out)
    date_out = tz_in.localize(naive, is_dst=None).astimezone(tz_out)
    date_out = date_out.strftime("%Y-%m-%d") # format date
    return date_out

def convert_tz_time(time_in, tz_in, tz_out):
    """Converts time in current timezone (tz_in) to desired timezone output (tz_out).

    Returns:
        Converted time based on desired timezone output (tz_out). 
    """
    naive = datetime.strptime(time_in, "%H:%M") # naive object does not contain enough information to unambiguously locate itself relative to other time objects
    tz_in = pytz.timezone(tz_in)
    tz_out = pytz.timezone(tz_out)
    time_out = tz_in.localize(naive, is_dst=None).astimezone(tz_out)
    time_out = time_out.strftime("%H:%M:%S%z") # format time
    return time_out