#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

"""
This script records internet radio streams. It can be used in conjunction
with "at" or "crontab".
"""

import argparse
import configparser
import os
import sys
import threading
import urllib.request

def check_args():
    parser = argparse.ArgumentParser(description='This program records '
                                              'internet radio streams.')
    parser.add_argument('station', type=str, help='Name of the radio station '
                                               '(see config file for a list)')
    parser.add_argument('duration', type=check_duration, 
                        help='Recording time in minutes')
    parser.add_argument('name', nargs='?', type=str, 
                        help='A name for the recording')
    return parser.parse_args()

def check_duration(value):
    try:
        value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('Duration must be a positive integer.')

    if value < 1:
        raise argparse.ArgumentTypeError('Duration must be a positive integer.')
    else:
        return value

def read_settings():
    settings_base_dir = ''
    if sys.platform == 'linux':
        settings_base_dir = os.getenv('HOME') + os.sep + '.config' + os.sep + 'radiorec'
    elif sys.platform == 'win32':
        settings_base_dir = os.getenv('APPDATA') + os.sep + 'radiorec'
    settings_base_dir += os.sep
    config = configparser.ConfigParser()
    config.read(settings_base_dir + 'settings.ini')
    return dict(config.items())

def record(stoprec, streamurl, target_dir):
    target = open(target_dir + '/test.mp3', "wb")
    conn = urllib.request.urlopen(streamurl)
    #print(conn.getheader('Content-Type'))
    while(not stoprec.is_set() and not conn.closed):
        target.write(conn.read(1024))

def main():
    args = check_args()
    settings = read_settings()
    streamurl = ''
    try:
        streamurl = settings['STATIONS'][args.station]
    except KeyError:
        print('Unkown station name: ' + args.station)
        return
    target_dir = os.path.expandvars(settings['GLOBAL']['target_dir'])
    stoprec = threading.Event()

    recthread = threading.Thread(target = record, 
                        args = (stoprec, streamurl, target_dir), daemon = True)
    recthread.start()
    recthread.join(args.duration * 60)

    if(recthread.is_alive):
        stoprec.set()

if __name__ == '__main__':
    main()
