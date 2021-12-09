#!/usr/bin/env python3
"""Lighten a mbox file by stripping out all non-text parts and producing a new mbox with just text"""

import time
import sys
import os
import mailbox
from email.mime.text import MIMEText
import re
import logging
from typing import Union

import mboxcl_parser
import mbox_type_detect


def main(infile: str, outfile: str) -> int:
    logging.info(f'Attempting to "lighten" {infile} --> {outfile}')
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
        headers = []
        for h in m.items():
            headers.append(h)  # appends a (key, value) tuple for each header
        lightmessage = lighten_message(m, headers)
        if not lightmessage:
            logging.debug('No content in message after comment stripping.')
            lightmessage = html_to_text(m, headers)
        if not lightmessage:
            logging.info(f'Skipped message without text or HTML payload: {m["Message-ID"]}')
            continue
        else:
            outbox.add(lightmessage)
    logging.info(f'Wrote {len(outbox)} messages to {os.path.basename(outfile)}')
    outbox.flush()
    outbox.close()
    return 0


def lighten_message(msg: mailbox.mboxMessage, headers: list) -> Union[MIMEText, bool]:
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


def html_to_text(msg: mailbox.mboxMessage, headers: list) -> Union[MIMEText, bool]:
    logging.debug(f'Looking for HTML in {msg["Message-ID"]} {msg["Content-Type"].split(";")[0]}')
    for part in msg.walk():
        ctype = part.get_content_type().lower()
        cdispo = str(part.get('Content-Disposition')).lower()
        if ctype == 'text/html' and 'attachment' not in cdispo:
            logging.debug(f'Found {msg["Content-Type"].split(";")[0]}')
            htmlbody = part.get_payload(decode=True).decode('utf-8', errors='replace')
            textbody = strip_html(htmlbody)
            newmsg = MIMEText(strip_3quoteblocks(textbody))
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
    joined = '\n'.join(lines)
    return joined.strip()


def is_quoted_line(lines: list, i: int) -> bool:
    """Determine if a plaintext line is quoted text; not safe for HTML components."""
    try:
        if '>' in lines[i][:3]:  # might be more sophisticated ways of detecting quoting...
            return True
        if re.match("On .*wrote:", lines[i]):  # also not worth keeping
            return True
        else:
            return False
    except IndexError:
        return False


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    start = time.process_time()  # For performance measurements
    exitval = main(sys.argv[1], sys.argv[2])
    logging.debug(f'{os.path.basename(sys.argv[0])} completed in {str((time.process_time() - start))} seconds')
    sys.exit(exitval)
