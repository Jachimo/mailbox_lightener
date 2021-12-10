#!/usr/bin/env python3
"""Lighten a mbox file by stripping out all non-text parts and producing a new mbox with just text"""

import time
import sys
import argparse
import os
import mailbox
from email.mime.text import MIMEText
import re
import logging
from typing import Union

import mboxcl_parser
import mbox_type_detect
import email_textutils


def main() -> int:
    parser = argparse.ArgumentParser(description='"Lighten" a mbox file by stripping out non-text parts"')
    parser.add_argument('infile', help='Input mbox file to read from')
    parser.add_argument('outfile', help='Output mbox file to write to (will append if exists)')
    parser.add_argument('--type', '-t', help='Manually specify input mbox type (mbox, mboxcl)')
    parser.add_argument('--quoteblock', '-q', type=int, default=3,
                        help="Strip blocks of this many quoted lines found together (default 3)")
    parser.add_argument('--debug', help='Enable debug mode (very verbose output)', action='store_true')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
        logging.debug('Debug output enabled')
    else:
        logging.basicConfig(encoding='utf-8', level=logging.INFO)

    infile = args.infile
    outfile = args.outfile
    logging.info(f'Attempting to "lighten" {infile} --> {outfile}')

    if args.type:
        type = args.type
    else:
        type = mbox_type_detect.detect(infile)
    if not type:
        logging.error('Could not determine mbox flavor. Try specifying manually with --type')
        return 1

    if type == 'mbox':
        mbox = mailbox.mbox(infile)
    if type == 'mboxcl':
        mbox = mboxcl_parser.parse_from_filename(infile)
    logging.info(f'Mailbox {os.path.basename(infile)} opened. Contains {len(mbox)} messages.')
    outbox = mailbox.mbox(outfile)
    logging.debug(f'{outfile} opened for writing.')

    for m in mbox:
        headers = []
        for h in m.items():
            headers.append(h)  # appends a (key, value) tuple for each header
        lightmessage = lighten_message(m, headers, args.quoteblock)
        if not lightmessage:
            logging.debug('No content in message after comment stripping.')
            lightmessage = html_to_text(m, headers, args.quoteblock)
        if not lightmessage:
            logging.info(f'Skipped message without text or HTML payload: {m["Message-ID"]}')
            continue
        else:
            outbox.add(lightmessage)
    logging.info(f'Output mailbox {os.path.basename(outfile)} now contains {len(outbox)} messages')
    outbox.flush()
    outbox.close()
    return 0


def lighten_message(msg: mailbox.mboxMessage, headers: list, blocksize: int) -> Union[MIMEText, bool]:
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
            newmsg = MIMEText(
                email_textutils.strip_quoteblocks(
                    part.get_payload(decode=True).decode('utf-8', errors='replace'),
                    blocksize)
            )
            return add_headers(newmsg, headers)
        else:
            logging.debug(f'Unhandled message part: {part.get_content_type().lower()}')
            continue
    return False  # message will fall through if it lacks a 'text/plain' part


def add_headers(msg: MIMEText, headers: list) -> MIMEText:
    for h in headers:
        keepheaders = ['Received', 'Date', 'From', 'To', 'Subject', 'Message-ID', 'User-Agent']
        if h[0] in keepheaders:
            msg.add_header(h[0], h[1])
        else:
            continue
    return msg


def html_to_text(msg: mailbox.mboxMessage, headers: list, blocksize: int) -> Union[MIMEText, bool]:
    logging.debug(f'Looking for HTML in {msg["Message-ID"]} {msg["Content-Type"].split(";")[0]}')
    for part in msg.walk():
        ctype = part.get_content_type().lower()
        cdispo = str(part.get('Content-Disposition')).lower()
        if ctype == 'text/html' and 'attachment' not in cdispo:
            logging.debug(f'Found {msg["Content-Type"].split(";")[0]}')
            htmlbody = part.get_payload(decode=True).decode('utf-8', errors='replace')
            textbody = strip_html(htmlbody)
            newmsg = MIMEText(email_textutils.strip_quoteblocks(textbody, blocksize))
            return add_headers(newmsg, headers)
    return False


def strip_html(htmlbody: str) -> str:
    """Attempt to produce readable plaintext from HTML; will mangle most complex HTML messages"""
    body = re.sub(r"<style.*</style>", "", htmlbody, re.DOTALL)  # strip <style...</style>
    newlinetags = ['<br>', '<br/>', '</p>', '</div>']  # convert all these to \n for readability of text version
    for t in newlinetags:
        body = body.replace(t, '\n')
    spacetags = ['&nbsp;', '&#160;', '&emsp;', '&ensp;']
    for s in spacetags:
        body = body.replace(s, ' ')
    body = re.sub(r"<[^>]*>", " ", body)  # and yes, an HTML parser would be the right way to do this...
    body = re.sub(r" {2,}", " ", body)  # condense spaces
    return body.strip()


if __name__ == '__main__':
    start = time.process_time()  # For performance measurements
    exitval = main()
    print(f'{os.path.basename(sys.argv[0])} completed in {str((time.process_time() - start))} seconds')
    sys.exit(exitval)
