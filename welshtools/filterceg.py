#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter CEG Frequency Lists

Filters Frequency Lists from the Cronfa Electroneg o Gymraeg (especially for the
file "RawCounted (freq).txt") for use with Elizabeth Eden's TextFormatter and
Phonotactic Analyser.
"""

from . import shared
import os
import sys
import errno
import enchant
import codecs
from optparse import OptionParser

#Make sure errno.ENOPKG is defined in line with errno.h
try:
    errno.ENOPKG
except (AttributeError, NameError):
    errno.ENOPKG = 65

def main(args=None):
    """Run as a standalone script.

    You can simulate running the script internally by just passing a list with
    arguments in args; these will be treated as though they were the actual
    command line arguments."""
    #Determin name of current command
    if __name__ == "__main__":
        cmd_name = os.path.basename(sys.argv[0])
    elif args is not None and len(args) > 0:
        cmd_name = "welshtools %s" % args[0]
    elif len(sys.argv) > 1:
        cmd_name = "welshtools %s" % os.path.basename(sys.argv[1])
    else:
        cmd_name = __name__

    #Parse Command Line Arguments
    usage = "Usage: %s [options] SOURCE_FILE DEST_FILE" % cmd_name
    epilog = ("Reads SOURCE_FILE line by line and writes a reformatted and "
              "filtered list to DEST_FILE. This is intended to be run on the "
              "frequency lists from the Cronfa Electroneg o Gymraeg and not "
              "guaranteed to work with differently formatted input files. "
              "Please note that the SOURCE_FILE must be converted to utf-8 "
              "before running the script or the script will fail. The output "
              "file is always written in utf-8.")
    parser = OptionParser(usage=usage,
                          version="%s %s" % (cmd_name, shared.__version__),
                          epilog=epilog)
    parser.add_option("-f", "--format", dest="format", metavar="STR",
                      help=("Format to use for output file. {WORD} is replaced "
                            "with the word and {FREQ} with the frequency. This "
                            "can include the control characters \\\\, \\r, \\n,"
                            " and \\t.  Default: \"{WORD},{FREQ}\\n\""),
                      default="{WORD},{FREQ}\\n")
    parser.add_option("-s", "--strict", action="store_true", dest="strict",
                      help=("If --strict is specified, the script will not only"
                            " exclude words which are found in the English "
                            "dictionary or contain non-Welsh orthographic "
                            "characters, but will also strip acute accents and "
                            "remove contractions (e.g. 'r), and words which are"
                            " hyphenated or contain j or J."))
    parser.add_option("-S", "--summary", action="store_true",
                      dest="print_summary", help=("Print a summary of how many "
                        "entries were read, written and excluded at the end "
                        "of the script. Note that this ignores --quiet."))
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                      help="Supress all command line output except for errors.")

    #Parse arguments
    if args is None:
        (opts, args) = parser.parse_args()
    else:
        (opts, args) = parser.parse_args(args)
    if len(args) != 2:
        print("Error: This command requires two arguments. Try `%s --help'." % cmd_name)
        return errno.EINVAL
    if opts.quiet:
        opts.verbose = False
    else:
        opts.verbose = True
    if opts.verbose:
        print("Opening source and destination files...  ", end="")
    try:
        fin = codecs.open(args[0], "r", "utf8")
        fin_size = os.path.getsize(args[0])
    except IOError as ex:
        print("\nError: Could not open SOURCE_FILE ("+args[0]+") for reading:", ex)
        return errno.EIO
    try:
        fout = codecs.open(args[1], "w+", "utf8")
    except IOError as ex:
        print("\nError Could not open DEST_FILE ("+args[1]+") for writing:", ex)
        return errno.EIO
    if opts.verbose:
        print("Done.")

    #Load dictionaries
    if opts.verbose:
        print("Loading Enchant dictionaries for en_US, en_GB and cy_GB...  ", end="")
    try:
        enchant.set_param("enchant.myspell.dictionary.path", "./geiriadur-cy/dictionaries")
        d_us = enchant.Dict("en_US")
        d_gb = enchant.Dict("en_GB")
        d_cy = enchant.Dict("cy_GB")
    except Exception as ex: #pylint: disable=broad-except
        print("\nError: Could not open Enchant dictionaries (en_US, en_GB, cy_GB):", ex)
        return errno.ENOPKG
    if opts.verbose:
        print("Done.")

    #Set string of allowed characters
    welsh_chrs_strict = set('ABCDEFGHILMNOPRSTUWYabcdefghilmnoprstuwy\\/+%')
    welsh_chrs_all = set((
        'ABCDEFGHIJLMNOPRSTUWYabcdefghijlmnoprstuwy'
        'ÄËÏÖÜẄŸäëïöüẅÿÂÊÎÔÛŴŶâêîôûŵŷÁÉÍÓÚẂÝáéíóúẃýÀÈÌÒÙẀỲàèìòùẁỳ'
        '\'-'
    ))

    #Set mappings from CEG transcription to UTF8
    if opts.strict:
        if opts.verbose:
            print("Mapping mode: strict.")
        #Strip /, map % onto ¨, map \ onto `, and map + onto ^
        mapping = {
            '/': '',
            'a%':'ä', 'e%':'ë', 'i%':'ï', 'o%':'ö', 'u%':'ü', 'y%':'ÿ', 'w%':'ẅ',
            'A%':'Ä', 'E%':'Ë', 'I%':'Ï', 'O%':'Ö', 'U%':'Ü', 'Y%':'Ŷ', 'W%':'Ẅ',
            'a\\':'à', 'e\\':'è', 'i\\':'ì', 'o\\':'ò', 'u\\':'ù', 'y\\':'ỳ', 'w\\':'ẁ',
            'A\\':'À', 'E\\':'È', 'I\\':'Ì', 'O\\':'Ò', 'U\\':'Ù', 'Y\\':'Ỳ', 'W\\':'Ẁ',
            'a+':'â', 'e+':'ê', 'i+':'î', 'o+':'ô', 'u+':'û', 'y+':'ŷ', 'w+':'ŵ',
            'A+':'Â', 'E+':'Ê ', 'I+':'Î', 'O+':'Ô', 'U+':'Û', 'Y+':'Ŷ', 'W+':'Ŵ'
        }
    else:
        if opts.verbose:
            print("Mapping mode: relaxed.")
        #Map / onto ´, map % onto ¨, map \ onto `, and map + onto ^
        mapping = {
            'a/':'á', 'e/':'é', 'i/':'í', 'o/':'ó', 'u/':'ú', 'y/':'ý', 'w/':'ẃ',
            'A/':'Á', 'E/':'É', 'I/':'Í', 'O/':'Ó', 'U/':'Ú', 'Y/':'Ý', 'W/':'Ẃ',
            'a%':'ä', 'e%':'ë', 'i%':'ï', 'o%':'ö', 'u%':'ü', 'y%':'ÿ', 'w%':'ẅ',
            'A%':'Ä', 'E%':'Ë', 'I%':'Ï', 'O%':'Ö', 'U%':'Ü', 'Y%':'Ŷ', 'W%':'Ẅ',
            'a\\':'à', 'e\\':'è', 'i\\':'ì', 'o\\':'ò', 'u\\':'ù', 'y\\':'ỳ', 'w\\':'ẁ',
            'A\\':'À', 'E\\':'È', 'I\\':'Ì', 'O\\':'Ò', 'U\\':'Ù', 'Y\\':'Ỳ', 'W\\':'Ẁ',
            'a+':'â', 'e+':'ê', 'i+':'î', 'o+':'ô', 'u+':'û', 'y+':'ŷ', 'w+':'ŵ',
            'A+':'Â', 'E+':'Ê ', 'I+':'Î', 'O+':'Ô', 'U+':'Û', 'Y+':'Ŷ', 'W+':'Ŵ'
        }

    #Parse format string
    if opts.verbose:
        print("Format string:", '"'+opts.format+'".')
    format_mappings = {'\\\\':'\\', '\\r':"\r", '\\n':"\n", '\\t':"\t"}
    for k, v in format_mappings.items():
        opts.format = opts.format.replace(k, v)

    #Process files
    if opts.verbose:
        print("Processing word list...")
        shared.progress(0, fin_size)
    count_inlines = 0
    count_outlines = 0
    for line in fin:
        count_inlines += 1
        #Split line into freq and word
        (freq, word) = line.strip().split("\t")

        #IF STRICT: Skip words with hyphens and non-Welsh characters before mapping
        if opts.strict and not set(word).issubset(welsh_chrs_strict):
            continue

        #Map CEG transcriptions onto UTF8 characters.
        for k, v in mapping.items():
            word = word.replace(k, v)

        #Skip words which have non-Welsh characters after mapping
        if not set(word).issubset(welsh_chrs_all):
            continue

        #Skip words which are more than one chr and in the English dictionaries
        #unless they are in the Welsh dictionary
        if not d_cy.check(word):
            if len(word) > 1 and (d_us.check(word) or d_gb.check(word)):
                continue

        #Format word
        formatted = opts.format.format(WORD=word, FREQ=freq)

        #Write to output file
        count_outlines += 1
        fout.write(formatted)

        #Show progress
        if opts.verbose:
            shared.progress(fin.tell(), fin_size)
    if opts.verbose:
        print("\nDone.")
    if opts.print_summary:
        print("Summary:")
        print("  Entries in Source: %s" % count_inlines)
        print("  Entries in Output: %s" % count_outlines)
        print("  Excluded Entries:  %s" % (count_inlines-count_outlines))

    #Close input and output files
    fin.close()
    fout.close()

    #Return clean exit code
    return 0

if __name__ == '__main__':
    sys.exit(main())
