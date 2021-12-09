#!/usr/bin/env python3

import sys
import re
import logging


fromlineregex = re.compile("From .+\n")
contentlengthregex = re.compile("Content-Length: .+\n")


def mbox_type_detect(infile):
    """Try to detect whether we have a mboxcl-style mailbox with Content-Length headers, or a classic mbox without"""
    logging.debug(f'Beginning mbox type detection on {infile}')
    with open(infile, 'r') as fo:
        # inspect the first message and see if it contains a Content-Length header...
        firstline = fo.readline()  # skip first line
        logging.debug(f'Mailbox first line is: {firstline.rstrip()}')
        for line in fo:
            #logging.debug(f'Analyzing line: {line.rstrip()}')
            if re.match(fromlineregex, line):
                logging.debug('Found next From line before Content-Length; probably a classic mbox')
                return 'mbox'
            if re.match(contentlengthregex, line):
                logging.debug('Found Content-Length header in first message; probably a mboxcl mbox')
                return 'mboxcl'
        logging.debug('Reached EOF without From line or Content-Length; invalid mailbox file?')
        return False


if __name__ == "__main__":
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    result = mbox_type_detect(sys.argv[1])
    if not result:
        print('Indeterminate result.')
        sys.exit(1)
    else:
        print(result)
        sys.exit(0)
