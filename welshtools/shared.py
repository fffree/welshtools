# -*- coding: utf-8 -*-
"""
Shared functions for the Welsh language utilities module
"""

__author__ = "Florian Breit"
__contact__ = "Florian Breit <florian.breit.12@ucl.ac.uk>"
__copyright__ = "(c) 2015 Florian Breit"
__license__ = "GNU AGPL v3"
__date__ = "18 May 2015"
__version__ = "1.0.0"

import sys
import time
import unicodedata

def chunks(lst, chunk_size):
    """Yield chuck_size pieces of list."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i+chunk_size]

def estimate_remaining_time(count, total, start_timestamp):
    """Estimate the remaining time based on count of total complete and time
    elapsed since beginning."""
    #Calculate time remaining in seconds
    time_elapsed = time.time()-start_timestamp
    time_per_unit = float(time_elapsed)/float(count)
    time_required = time_per_unit*float(total)
    time_remaining = time_required-time_elapsed
    #Format into H:m:s string
    string_remaining = "%dh%02dm%02ds" % seconds_to_hms(time_remaining)
    return string_remaining

def is_welsh_utf8(string):
    """Test whether a given UTF8 string only contains characters that are
    part of the Welsh alphabet (Whitespace and punctuation are ignored)."""
    #Set string of allowed characters
    welsh_chars = set((
        'ABCDEFGHIJLMNOPRSTUWYabcdefghijlmnoprstuwy'
        'ÄËÏÖÜẄŸäëïöüẅÿÂÊÎÔÛŴŶâêîôûŵŷÁÉÍÓÚẂÝáéíóúẃýÀÈÌÒÙẀỲàèìòùẁỳ'
        '\'-'
    ))
    string = strip_punctuation(string)
    for char in string:
        if not char in welsh_chars:
            return False
    return True

def progress(count, total, suffix=''):
    """Show a progress bar; percentage of count/total."""
    bar_len = 40
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = 'Ã¢â€“â€˜' * filled_len + ' ' * (bar_len - filled_len) #pylint: disable=blacklisted-name

    sys.stdout.write('  Progress: [%s] %s%s%s\r' % (bar, percents, '%', suffix))

def seconds_to_hms(seconds):
    """Convert an amount of time given in seconds to the format (H, m, s)"""
    (minutes, seconds) = divmod(seconds, 60)
    (hours, minutes) = divmod(minutes, 60)
    return (hours, minutes, seconds)

def strip_punctuation(string):
    """Strip a UTF8 string of all punctuation and space symbols."""
    #Punctuation
    string = "".join(c for c in string if not unicodedata.category(c).startswith('P'))
    #Whitespace
    string = "".join(c for c in string if not unicodedata.category(c).startswith('Z'))
    #Control Characters (\r, \n, etc.)
    string = "".join(c for c in string if not unicodedata.category(c).startswith('C'))
    return string
