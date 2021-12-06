#!/usr/bin/env python3

import sys
import os
import mailbox
import email
from email.mime.multipart import MIMEMultipart


def main(infile, outfile):
    mbox = parse_mbox(infile)
    outbox = mailbox.mbox(of)
    for m in mbox:
        msg: email.message = email.message_from_string(m)
        lightmessage: email.message = lighten_message(msg)
        outbox.add(lightmessage)
    outbox.flush()
    outbox.close()
    return 0


def lighten_message(msg: email.message) -> email.message:
    if msg.is_multipart:
        for part in msg.walk():
            return lighten_message(part)  # descend recursively
    else:
        if msg.get_content_maintype().lower() == 'text/plain':
            msg.set_payload(strip_quoteblocks(msg.get_payload()))
            return msg


def strip_quoteblocks(lines):
    outlines = []
    for i in range(len(lines)):
        # look for series of 3 quoted lines together
        if (
                (is_quoted_line(lines, i) and is_quoted_line(lines, i + 1) and is_quoted_line(lines, i + 2))
                or (is_quoted_line(lines, i) and is_quoted_line(lines, i + 1) and is_quoted_line(lines, i - 1))
                or (is_quoted_line(lines, i) and is_quoted_line(lines, i - 1) and is_quoted_line(lines, i - 2))
        ):
            outlines.append(i)
    for l in sorted(outlines, reverse=True):
        del lines[l]  # in-place modification
    return lines


def is_quoted_line(lines, i):
    try:
        if '>' in lines[i][:3] and not '<' in lines[i]:
            return True
        else:
            return False
    except IndexError:
        return False


def is_quoted_block(lines, blocksize, i):
    lookahead = blocksize - 1
    if i < (len(lines) - lookahead):
        for j in range(lookahead):
            if not is_quoted_line(lines, i+j):
                return False
            else:
                continue
        return True
    else:  # last N lines of file where N = blocksize
    lookbehind = len(lines) - (i + blocksize)  # should be negative
    lookahead = lookahead + lookbehind



def parse_mbox(infile):
    messages = []
    mbox = mailbox.mbox(infile)
    for msg in mbox:
        messages.append(msg)
    return messages


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
