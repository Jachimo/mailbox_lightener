#!/usr/bin/env python3
"""Quick-and-dirty parser for mboxcl2-flavor .mbox files, such as those produced by (old versions of?) Dovecot"""

# Dovecot mbox implementation docs: https://doc.dovecot.org/admin_manual/mailbox_formats/mbox/#mbox-mbox-format
#  and https://opensource.apple.com/source/dovecot/dovecot-279/dovecot/doc/wiki/MailboxFormat.mbox.txt.auto.html

from typing import TextIO
from typing import BinaryIO
import os
import sys
import mmap
import re
import mailbox
import email.parser
import logging


def parse_from_filename(fname):
    assert type(fname) is str
    assert os.path.isfile(fname) is True
    logging.debug(f'Processing from file {fname}')
    with open(fname, 'rb') as infile:
        return parse_from_file(infile)


def parse_from_file(infile):
    logging.debug(f'Creating read-only mmap from {infile.fileno()}')
    mm = mmap.mmap(infile.fileno(), 0, access=mmap.ACCESS_READ)
    return parse_from_mmap(mm)


def parse_from_mmap(mm):
    assert type(mm) is mmap.mmap
    if not is_unix_from(mm[:5]):
        raise ValueError('Input does not begin with "From " which is required for an mbox file.')
    logging.debug('Beginning mmap processing.')
    messages = []
    regex = re.compile(b'\nContent-Length:\s(\d*)\n\n')  # find content-length if at end of headers (followed by \n)

    mm.seek(0)
    msgstart = mm.tell()
    searchstart = mm.tell()
    while True:
        logging.debug(f'Beginning search at offset {searchstart}')
        try:
            contentsearch = re.search(regex, mm[searchstart:])
        except:
            print("Trapped contentsearch exception!")  # TODO remove me when we figure out what exception is thrown
            raise
        if not contentsearch:  # when no more matches
            break
        logging.debug(f'Found {contentsearch.group(1)} at offset {contentsearch.start()}')
        headerend = int(contentsearch.end()) + searchstart  # offset where search string ends (relative to searchstart!)
        contentlen = int(contentsearch.group(1))  # length of the alleged content payload in bytes (from headerend)
        msg = mm[msgstart:headerend + contentlen]
        logging.debug('First 64B are: ' + str(msg[:64]))
        if msg[:5] == b'From ':
            logging.debug('Valid Content-Length detected, processing message.')
            messages.append(msg)
            msgstart = headerend + contentlen + 1  # should be beginning of next "From " line (extra 1B is for \n)
            searchstart = msgstart
        else:
            logging.debug(f'Invalid Content-Length detected; restarting search at {headerend}')
            searchstart = headerend
            mm.seek(headerend)  # restart the search after the previous (bad) match
            continue
    logging.info(f'Finished parsing {len(messages)} messages')

    logging.debug('Converting bytestrings to mailbox.mboxMessage objects...')
    convertedmsgs = []
    for msg in messages:
        bparser = email.parser.BytesParser()
        emailmessage = bparser.parsebytes(msg)  # returns an email.message.Message object
        mboxmessage = mailbox.mboxMessage(emailmessage)  # convert to a specialized mailbox.mbox message
        convertedmsgs.append(mboxmessage)  # return list of messages (closest we can easily get to an actual mailbox)
    logging.info(f'Finished converting {len(convertedmsgs)} messages, returning list')
    return convertedmsgs


def is_unix_from(bline):
    if type(bline) is str:
        bline = bline.encode('us-ascii', errors='replace')  # get bytes from string
    if bline[:5] == 'From '.encode('us-ascii'):
        return True
    else:
        return False


if __name__ == "__main__":
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    # for testing:
    testoutput = parse_from_filename(sys.argv[1])
    if not testoutput:
        sys.exit(1)
    for m in testoutput:
        print(f'TYPE:  {type(m)}')
        print(f'To:    {m["To"]}')
        print(f'From:  {m["From"]}')
        print(f'Date:  {m["Date"]}')
        print(f'Subj.: {m["Subject"]}\n')
    logging.info(f'{sys.argv[0]} completed with {len(testoutput)} messages output.')
    sys.exit(0)
