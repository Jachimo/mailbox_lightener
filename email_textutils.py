#!/usr/bin/env python3
"""Clean up text emails by stripping block-quoted lines and other garbage"""

import sys
from typing import List
import re

testdata = """LOREM IPSUM

> Lorem ipsum dolor sit amet, consectetur adipiscing elit

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed
do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation
ullamco laboris nisi ut aliquip ex ea commodo consequat.

>> Duis aute irure dolor in reprehenderit in voluptate velit
>> esse cillum dolore eu fugiat nulla pariatur. Excepteur sint
> occaecat cupidatat non proident, sunt in culpa qui officia
> deserunt mollit anim id est laborum.

Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint
occaecat cupidatat non proident, sunt in culpa qui officia
deserunt mollit anim id est laborum.

<p>Duis aute irure dolor in reprehenderit</p>

* Duis aute irure dolor in reprehenderit
* Sunt in culpa qui officia
  <> Cupidatat
  <> Occaecat
* Ad minim veniam

On Quartidi Ventôse, Ullamco Laboris wrote:
> Voluptate Velit
> Ullamco Laboris
> Irure Dolor
"""


def strip_quoteblocks(instr: str, blocksize: int) -> str:
    """Strip blocks of more than blocksize (int) quoted lines together"""
    lines: List[str] = instr.splitlines()
    dellist: List[int] = []
    badcount: List[int] = []
    i = 0
    for i in range(len(lines)):
        result = is_quoted_line(lines[i])
        if not result:
            if len(badcount) >= blocksize:
                dellist.extend(badcount)
            badcount = []
        if result:
            badcount.append(i)
        i += 1
    if len(badcount) >= blocksize:  # At EOF
        dellist.extend(badcount)
    for j in sorted(dellist, reverse=True):
        del lines[j]
    joined = '\n'.join(lines)
    return joined.strip()


def strip_trailing_quoteblocks(instr: str, blocksize: int) -> str:
    """Strip blocks of more than blocksize quoted lines together, but only if they are at the end of the file"""
    lines: List[str] = instr.strip().splitlines()
    dellist: List[int] = []
    badcount: List[int] = []
    i = 0
    for i in range(len(lines)):
        result = is_quoted_line(lines[i])
        if not result:
            badcount = []
        if result:
            badcount.append(i)
        i += 1
    if len(badcount) >= blocksize:  # Only strip quote blocks that occur at EOF
        dellist.extend(badcount)
    for j in sorted(dellist, reverse=True):
        del lines[j]
    joined = '\n'.join(lines)
    return joined.strip()


def is_quoted_line(line: str) -> bool:
    """Determine if a plaintext line is quoted text; not safe for HTML components."""
    if '>' in line[:3] and '<' not in line[:3]:
        return True
    else:
        return False


def strip_quoteheader(instr: str) -> str:
    lines: List[str] = instr.splitlines()
    dellist: List[int] = []
    i = 0
    for i in range(len(lines)):
        if re.match("On .*wrote:", lines[i]):
            dellist.append(i)
        i += 1
    for j in sorted(dellist, reverse=True):
        del lines[j]
    joined = '\n'.join(lines)
    return joined.strip()


if __name__ == "__main__":
    print(strip_quoteheader(strip_quoteblocks(testdata, 3)))
    sys.exit()
