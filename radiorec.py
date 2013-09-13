#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

"""
This script records internet radio streams. It can be used in conjunction
with "at" or "crontab".
"""

import argparse
import configparser
import threading
import time
import urllib.request

def _check_args():
    parser = argparse.ArgumentParser(description='This program records '
                                              'internet radio streams.')
    parser.add_argument('station', type=str, help='Name of the radio station '
                                               '(see config file for a list)')
    parser.add_argument('duration', type=_check_duration, 
                        help='Recording time in minutes')
    parser.add_argument('name', nargs='?', type=str, 
                        help='A name for the recording')
    return parser.parse_args()

def _check_duration(value):
    try:
        value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('Duration must be a positive integer.')

    if value < 1:
        raise argparse.ArgumentTypeError('Duration must be a positive integer.')
    else:
        return value

def record(stoprec):
    while(not stoprec.is_set()):
        time.sleep(1)

def main():
    args = _check_args()

    stoprec = threading.Event()
    recthread = threading.Thread(target=record, args=(stoprec,))
    recthread.start()
    recthread.join(args.duration * 60)
    if(recthread.is_alive):
        stoprec.set()

if __name__ == '__main__':
    main()
