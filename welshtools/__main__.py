#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities for working with Welsh language data
"""

from . import shared
from . import filterceg
from . import transcription
import sys
import errno

def main():
    """Provide command line interface to welshtools."""
    if len(sys.argv) < 2:
        print("Error: This script requires at least two arguments. Try `welshtools --help.'")
        return errno.EINVAL
    if sys.argv[1] in ("--help", "-h", "/?"):
        print(("Usage: welshtools command [options] [args]\n"
               "\n"
               "Commands:\n"
               "  filterceg       Filter and reformat CEG frequency lists\n"
               "  transcription   Transcribe orthographic Welsh into IPA\n"
               "\n"
               "To see the options and arguments for individual commands try "
               "`welshtools command --help' (e.g. `welshtools transcription --help')."
               ))
        print("End of help.")
        return 0
    if sys.argv[1] in ("--version", "-v"):
        print("welshtools %s" % shared.__version__)
        return 0
    if sys.argv[1] == "--list-commands": #Can be invoked for bash autocomplete
        print("filterceg transcription")
        return 0
    if sys.argv[1] == "filterceg":
        return filterceg.main(sys.argv[1:])
    if sys.argv[1] == "transcription":
        return transcription.main(sys.argv[1:])
    print("Error: Unknown command `%s'. Try `%s --help'." % (sys.argv[1], sys.argv[0]))
    print(sys.argv)
    return 0

if __name__ == '__main__':
    sys.exit(main())
