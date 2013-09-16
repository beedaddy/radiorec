#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

"""
This script records internet radio streams. It can be used in conjunction
with "at" or "crontab".
"""

import argparse
import configparser
import datetime
import os
import sys
import threading
import urllib.request

def check_args():
    parser = argparse.ArgumentParser(description='This program records internet radio streams')
    parser.add_argument('station', type=str, help='Name of the radio station '
                                               '(see config file for a list)')
    parser.add_argument('duration', type=check_duration, 
                        help='Recording time in minutes')
    parser.add_argument('name', nargs='?', type=str, 
                        help='A name for the recording')
    parser.add_argument('-l', '--list', action='store_true',
                        help='Get a list of all known radio stations')
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

def record(stoprec, streamurl, target_dir, name=None):
    conn = urllib.request.urlopen(streamurl)
    filename = target_dir + os.sep + datetime.datetime.now().isoformat()
    if name:
        filename += '_' + name
    if(conn.getheader('Content-Type') == 'audio/mpeg'):
        filename += '.mp3'
    target = open(filename, "wb")
    while(not stoprec.is_set() and not conn.closed):
        target.write(conn.read(1024))

def main():
    args = check_args()
    settings = read_settings()
    streamurl = ''
    if(args.list):
        for l in args.list:
            print(l)
    try:
        streamurl = settings['STATIONS'][args.station]
    except KeyError:
        print('Unkown station name: ' + args.station)
        return
    target_dir = os.path.expandvars(settings['GLOBAL']['target_dir'])
    stoprec = threading.Event()

    recthread = threading.Thread(target = record, 
                        args = (stoprec, streamurl, target_dir, args.name), daemon = True)
    recthread.start()
    recthread.join(args.duration * 60)

    if(recthread.is_alive):
        stoprec.set()

if __name__ == '__main__':
    main()
