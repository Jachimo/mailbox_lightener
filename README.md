# Mailbox Lightener

A set of scripts to "lighten" large mbox files by stripping all messages down to a single plain text component, while preserving important headers. Useful to reduce the size of mbox files prior to analysis where only the text component of the messages are used.

Written and tested on Python 3.9 on Mac OS X.

## Usage

**Run only on a copy of your data.** This is "developer grade" software. Make a backup first!

Normal usage: From inside the mailbox_lightener directory, run 
`python3 main.py inputmbox outputmbox`
where `inputmbox` is the path to your input mbox file (which is not required to end in .mbox), and `outputmbox` is the path to your desired output file.

The output file should either be an existing valid mbox file, or the name of a new file to be created.
**Note that if `outputmbox` exists and is a valid mbox, messages will be appended to it.**

The program works by parsing the input mailbox, which can be either a "classic mbox" (delimited solely by 'From ' lines) or an "mboxcl" style mailbox (with a Content-Length header included as part of each message's headers, specifying the following content payload length in bytes).  An attempt is made to determine the type of mailbox, but is not guaranteed to be correct (it looks only at the first message in the mailbox and assumes all others are similar).  The mailbox-determination logic can be overridden by manually specifying a type with the `-t` or `--type` flags; valid types are `mbox` or `mboxcl`.  No other mailbox types are currently supported, although adding those supported by the Python "mailbox" package (Maildir, MH, Babyl, and MMDF) would be relatively straightforward.

After parsing the input mailbox file into messages, each message is inspected via depth-first tree traversal of all MIME parts, until a part of type `text/plain` is encountered.  This part is then processed by stripping out blocks of quoted lines, in order to remove extraneous bottom-quoting.  The minimum number of quoted lines in a block that will be stripped defaults to 3, but can be configured up or down via the optional `--quoteblock` or `-q` flag.  Note that setting `-q 1` will result in _all_ quoted lines being stripped, including those that may be interleaved in the message body text.

If a message is encountered which does not contain a text/plain part, then a fallback attempt will be made to find a text/html part instead.  If an HTML part can be found, it is stripped of HTML tags to produce a (very rough) plain text version.  The resulting text is also fed through the quote-stripping logic, although there is no guarantee that HTML messages will be quoted in the normal '>' prefixed way.

The output message is constructed from the "stripped" plain text, with a selection of important headers copied from the original message, and the rest discarded.  Headers copied from the original to the output message include: 

* Received
* Date
* From
* To
* Subject
* Message-ID
* User-Agent

Additional headers can be preserved by editing the "keepheaders" list inside the add_headers() function in main.py.

Output messages are then written to the output mailbox file, which is formatted as a "classic" ('From ' line delimited, no Content-Length headers) mbox.

If successful, main.py returns 0, for use in wrapper scripts.

### Command Line Options

Running `python3 main.py --help` will produce a description of all options:

```commandline
usage: main.py [-h] [--type TYPE] [--quoteblock N] [--debug] infile outfile

"Lighten" a mbox file by stripping out non-text parts"

positional arguments:
  infile                Input mbox file to read from
  outfile               Output mbox file to write to (will append if exists)

optional arguments:
  -h, --help            show this help message and exit
  --type TYPE, -t TYPE  Manually specify input mbox type (mbox, mboxcl)
  --quoteblock N, -q N  Strip blocks of N+ quoted lines found together (default 3)
  --debug               Enable debug mode (very verbose output)
```

# License

Released under the GPLv3 or later.  For more information, see the LICENSE file.
