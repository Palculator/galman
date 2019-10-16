# Introduction

The somewhat specific scenario Galman is supposed to be of help in is trying to
maintain a growing collection of media files, with new file being vetted by the
user before actually being entered into the gallery. Other tools for this exist,
but Galman focuses only on the decision of whether or not to keep or delete a
file and tries to make going through files en masse faster that way.

# Requirements

Galman requires Python 3 and a local [mpv](https://mpv.io/) installation to
work. Additional requirements are managed through pip, so before using the tool,
execute the following in the project directory (preferably relying on a
virtualenv):

    pip install -r requirements.txt

This will install other libraries needed to run the tool.

# Collections

As mentioned, Galman's point is to manage a collection of media files. This is
done mostly through file system functions: A collection is a directory that
contains a set of files and directories Galman relies on, most notably, a
"Gallery" folder of media files that were okay'd by the user.

# Note on filenames

It's important to mention that Galman does not retain names of files entered
into a collection, but rather renames them to be a combination of their hash
and size, to make files somewhat uniquely identifiable.

# Running

Interaction with Galman is done through the command line and using key bindings
in MPV. The tool is started from the command line and always requires a
collection directory to work on as a parameter specified with `-c`:

    ./galman.py -c /path/to/collection

By default, with no other option specified, Galman will scan the collection's
airlock for files, enter them into an MPV playlist and have the user filter
that. However, to import files into the airlock, one needs to start the
application with:

    ./galman.py -c /path/to/collection -s /path/to/import

The contents of the directory specified in `-s` will be copied into the airlock
of the collection specified in `-c`, with files that were previously black- or
whitelisted ignored to avoid having to re-filter them. Once all files are
copied, the normal sorting process is started.

# Sorting

If Galman is started with a collection that has files to filter in the airlock,
it starts up the MPV media player with a few custom keybindings:

- To blacklist and delete the current file, the user can press the `8` key on
  their keyboard.
- To whitelist and move the current file to the gallery, the user can press the
  `4` key on their keyboard.
- To quit sorting for now, the user can press the `q` on their keyboard.

Each time a file is black-/whitelisted, MPV advances to the next file, meaning
the user can filter files in bulk relatively quickly by just hitting 4 or 8
depending on whether or not they want to keep the file and MPV presenting the
next file right away.

Galman automatically exits once there are no files to sort.
