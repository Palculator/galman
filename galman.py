#!/usr/bin/python
"""
Utility to filter large collections of assorted media files, especially focused
on retaining information on previously black-/whitelisted files to avoid
having to re-filter duplicates.
"""

import argparse
import hashlib
import os
import os.path
import shutil
import threading
import sys

import mpv

from random import shuffle
from time import sleep


HASH_LENGTH = 32
SIZE_LENGTH = 8

IGNORED_EXT = set([
    '.tags',
    '.swf',
    '.json'
])

BLACKLIST_FILE = '.blacklist'
WHITELIST_FILE = '.whitelist'

AIRLOCK_DIR = '.airlock'
GALLERY_DIR = 'Gallery'

BLACKLIST_KEY = '8'
WHITELIST_KEY = '4'
QUIT_KEY = 'q'

class Collection:
    """
    Class to encapsulate a media collection and its corresponding data. Its
    main property is the location of the collection, but the class offers
    unified access to derived properties of a collection: Its blacklist and
    whitelist files and the airlock and gallery directories. The class makes
    sure these files exist for proper operation and implements __enter__ and
    __exit__ functions that ensure black-/whitelists are saved upon exit.
    """

    def __init__(self, col):
        self.directory = col

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        blacklist = os.path.join(self.directory, BLACKLIST_FILE)
        if not os.path.isfile(blacklist):
            open(blacklist, 'a').close()

        whitelist = os.path.join(self.directory, WHITELIST_FILE)
        if not os.path.isfile(whitelist):
            open(whitelist, 'a').close()

        airlock = os.path.join(self.directory, AIRLOCK_DIR)
        if not os.path.isdir(airlock):
            os.mkdir(airlock)

        gallery = os.path.join(self.directory, GALLERY_DIR)
        if not os.path.isdir(gallery):
            os.mkdir(gallery)

        self.blacklist = read_file_keys(blacklist)
        self.whitelist = read_file_keys(whitelist)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        blacklist_file = os.path.join(self.directory, BLACKLIST_FILE)
        whitelist_file = os.path.join(self.directory, WHITELIST_FILE)
        write_file_keys(blacklist_file, self.blacklist)
        write_file_keys(whitelist_file, self.whitelist)

    def is_blacklisted(self, fkey):
        """
        Returns True iff the file identified by the given key is blacklisted.
        """
        return fkey in self.blacklist

    def is_whitelisted(self, fkey):
        """
        Returns True iff the file identified by the given key is whitelisted.
        """
        return fkey in self.whitelist

    def blacklist_file(self, fkey):
        """
        Retains the file identified by the given key to be blacklisted.
        """
        self.blacklist.update([fkey])

    def whitelist_file(self, fkey):
        """
        Retains the file identified by the given key to be whitelisted.
        """
        self.whitelist.update([fkey])

    def get_airlock(self):
        """
        Returns the path to the airlock directory of this collection.
        """
        return os.path.join(self.directory, AIRLOCK_DIR)

    def get_gallery(self):
        """
        Returns the path to the gallery directory of this collection.
        """
        return os.path.join(self.directory, GALLERY_DIR)


def parse_command_line():
    """Parses the commandline parameters and returns a dictionary of them."""
    parser = argparse.ArgumentParser()

    help_str = \
        'The collection folder to sort files into. ' \
        'If the folder does not exist, it will be created along with the ' \
        'necessary contents.'
    parser.add_argument('-c', '--collection', help=help_str)

    help_str = \
        'The source folder to import files from. Has to exist and ' \
        'has to be a folder.'
    parser.add_argument('-s', '--source', help=help_str, required=False)

    help_str = \
        'View the gallery in random order auto skpping after the' \
        'given amount of seconds'
    parser.add_argument('-v', '--view', help=help_str, required=False)

    return parser.parse_args()


def get_file_extension(fname):
    """Returns the given file's extension as a string, . included"""
    _, ext = os.path.splitext(fname)
    return ext


def hex_encode(data, length):
    """
    Pads the given data to fit into the given length of hexadecimal characters
    and returns it encoded as one.
    """
    fmt = '{0:0' + str(length) + 'x}'
    return fmt.format(data)


def get_file_hash(fname, hash_length):
    """
    Computes the SHA256 hash of the file at the given path and encodes its
    value to a hexadecimal string of the given length. The computed value is
    returned as a string.
    """
    hash_sha = hashlib.sha256()
    with open(fname, 'rb') as infile:
        for chunk in iter(lambda: infile.read(4096), b''):
            hash_sha.update(chunk)
    hash_sha = hash_sha.hexdigest()
    hash_sha = int(hash_sha, 16) % (2 ** (4 * hash_length))
    return hex_encode(hash_sha, hash_length)


def get_file_size(fname, size_length):
    """
    Computes the size of the file at the given path and encodes it as a
    hexadecimal string of the given length. The computed value is returned as a
    string.
    """
    size = os.path.getsize(fname)
    return hex_encode(size, size_length)


def get_file_key(fname, hash_length=HASH_LENGTH, size_length=SIZE_LENGTH):
    """
    Computes a likely-to-be-unique key for the given file by combining its hash
    and file size and returns it.
    """
    fhash = get_file_hash(fname, hash_length)
    fsize = get_file_size(fname, size_length)
    return fhash + fsize


def read_file_keys(fname):
    """
    Reads the given file's list of file keys and returns them as a set.
    """
    with open(fname, 'r') as infile:
        fkeys = infile.read().split('\n')
        return set(fkeys)


def write_file_keys(fname, fkeys):
    """
    Writes the given set of file keys to the given file.
    """
    with open(fname, 'w') as outfile:
        for fkey in fkeys:
            outfile.write(fkey + '\n')


def import_files(col, src):
    """
    Imports files from the given src directory into the given collection's
    airlock, ignoring previously blacklisted files.
    """
    for root, _, files in os.walk(src, topdown=False):
        for fil in sorted(files):
            fname = os.path.join(root, fil)
            ext = get_file_extension(fil)
            fkey = get_file_key(fname)

            if ext in IGNORED_EXT:
                print('- Ignored: {}'.format(fname))
                continue

            if not col.is_blacklisted(fkey) and not col.is_whitelisted(fkey):
                target = fkey + ext
                target = os.path.join(col.get_airlock(), target)
                if not os.path.exists(target):
                    shutil.copy(fname, target, follow_symlinks=True)
                    print('+ Copied:  {} -> {}'.format(fname, target))
            else:
                print('- Ignored: {}'.format(fname))


def blacklist_handler(col, player):
    """
    Helper function to create a blacklist handler for the given player and
    collection.
    """
    def handler(state, _):
        """
        Retains the current file in the player in the collection's blacklist
        and removes it from the airlock. The player is then advanced to the
        next file.
        """
        if state[0] == 'u':
            fname = player.playlist[player.playlist_pos]['filename']
            fkey = get_file_key(fname)
            col.blacklist_file(fkey)
            player.playlist_remove()
            os.remove(fname)
            print('Blacklisted: {}'.format(fname))
    return handler


def whitelist_handler(col, player):
    """
    Helper function to create a whitelist handler for the given player and
    collection.
    """
    def handler(state, _):
        """
        Retains the current file in the player in the collection's whitelist
        and moves the file from the airlock to the gallery directory of the
        collection. The player is then advanced to the next file.
        """
        if state[0] == 'u':
            fname = player.playlist[player.playlist_pos]['filename']
            fkey = get_file_key(fname)
            col.whitelist_file(fkey)
            player.playlist_remove()
            basename = os.path.basename(fname)
            shutil.move(fname, os.path.join(col.get_gallery(), basename))
            print('Whitelisted: {}'.format(fname))
    return handler


def quit_handler(playlist, player):
    """
    Helper function to create quit handler for given player and playlist
    """
    def handler(state, _):
        """
        Empties the playlist and quits the player if the key this handler is
        bound to is raised.
        """
        if state[0] == 'u':
            player.quit()
            playlist.clear()
            print('Quitting manually.')
    return handler


def sort_airlock(col):
    """
    Displays the contents of the airlock to the user, allowing them to either
    blacklist a file to be ignored from the collection or whitelist and copy
    them to the gallery.
    """
    playlist = os.listdir(col.get_airlock())
    playlist = [os.path.join(col.get_airlock(), fil) for fil in playlist]
    total_count = len(playlist)

    if not playlist:
        print('{}: Airlock empty. Nothing to do.'.format(col.directory))
        return

    player = mpv.MPV(input_vo_keyboard=True)
    player['loop-file'] = 'inf'
    player['mute'] = True

    player.register_key_binding(BLACKLIST_KEY, blacklist_handler(col, player))
    player.register_key_binding(WHITELIST_KEY, whitelist_handler(col, player))
    player.register_key_binding('\\', blacklist_handler(col, player))
    player.register_key_binding('a', whitelist_handler(col, player))
    player.register_key_binding(QUIT_KEY, quit_handler(playlist, player))

    for fil in playlist:
        player.playlist_append(fil)
    player.playlist_pos = 0

    while playlist:
        print(playlist[0])
        print('Progress: {}/{}'.format(len(playlist), total_count))
        del playlist[0]
        player.wait_for_playback()

    del player
    print('{}: Done sorting airlock.'.format(col.directory))


def view_collection(col, wait):
    playlist = os.listdir(col.get_gallery())
    playlist = [os.path.join(col.get_gallery(), fil) for fil in playlist]
    shuffle(playlist)
    total_count = len(playlist)

    if not playlist:
        print('{}: Gallery empty. Nothing to do.'.format(col.directory))
        return

    player = mpv.MPV(input_default_bindings=True, input_vo_keyboard=True)
    player['loop-file'] = 'inf'
    player['mute'] = False

    #player.register_key_binding('a', blacklist_handler(col, player))
    #player.register_key_binding(WHITELIST_KEY, whitelist_handler(col, player))
    #player.register_key_binding(QUIT_KEY, quit_handler(playlist, player))

    for fil in playlist:
        player.playlist_append(fil)
    player.playlist_pos = 0

    def nexter():
        while True:
            sleep(wait)
            player.playlist_next()

    thread = threading.Thread(target=nexter, args={})
    thread.daemon = True
    thread.start()

    while playlist:
        print('Progress: {}/{}'.format(len(playlist), total_count))
        player.wait_for_playback()

    del player
    print('{}: Done sorting airlock.'.format(col.directory))


if __name__ == '__main__':
    ARGS = parse_command_line()

    if ARGS.source:
        if not os.path.isdir(ARGS.source):
            print('Soure directory {} does not exist.'.format(ARGS.source))
            sys.exit(-1)
        with Collection(ARGS.collection) as COL:
            import_files(COL, ARGS.source)
    elif ARGS.view:
        with Collection(ARGS.collection) as COL:
            view_collection(COL, int(ARGS.view))
    else:
        with Collection(ARGS.collection) as COL:
            sort_airlock(COL)
