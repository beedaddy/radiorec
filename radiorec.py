#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

"""
radiorec.py – Recording internet radio streams
Copyright (C) 2013  Martin Brodbeck <martin@brodbeck-online.de>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import configparser
import datetime
import os
import stat
import sys
import threading
import urllib3
import logging
import time
logging.basicConfig(level=logging.DEBUG)

def print_time():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def check_duration(value):
    try:
        value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            'Duration in minutes must be a positive integer.')

    if value < 1:
        raise argparse.ArgumentTypeError(
            'Duration in minutes must be a positive integer.')
    else:
        return value


def read_settings(args):
    settings_base_dir = ''
    if args.settings:
        settings_base_dir = args.settings
    elif sys.platform.startswith('linux'):
        settings_base_dir = os.getenv(
            'HOME') + os.sep + '.config' + os.sep + 'radiorec'
    elif sys.platform == 'win32':
        settings_base_dir = os.getenv('LOCALAPPDATA') + os.sep + 'radiorec'
    elif sys.platform == 'darwin':
        settings_base_dir = os.getenv('HOME') + os.sep + 'Library' + os.sep + 'Application Support' + os.sep + 'radiorec'
    settings_base_dir += os.sep
    config = configparser.ConfigParser()
    try:
        config.read_file(open(settings_base_dir + 'settings.ini'))
    except FileNotFoundError as err:
        print(str(err))
        print('Please copy/create the settings file to/in the appropriate location.')
        sys.exit()
    return dict(config.items())


def record_worker(stoprec, streamurl, target_dir, args):
    pool = urllib3.PoolManager()
    conn = pool.request('GET',streamurl, preload_content=False)
    conn.auto_close = False
    if conn.status != 200:
        conn.release_conn()
        time.sleep(10)
        verboseprint(print_time() + " ... Waited to return for retry bcof status " + str(conn.status))
        return

    cur_dt_string = datetime.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
    filename = target_dir + os.sep + cur_dt_string + "_" + args.station
    if args.name:
        filename += '_' + args.name
    content_type = conn.getheader('Content-Type')
    if(content_type == 'audio/mpeg'):
        filename += '.mp3'
    elif(content_type == 'application/aacp' or content_type == 'audio/aacp'):
        filename += '.aac'
    elif(content_type == 'application/ogg' or content_type == 'audio/ogg'):
        filename += '.ogg'
    elif(content_type == 'audio/x-mpegurl'):
        print('Sorry, M3U playlists are currently not supported')
        sys.exit()
    else:
        print('Unknown content type "' + content_type + '". Assuming mp3.')
        filename += '.mp3'

    verboseprint(print_time() + " ... Writing to: " + filename + ", Content-Type: " + conn.getheader('Content-Type'))
    with open(filename, 'wb') as target:
        if args.public:
            verboseprint('Apply public write permissions (Linux only)')
            os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
        while(not stoprec.is_set() and not conn.closed):
            target.write(conn.read(1024))

    verboseprint(print_time() + " ... Connection closed = " + str(conn.closed))
    conn.release_conn()

def record(args):
    settings = read_settings(args)
    streamurl = ''
    global verboseprint
    verboseprint = print if args.verbose else lambda *a, **k: None

    try:
        streamurl = settings['STATIONS'][args.station]
    except KeyError:
        print('Unkown station name: ' + args.station)
        sys.exit()
    if streamurl.endswith('.m3u'):
        verboseprint('Seems to be an M3U playlist. Trying to parse...')
        pool = urllib3.PoolManager()
        with pool.request('GET',streamurl) as remotefile:
            for line in remotefile:
                if not line.decode('utf-8').startswith('#') and len(line) > 1:
                    tmpstr = line.decode('utf-8')
                    break
        streamurl = tmpstr

    verboseprint(print_time() + " ... Stream URL: " + streamurl)
    target_dir = os.path.expandvars(settings['GLOBAL']['target_dir'])
    started_at = time.time()
    should_end_at = started_at + (args.duration * 60)
    remaining = (args.duration * 60)

    # as long as recording is supposed to run
    while time.time() < should_end_at:
        stoprec = threading.Event()
        recthread = threading.Thread(target=record_worker, args=(stoprec, streamurl, target_dir, args))
        recthread.setDaemon(True)
        recthread.start()
        verboseprint(print_time() + " ... Started thread " + str(recthread) + " timeout: " + str(remaining / 60) + " min")
        recthread.join(remaining)
        verboseprint(print_time() +  " ... Came out of rec thread again")

        if(recthread.is_alive):
            stoprec.set()
            verboseprint(print_time() + " ... Called stoprec.set()")
        else:
            verboseprint(print_time() + " ... recthread.is_alive = False")

        remaining = should_end_at - time.time()
        verboseprint(print_time() + " ... Remaining: " + str(remaining / 60) + ", Threads: "  + str(threading.activeCount()))


def list(args):
    settings = read_settings(args)
    for key in sorted(settings['STATIONS']):
        print(key)


def main():
    parser = argparse.ArgumentParser(description='This program records internet radio streams. It is free software and comes with ABSOLUTELY NO WARRANTY.')
    subparsers = parser.add_subparsers(help='sub-command help')
    parser_record = subparsers.add_parser('record', help='Record a station')
    parser_record.add_argument('station', type=str,
                               help='Name of the radio station '
                               '(see `radiorec.py list`)')
    parser_record.add_argument('duration', type=check_duration,
                               help='Recording time in minutes')
    parser_record.add_argument('name', nargs='?', type=str,
                               help='A name for the recording')
    parser_record.add_argument(
        '-p', '--public', action='store_true',
        help="Public write permissions (Linux only)")
    parser_record.add_argument(
        '-v', '--verbose', action='store_true', help="Verbose output")
    parser_record.add_argument(
        '-s', '--settings', nargs='?', type=str,
        help="specify alternative location for settings.ini")
    parser_record.set_defaults(func=record)
    parser_list = subparsers.add_parser('list', help='List all known stations')
    parser_list.set_defaults(func=list)
    parser_list.add_argument('-s', '--settings', nargs='?', type=str, help="specify alternative location for settings.ini")

    if not len(sys.argv) > 1:
        print('Error: No argument specified.\n')
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
