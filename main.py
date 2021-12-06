#!/usr/bin/env python3

import sys
import mailbox
import email
from email.mime.text import MIMEText


def main(infile, outfile):
    mbox = mailbox.mbox(infile)
    outbox = mailbox.mbox(outfile)
    for m in mbox:
        msg: email.message = email.message_from_string(m)
        headers = []  # store outer headers for later use
        for h in msg.items():
            headers.append(h)
        lightmessage: email.message = lighten_message(msg, headers)
        outbox.add(lightmessage)
    outbox.flush()
    outbox.close()
    return 0


def lighten_message(msg: email.message, headers: list) -> email.message:
    for part in msg.walk():
        if part.is_multipart:
            continue
        else:
            if part.get_content_type().lower() == 'text/plain':
                outmsg = MIMEText(_subtype='plain')
                outmsg.set_payload(strip_quoteblocks(msg.get_payload()))
                for hname, hval in headers:
                    outmsg[hname] = hval  # copy headers from outermost message to output
                return outmsg


def strip_quoteblocks(lines: list) -> list:
    outlines = []
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
    return lines


def is_quoted_line(lines: list, i: int) -> bool:
    try:
        if '>' in lines[i][:3] and not '<' in lines[i]:
            return True
        else:
            return False
    except IndexError:
        return False


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
