#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic Phonemic Transcription of Welsh

This script takes either a single string or a frequency list (Format: word,freq
and a newline for each word) and transcribes it into a phonemic transcription
based on the rules in Briony Williams (1994) "Welsh letter-to-sound rules:
rewrite rules and two-level rules compared".

Requires both the Festival speech synthesis software and Canolfan Bedwyr's Welsh
voice for Festival (voice_cb_cy_llg_diphone) to be installed.
"""

from . import shared
import os
import sys
import errno
import codecs
import unicodedata
import tempfile
import time
import random
import string
import subprocess
import multiprocessing
import shutil
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

    #Check number of available CPU cores, this will influence the -p default.
    try:
        cpu_count = multiprocessing.cpu_count() #pylint: disable=no-member
    except NotImplementedError:
        cpu_count = 4 #Conservative estimate = quad core but should be fine
                      #even with fewer cores, just slow

    #Check python version (shututil.which is only available from >3.3)
    if sys.version_info >= (3, 3):
        #Check that festival is installed and executable
        if shutil.which("festival") is None:
            print(("Error: Cannot find find festival executable. "
                   "Please make sure you have Festival installed."))
            return errno.ENOPKG

    #Show and Parse Command Line Arguments
    usage = ("Usage: %s [options] SOURCE_FILE DEST_FILE\n"
             "       %s -i STRING") % (cmd_name, cmd_name)
    epilog = ("Reads SOURCE_FILE line by line and writes a new list to "
              "DEST_FILE where each word is transcribed in IPA. SOURCE_FILE "
              "should be of the format `word,frequency', with one word per "
              "line; DEST_FILE will be the same format, except word being "
              "replaced by the transcription. \n"
              "If the option -i is specified, the script takes a single word "
              "as an argument and prints the IPA transcription of that word.")
    parser = OptionParser(usage=usage,
                          version="%s %s" % (cmd_name, shared.__version__),
                          epilog=epilog)
    parser.add_option("-i", "--inline", dest="word", metavar="STR",
                      help=("Inline mode. Print the IPA transcription of STR "
                            "and exit. Ignores all other arguments and does not "
                            "read or write any files.")
                     )
    parser.add_option("-p", "--processes", dest="nprocs", metavar="N",
                      help=("Maximum number of child processes to spawn for "
                            "processing in file-based mode. More is be faster, "
                            "but requires more system resources. Default: %i.")
                            % cpu_count,
                      default=cpu_count)
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
                      help="Supress all command line output except for errors.",
                      default=False)

    #Parse arguments
    if args is None:
        (opts, args) = parser.parse_args()
    else:
        (opts, args) = parser.parse_args(args)
    if opts.quiet:
        opts.verbose = False
    else:
        opts.verbose = True
    opts.nprocs = int(opts.nprocs)

    #Single word mode
    if opts.word:
        #Just transcribe and print transcription
        word = transcribe_string(opts.word)
        print(word)
        return 0
    #File based mode
    #Check number of arguments, should be two: SOURCE_FILE and DEST_FILE
    if len(args) != 2:
        print("Error: This command requires two arguments. Try `%s --help'." % cmd_name)
        return errno.EINVAL
    else:
        try:
            transcribe_file(args[0], args[1], opts.nprocs, opts.verbose)
        except IOError as ex:
            print("\n%s" % ex)
            return errno.EIO
        #Return exit code
        return 0

def transcribe_file(infile, outfile, nprocs=1, verbose=False):
    """Transcribe the file `infile' line by line and write the results to the
    file `outfile'. Uses multiprocessing to speed things up. nprocs should be
    set to the number of available CPU cores. If verbose is True the script
    prints progress information."""
    #Open input and output file streams
    if verbose:
        print("Opening source and destination files...", end="")
    try:
        fin = codecs.open(infile, "r", "utf8")
    except IOError as ex:
        raise IOError("Error: Could not open SOURCE_FILE ("+infile+") for reading: %s" % ex)
    try:
        fout = codecs.open(outfile, "w+", "utf8")
    except IOError as ex:
        raise IOError("Error Could not open DEST_FILE ("+outfile+") for writing: %s" % ex)
    if verbose:
        print("Done.")
    #Read in the whole input file (need this in memory for multiprocessing)
    if verbose:
        print("Reading source file to memory...", end="")
    fin_lines = []
    for line in fin:
        fin_lines.append(line)
    fin.close() #Close source file, as we no longer need it
    fin_line_count = len(fin_lines)
    if verbose:
        print("Done.")
    #Transcribe file line by line
    if verbose:
        print("Processing word list...")
        print("  Number of processes: %d" % nprocs)
        shared.progress(0, fin_line_count, " (ETA: ????)")
    count_lines = 0
    start_time = time.time()
    #Spawn pool with 10 processes and map word list in chunks of process n
    pool = multiprocessing.Pool(processes=nprocs)
    for chunk in shared.chunks(fin_lines, nprocs):
        count_lines += len(chunk)
        fout_lines = pool.map(transcribe_line, chunk)
        for line in fout_lines:
            fout.write(line) #Write all the transcribed lines to fout()
        if verbose:
            eta = shared.estimate_remaining_time(count_lines, fin_line_count, start_time)
            shared.progress(count_lines, fin_line_count, " (ETA: %s)" % eta)
    end_time = time.time()
    if verbose:
        print("\nDone.")
        print("Successfully transcribed %s words in " % count_lines, end='')
        print("%dh%02dm%02ds total." % shared.seconds_to_hms(end_time-start_time))
    #Close output file
    fout.close()

def transcribe_line(line, timeout=30):
    """Takes a line of the form `word,freqEOL', passes word to
    transcribe_string() and returns a line of the form
    `transcription,freq,wordEOL'. Intended as a mapping function for
    use with multiprocess.Pool.map()."""
    #Reset the current process as non-daemonic, so it is allowed to spawn
    #a child process for festival. (Potentially unsafe?)
    proc = multiprocessing.current_process()
    proc.daemon = False
    #Let festival transcribe the word
    (word, count) = line.strip().split(',')
    transcription = transcribe_string(word, timeout)
    ##For testing consider using this code instead of actual transcription:
    ##word = word[::-1] #Just reverse the word...
    ##transcription = "_"+word  #Add initial underscore for easy inspection...
    ##time.sleep(0.01) #Pretend the process takes a while..
    return "%s,%s,%s\r\n" % (transcription, count, word)

def transcribe_string(string, timeout=5):
    """Transcribes a string of orthographic Welsh to IPA using Festival."""
    #Map string to Festival compatible format
    string = map_utf8_to_festival(string)
    with TempFile('festival-', '.segs') as tempf:
        command = "(voice_cb_cy_llg_diphone)\n" \
                  '(utt.save.segs (utt.synth (Utterance Text "{TEXT}")) "{PATH}")\n' \
                  "(exit)\n\n"
        string = festival_escape(string)
        path = festival_escape(tempf.get_path())
        command = command.format(TEXT=string, PATH=path)
        #subprocess.call(['festival', '--pipe'], stdin)
        proc = subprocess.Popen(['festival', '--pipe'], stdin=subprocess.PIPE)
        proc.stdin.write(bytes(command, "utf8"))
        proc.stdin.flush()
        #Terminate proc after 5 seconds (=20x0.25 seconds) if not terminated
        timeout_loops = int(timeout/0.1)
        for i in range(timeout_loops+1):
            status = proc.poll()
            if status != None: #Proc has finished
                break
            else:                    #Proc still going
                if i < timeout_loops:
                    time.sleep(0.1) #Wait 0.1s and try again
                else:
                    proc.kill() #Kill process, raise exception
                    print("Festivl timed out after %ds" % (timeout_loops*0.1))
                    raise Exception(("Festival subprocess timed out (Timeout: "
                                     "%ss, Command: %s).") % (timeout, command))
        #Process has terminated, read tempfile
        with open(tempf.get_path(), "r") as fh:
            output = []
            for line in fh:
                output.append(line)
    #Now process the output to remove all but the transcription symbols
    transcription = ""
    for line in output:
        transcription += line.split()[-1] + " " #Strip all but the last field
    #Now we need to put the transcription into IPA
    transcription = map_festival_to_ipa(transcription, encode_labialisation=False)
    return transcription

def festival_escape(string):
    """Escapes a string so it can be passed to festival in double quotes."""
    escape_mapping = [
        ['\\', '\\\\'], #Must be first to avoid double escaping other escapes
        ['"',  '\\"']
    ]
    for item in escape_mapping:
        string = string.replace(item[0], item[1])
    return string

def is_welsh_festival_string(string):
    """Test whether a given string only contains characters that are accepted
    by the festival speech synthesis system (Whitespace and punctuation are
    ignored)."""
    #Set string of allowed characters
    festival_chrs = set('ABCDEFGHILMNOPRSTUWYabcdefghilmnoprstuwy\\/+:')
    string = shared.strip_punctuation(string)
    for c in string:
        if not c in festival_chrs:
            return False
    return True

def map_utf8_to_festival(string):
    """Map a Welsh UTF8 string onto a Festival compatible ASCII string."""
    #Put string into NFKD (Normalization Form Compatibility Decomposition)
    string = unicodedata.normalize('NFKD', string)
    #Set mappings from UTF8 to Festival format
    utf8_to_festival_mapping = {
        chr(770) : "+",  #^ --> +
        chr(776) : ":",  #¨ --> :
        chr(769) : '/',  #´ --> /
        chr(768) : '\\', #` --> \
    }
    #Map diacritics to Festival characters
    for k, v in utf8_to_festival_mapping.items():
        string = string.replace(k, v)
    #Stip non-utf8 characters and return
    return str(string.encode('ASCII', 'ignore'), encoding="ASCII")

def map_festival_to_ipa(string, encode_tense_lax=False, encode_labialisation=True, encode_long_schwa=True):
    """Map a Welsh Festival segment string onto an IPA string.

    Maps a Festival segmentation string (as in the Utterance Segment
    represenation) to IPA characters.

    There are two options that can be specified to improve on the transcription,
    (1) encode_tense_lax if True encodes short vowels as lax and long ones as
    tense.
    (2) If Labialisation is False, then labialised /l,r,n/ are
    encoded as sequences of /lw,rw,nw/ rather than phonemic /lÃƒÅ Ã‚Â·,rÃƒÅ Ã‚Â·,nÃƒÅ Ã‚Â·/. By default
    it returns the representations envisaged by Briony Williams in her original
    LTS rules (i.e. no tense-lax distinction, and labialisation is phonemic).
    (3) If EncodeLongSchwa is False then the transcription reduces long schwa
    /Ãƒâ€°Ã¢â€žÂ¢Ãƒâ€¹Ã‚Â/ from the transcription to short /Ãƒâ€°Ã¢â€žÂ¢/. It is debated whether there is a
    long schwa in Welsh; the main current textbooks (Hannahs 2013, Ball and
    Williams 2001) tend to say there isn't.
    """
    #Original mappings for characters documented in Festival LTS file (gogwel.scm)
    festival_to_ipa_mapping = {
        'i'   :  'i',   #Short [i]
        'e'   :  'e',   #Short [e]
        'a'   :  'a',   #Short [a]
        'o'   :  'o',   #Short [o]
        'u'   :  'u',   #Short [u]
        'y'   :  'ɨ',   #Short [high central unrounded V]
        '@'   :  'ə',   #Short [schwa]
        'ii'  :  'iː',  #Long [i]
        'ee'  :  'eː',  #Long [i]
        'aa'  :  'aː',  #Long [i]
        'oo'  :  'oːː',  #Long [i]
        'uu'  :  'uː',  #Long [i]
        'yy'  :  'ɨː',  #Long [i]
        '@@'  :  'əː',  #Long [i]
        'oa'  :  'oa',  #Diphthong [oa (as in English "paw"]
        'oi'  :  'oi',  #Diphthong [oi]
        'ou'  :  'ou',  #Diphthong [ou]
        'oy'  :  'oɨ',  #Diphthong [oy]
        'ai'  :  'ai',  #Diphthong [ai]
        'au'  :  'au',  #Diphthong [au]
        'ay'  :  'aɨ',  #Diphthong [ay (corresponds to orth "au"]
        'aay' :  'aːɨ', #Diphthong [aay (corresponds to orth "ae"]
        'uy'  :  'uɨ',  #Diphthong [uy]
        'iu'  :  'iu',  #Diphthong [iu]
        'ei'  :  'ei',  #Diphthong [ei]
        'eu'  :  'eu',  #Diphthong [eu]
        'ey'  :  'eɨ',  #Diphthong [ey]
        'ye'  :  'ɨe',  #Diphthong [yu]
        'p'   :  'p',   #Consonant [p]
        't'   :  't',   #Consonant [t]
        'k'   :  'k',   #Consonant [k]
        'b'   :  'b',   #Consonant [b]
        'd'   :  'd',   #Consonant [d]
        'g'   :  'g',   #Consonant [g]
        'f'   :  'f',   #Consonant [f]
        'th'  :  'θ',   #Consonant [theta]
        'h'   :  'h',   #Consonant [h]
        'x'   :  'χ',   #Consonant [x (voiceless uvular fricative)]
        'v'   :  'v',   #Consonant [v]
        'dh'  :  'ð',   #Consonant [edh]
        's'   :  's',   #Consonant [s]
        'z'   :  'z',   #Consonant [z]
        'sh'  :  'ʃ',   #Consonant [voiceless palato-alveolar fricative]
        'zh'  :  'ʒ',   #Consonant [voiced palato-alveolar fricative]
        'ch'  :  't͡ʃ',  #Consonant [voiceless palato-alveolar affricate]
        'jh'  :  'd͡ʒ',  #Consonant [voiced palato-alveolar affricate]
        'lh'  :  'ɬ',   #Consonant [voiceless alveolar lateral fricative]
        'rh'  :  'r̥ʰ', #Consonant [voiceless alveolar apical trill]
        'l'   :  'l',   #Consonant [l]
        'r'   :  'r',   #Consonant [r]
        'w'   :  'w',   #Consonant [w]
        'j'   :  'j',   #Consonant [voiced palatal approximant]
        'm'   :  'm',   #Consonant [m]
        'n'   :  'n',   #Consonant [n]
        'ng'  :  'ŋ',   #Consonant [voiced velar nasal]
        'mh'  :  'm̥',  #Consonant [voiceless m]
        'nh'  :  'n̥',  #Consonant [voiceless n]
        'ngh' :  'ŋ̊',  #Consonant [voiceless velar nasal]
        'lw'  :  'lʷ',  #Consonant [labialised voiced alveolar lateral approximant]
        'nw'  :  'nʷ',  #Consonant [labialised voiced alveolar nasal stop]
        'rw'  :  'rʷ',  #Consonant [labialised voiced alveolar central approximant]
    }
    #Additional mappings that seem to be required but are not documented in Festival
    festival_to_ipa_fixes = {
        'hh'  :  'h',
        'yu'  :  'ɨu',
        'sil' :  ' ',   #Silence
        '#'   :  '',    #Phrase Edge Marker? Always at the start of transcription
    }
    festival_to_ipa_mapping.update(festival_to_ipa_fixes)
    #Tense-Lax augmentation
    if encode_tense_lax:
        festival_tense_lax_augmentation = {
            'i'   :  'ɪ',   #Short Lax [i]
            'e'   :  'ɛ',   #Short Lax [e]
            'a'   :  'a',   #Short Lax [a]
            'aa'  :  'ɑː',  #Long Tense [a]
            'o'   :  'ɔ',   #Short Lax [o]
            'u'   :  'ʊ',   #Short Lax [u]
        }
        festival_to_ipa_mapping.update(festival_tense_lax_augmentation)
    #Augmentation to remove labialised phonemes
    if encode_labialisation is False:
        festival_labialisation_augmentation = {
            'lw'  :  'lw',
            'nw'  :  'nw',
            'rw'  :  'rw',
        }
        festival_to_ipa_mapping.update(festival_labialisation_augmentation)
    #Augmentation to remove long schwa
    if encode_long_schwa is False:
        festival_long_schwa_augmentation = {
            '@@'  :  'ə',
        }
    #Now transcribe the string
    transcription = ""
    for item in string.split():
        try:
            transcription += festival_to_ipa_mapping[item.strip()]
        except KeyError as ex:
            ex.args[0] = ("The symbol `%s' was encountered, but it is not "
                         "specified in the Festival to IPA mapping.") % item
            raise
    return transcription.strip()

class TempFile:
    """Create a temporary file context that can be passed on to other processes.

    Creates a temporary file object, but does not open it. The temporary
    file is deleted when the object is destroyed (e.g. garbage collection).

    This class will normally be called using the with statement, e.g.
    with TempFile() as tempf: pass
    If you construct it directly you have to make sure to delete the file when
    you're done by calling TempFile.destroy() yourself. This is done
    automatically using the with statement.
    """
    def __init__(self, prefix='', suffix=''):
        self.destroyed = False
        self.prefix = prefix
        self.suffix = suffix
        self.tempdir = tempfile.gettempdir()
        while True:
            self.randomstring = self.random_string()
            self.filename = self.prefix + self.randomstring + self.suffix
            self.filepath = self.tempdir + os.path.sep + self.filename
            if not os.path.isfile(self.filepath):
                try:
                    fh = open(self.filepath, "w+")
                    fh.close()
                except IOError:
                    continue
                break
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.destroy()
    def destroy(self):
        """Destroys the temporary file object."""
        if not self.destroyed:
            os.unlink(self.filepath)
            self.destroyed = True
    def random_string(self, length=5):
        """Generates a random string for use in temporary file names."""
        return ''.join(random.SystemRandom().choice( #Can line breaks be avoided?
                          string.ascii_uppercase+string.digits
                       ) for i in range(length))
    def get_filename(self):
        """Returns the name of the temporary file."""
        return self.filename
    def get_path(self):
        """Returns the full path to the temporary file."""
        return self.filepath

if __name__ == '__main__':
    sys.exit(main())
