#!/usr/bin/env python3

import time
import sys
import os
import mailbox
from email.mime.text import MIMEText
import logging

import mboxcl_parser
import mbox_type_detect


def main(infile, outfile):
    logging.debug(f'Attempting to "lighten" {infile} --> {outfile}')
    type = mbox_type_detect.detect(infile)
    if not type:
        logging.error('Could not determine mbox flavor.')
        return 1
    if type == 'mbox':
        mbox = mailbox.mbox(infile)
    if type == 'mboxcl':
        mbox = mboxcl_parser.parse_from_filename(infile)
    logging.info(f'Mailbox {os.path.basename(infile)} opened. Contains {len(mbox)} messages.')
    outbox = mailbox.mbox(outfile)
    logging.debug(f'{outfile} opened for writing.')
    for m in mbox:
        headers = []  # for storing headers later
        for h in m.items():
            headers.append(h)
        lightmessage = lighten_message(m, headers)
        if not lightmessage:
            logging.debug('No content in message after comment stripping.')
            # TODO catch HTML-only messages and process them here
            continue
        if not lightmessage['Subject']:
            # no subject line, which is bad
            logging.info(f'Subject-less message skipped: {lightmessage["Message-ID"]}')
            continue
        else:
            outbox.add(lightmessage)
    logging.info(f'Wrote {len(outbox)} messages to {os.path.basename(outfile)}')
    outbox.flush()
    outbox.close()
    return 0


def lighten_message(msg: mailbox.mboxMessage, headers: list) -> MIMEText:
    logging.debug(f'Processing message {msg["Message-ID"]} {msg["Content-Type"].split(";")[0]}')
    for part in msg.walk():
        if part.get_content_disposition() is not None:  # skip attachments
            logging.debug(f'Skipped {msg["Content-Type"].split(";")[0]} -- appears to be an attachment')
            continue
        if part.get_content_maintype().lower() in ['application', 'audio', 'multipart']:  # skip multipart, etc.
            logging.debug(f'Skipped {msg["Content-Type"].split(";")[0]} -- appears to be a non-text part')
            continue
        if part.get_content_type().lower() == 'text/plain':
            logging.debug(f'Found {msg["Content-Type"].split(";")[0]}')
            newmsg = MIMEText(strip_3quoteblocks(part.get_payload(decode=True).decode('utf-8', errors='replace')))
            for h in headers:
                keepheaders = ['Received', 'Date', 'From', 'To', 'Subject', 'Message-ID', 'User-Agent']
                if h[0] in keepheaders:
                    newmsg.add_header(h[0], h[1])
                else:
                    continue
            return newmsg
        else:
            logging.debug(f'Unhandled message part: {part.get_content_type().lower()}')
            continue


def strip_3quoteblocks(payload: str) -> str:
    deletelines = []
    lines = payload.splitlines()
    logging.debug(f'Starting to strip quote blocks: original message contains {len(lines)} lines')
    for i in range(len(lines)):
        # look for series of 3 quoted lines together
        if (  # there's probably a more-elegant general way to do this for blocks of N quoted lines...
                (is_quoted_line(lines, i) and is_quoted_line(lines, i + 1) and is_quoted_line(lines, i + 2))
                or (is_quoted_line(lines, i) and is_quoted_line(lines, i + 1) and is_quoted_line(lines, i - 1))
                or (is_quoted_line(lines, i) and is_quoted_line(lines, i - 1) and is_quoted_line(lines, i - 2))
        ):
            deletelines.append(i)
    for linenumber in sorted(deletelines, reverse=True):  # reverse sort, so we don't change indices as we delete lines
        del lines[linenumber]  # in-place modification
    logging.debug(f'Finished stripping quote blocks: stripped message contains {len(lines)} lines')
    return '\n'.join(lines)


def is_quoted_line(lines: list, i: int) -> bool:
    """Determine if a plaintext line is quoted text; not safe for HTML components."""
    try:
        if '>' in lines[i][:3]:  # might be more sophisticated ways of detecting quoting...
            return True
        else:
            return False
    except IndexError:
        return False


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    start = time.process_time()  # For performance measurements
    exitval = main(sys.argv[1], sys.argv[2])
    logging.debug(f'{sys.argv[0]} completed in {str((time.process_time() - start))} seconds')
    sys.exit(exitval)
