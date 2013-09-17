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

def record_worker(stoprec, streamurl, target_dir, name=None):
    conn = urllib.request.urlopen(streamurl)
    filename = target_dir + os.sep + datetime.datetime.now().isoformat()
    if name:
        filename += '_' + name
    content_type = conn.getheader('Content-Type')
    if(content_type == 'audio/mpeg'):
        filename += '.mp3'
    elif(content_type == 'application/ogg' or content_type == 'audio/ogg'):
        filename += '.ogg'
    elif(content_type == 'audio/x-mpegurl'):
        print('Sorry, M3U playlists are currently not supported')
        sys.exit()
    else:
        print('Unknown content type "' + content_type + '". Assuming mp3.')
        filename += 'mp3'
    with open(filename, "wb") as target:
        while(not stoprec.is_set() and not conn.closed):
            target.write(conn.read(1024))

def record(args):
    settings = read_settings()
    streamurl = ''
    global verboseprint
    verboseprint = print if args.verbose else lambda *a, **k: None

    try:
        streamurl = settings['STATIONS'][args.station]
    except KeyError:
        print('Unkown station name: ' + args.station)
        sys.exit()
    if streamurl.endswith('.m3u'):
        verboseprint('Seems to be an M3U playlist. Trying to parse…')
        with urllib.request.urlopen(streamurl) as remotefile:
            for line in remotefile:
                if not line.decode('utf-8').startswith('#'):
                    tmpstr = line.decode('utf-8')
                    break
        streamurl = tmpstr
    verboseprint('stream url: ' + streamurl)
    target_dir = os.path.expandvars(settings['GLOBAL']['target_dir'])
    stoprec = threading.Event()

    verboseprint('Recording ' + args.station + '…')
    recthread = threading.Thread(target = record_worker, 
                        args = (stoprec, streamurl, target_dir, args.name), daemon = True)
    recthread.start()
    recthread.join(args.duration * 60)

    if(recthread.is_alive):
        stoprec.set()

def list(args):
    settings = read_settings()
    for key in settings['STATIONS']:
        print(key)

def main():
    parser = argparse.ArgumentParser(prog='radiorec', description='This program records internet radio streams')
    subparsers = parser.add_subparsers(help='sub-command help')
    parser_record = subparsers.add_parser('record', help='Record a station')
    parser_record.add_argument('station', type=str, help='Name of the radio station '
                                               '(see config file for a list)')
    parser_record.add_argument('duration', type=check_duration, 
                        help='Recording time in minutes')
    parser_record.add_argument('name', nargs='?', type=str, 
                        help='A name for the recording')
    parser_record.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
    parser_record.set_defaults(func=record)
    parser_list = subparsers.add_parser('list', help='List all known stations')
    parser_list.set_defaults(func=list)
    #parser_list.add_argument('-l', '--list', action='store_true',
    #                    help='Get a list of all known radio stations')
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
