#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

"""
This script records internet radio streams. It can be used in conjunction
with "at" or "crontab".
"""

import argparse
import configparser
import urllib.request

def main():
    parser = argparse.ArgumentParser(description='This program records internet radio streams.')
    parser.add_argument('station', type=str, help='Name of the radio station '
                                                '(see config file for a list)')
    parser.add_argument('duration', type=int, help='Recording time in minutes')
    parser.add_argument('name', nargs='?', type=str, help='A name for the recording')
    args = parser.parse_args()

if __name__ == '__main__':
    main()
