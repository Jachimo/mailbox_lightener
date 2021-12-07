#!/usr/bin/env python3

import sys
import os
import mailbox
from email.mime.text import MIMEText
import logging


def main(infile, outfile):
    logging.debug(f'Attempting to "lighten" {infile} --> {outfile}')
    mbox = mailbox.mbox(infile)
    logging.info(f'Mailbox {os.path.basename(infile)} opened. Contains {len(mbox)} messages.')
    outbox = mailbox.mbox(outfile)
    logging.debug(f'{outfile} opened for writing.')
    for m in mbox:
        headers = []  # store outer headers for later use
        for h in m.items():
            headers.append(h)
        lightmessage = lighten_message(m, headers)
        if not lightmessage:
            logging.debug('No content in message after comment stripping.')
        else:
            outbox.add(lightmessage)
    outbox.flush()
    outbox.close()
    return 0


def lighten_message(msg: mailbox.mboxMessage, headers: list) -> MIMEText:
    logging.debug(f'Processing message {msg["Message-ID"]} {msg["Content-Type"]}')
    for part in msg.walk():
        if part.get_content_disposition() is not None:
            continue
        if part.get_content_maintype().lower() in ['application', 'audio', 'multipart']:
            continue
        if part.get_content_type().lower() == 'text/plain':
            newmsg = MIMEText(strip_quoteblocks(part.get_payload(decode=True).decode('utf-8', errors='replace') ))
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


def strip_quoteblocks(payload: str) -> str:
    outlines = []
    lines = payload.splitlines()
    for i in range(len(lines)):
        # look for series of 3 quoted lines together
        if (  # there's probably a more-elegant general way to do this for blocks of N quoted lines...
                (is_quoted_line(lines, i) and is_quoted_line(lines, i + 1) and is_quoted_line(lines, i + 2))
                or (is_quoted_line(lines, i) and is_quoted_line(lines, i + 1) and is_quoted_line(lines, i - 1))
                or (is_quoted_line(lines, i) and is_quoted_line(lines, i - 1) and is_quoted_line(lines, i - 2))
        ):
            outlines.append(i)
    for l in sorted(outlines, reverse=True):
        del lines[l]  # in-place modification
    return '\n'.join(lines)


def is_quoted_line(lines: list, i: int) -> bool:
    try:
        if '>' in lines[i][:3] and not '<' in lines[i]:
        #if '>' in lines[i] and not '<' in lines[i]:  # simplification
            return True
        else:
            return False
    except IndexError:
        return False


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    sys.exit(main(sys.argv[1], sys.argv[2]))
