import os
import sys

from .list_mount_points import os_mount_points
from .trash import version, logger
from .fstab import volume_of
from .trash import TrashDirectories
from .fs import contents_of, list_files_in_dir
from .trash import backup_file_path_from
from . import fs, trash


def main():
    try:           # Python 2
        input23 = raw_input
    except:        # Python 3
        input23 = input
    trash_directories = make_trash_directories()
    trashed_files = TrashedFiles(trash_directories, TrashDirectory(),
                                 contents_of)
    RestoreCmd(
        stdout  = sys.stdout,
        stderr  = sys.stderr,
        exit    = sys.exit,
        input   = input23,
        trashed_files=trashed_files
    ).run(sys.argv)


def getcwd_as_realpath():
    return os.path.realpath(os.curdir)


def parse_args(sys_argv, curdir):
    import argparse
    parser = argparse.ArgumentParser(
        description='Restores from trash chosen file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('path',
                        default=curdir, nargs='?',
                        help='Restore files from given path instead of current '
                             'directory')
    parser.add_argument('--sort',
                        choices=['date', 'path', 'none'],
                        default='path',
                        help='Sort list of restore candidates by given field')
    parser.add_argument('--version', action='store_true', default=False)
    return parser.parse_args(sys_argv[1:])


class TrashedFiles:
    def __init__(self, trash_directories, trash_directory, contents_of):
        self.trash_directories = trash_directories
        self.trash_directory = trash_directory
        self.contents_of = contents_of

    def all_trashed_files(self):
        logger = trash.logger
        for path, volume in self.trash_directories.all_trash_directories():
            for type, info_file in self.trash_directory.all_info_files(path):
                if type == 'non_trashinfo':
                    logger.warning("Non .trashinfo file in info dir")
                elif type == 'trashinfo':
                    try:
                        trash_info = TrashInfoParser(self.contents_of(info_file),
                                                     volume)
                        original_location = trash_info.original_location()
                        deletion_date     = trash_info.deletion_date()
                        backup_file_path  = backup_file_path_from(info_file)
                        trashedfile = TrashedFile(original_location,
                                                  deletion_date,
                                                  info_file,
                                                  backup_file_path)
                        yield trashedfile
                    except ValueError:
                        logger.warning("Non parsable trashinfo file: %s" % info_file)
                    except IOError as e:
                        logger.warning(str(e))
                else:
                    logger.error("Unexpected file type: %s: %s",
                                 type, info_file)


class RestoreCmd(object):
    def __init__(self, stdout, stderr, exit, input,
                 curdir = getcwd_as_realpath, version = version,
                 trashed_files=None):
        self.out      = stdout
        self.err      = stderr
        self.exit     = exit
        self.input    = input
        self.curdir   = curdir
        self.version = version
        self.fs = fs
        self.path_exists = os.path.exists
        self.trashed_files = trashed_files
    def run(self, argv):
        args = parse_args(argv, self.curdir() + os.path.sep)
        if args.version:
            command = os.path.basename(argv[0])
            self.println('%s %s' % (command, self.version))
            return
        def is_trashed_from_curdir(trashedfile):
            return trashedfile.original_location.startswith(args.path)
        trashed_files = self.all_trashed_files_filter(is_trashed_from_curdir)
        if args.sort == 'path':
            trashed_files = sorted(trashed_files, key=lambda x: x.original_location + str(x.deletion_date))
        elif args.sort == 'date':
            trashed_files = sorted(trashed_files, key=lambda x: x.deletion_date)
        self.handle_trashed_files(trashed_files)

    def handle_trashed_files(self,trashed_files):
        if not trashed_files:
            self.report_no_files_found()
        else :
            for i, trashedfile in enumerate(trashed_files):
                self.println("%4d %s %s" % (i, trashedfile.deletion_date, trashedfile.original_location))
            self.restore_asking_the_user(trashed_files)
    def restore_asking_the_user(self, trashed_files):
        index=self.input("What file to restore [0..%d]: " % (len(trashed_files)-1))
        if index == "" :
            self.println("Exiting")
        else :
            try:
                indexes = index.split(',')
                indexes.sort(reverse=True)  # restore largest index first
                for index in indexes:
                    index = int(index)
                    if (index < 0 or index >= len(trashed_files)):
                        raise IndexError("Out of range")
                    trashed_file = trashed_files[index]
                    self.restore(trashed_file)
            except (ValueError, IndexError) as e:
                self.printerr("Invalid entry")
                self.exit(1)
            except IOError as e:
                self.printerr(e)
                self.exit(1)
    def restore(self, trashed_file):
        restore(trashed_file, self.path_exists, self.fs)
    def all_trashed_files_filter(self, matches):
        trashed_files = []
        for trashedfile in self.trashed_files.all_trashed_files():
            if matches(trashedfile):
                trashed_files.append(trashedfile)
        return trashed_files

    def report_no_files_found(self):
        self.println("No files trashed from current dir ('%s')" % self.curdir())
    def println(self, line):
        self.out.write(line + '\n')
    def printerr(self, msg):
        self.err.write('%s\n' % msg)

from .trash import parse_path
from .trash import parse_deletion_date
class TrashInfoParser:
    def __init__(self, contents, volume_path):
        self.contents    = contents
        self.volume_path = volume_path
    def deletion_date(self):
        return parse_deletion_date(self.contents)
    def original_location(self):
        path = parse_path(self.contents)
        return os.path.join(self.volume_path, path)


def make_trash_directories():
    return AllTrashDirectories(
        volume_of=volume_of,
        getuid=os.getuid,
        environ=os.environ,
        mount_points=os_mount_points()
    )


class AllTrashDirectories:
    def __init__(self, volume_of, getuid, environ, mount_points):
        self.volume_of    = volume_of
        self.getuid       = getuid
        self.environ      = environ
        self.mount_points = mount_points

    def all_trash_directories(self):
        trash_directories = TrashDirectories(self.volume_of,
                                             self.getuid)
        for path1, volume1 in trash_directories.home_trash_dir(self.environ):
            yield path1, volume1
        for volume in self.mount_points:
            for path1, volume1 in trash_directories.volume_trash_dir1(volume):
                yield path1, volume1
            for path1, volume1 in trash_directories.volume_trash_dir2(volume):
                yield path1, volume1

class TrashedFile:
    """
    Represent a trashed file.
    Each trashed file is persisted in two files:
     - $trash_dir/info/$id.trashinfo
     - $trash_dir/files/$id

    Properties:
     - path : the original path from where the file has been trashed
     - deletion_date : the time when the file has been trashed (instance of
                       datetime)
     - info_file : the file that contains information (instance of Path)
     - original_file : the path where the trashed file has been placed after the
                       trash opeartion (instance of Path)
    """
    def __init__(self, original_location,
                       deletion_date,
                       info_file,
                       original_file):
        self.original_location = original_location
        self.deletion_date = deletion_date
        self.info_file = info_file
        self.original_file = original_file

def restore(trashed_file, path_exists, fs):
    if path_exists(trashed_file.original_location):
        raise IOError('Refusing to overwrite existing file "%s".' % os.path.basename(trashed_file.original_location))
    else:
        parent = os.path.dirname(trashed_file.original_location)
        fs.mkdirs(parent)

    fs.move(trashed_file.original_file, trashed_file.original_location)
    fs.remove_file(trashed_file.info_file)


class TrashDirectory:

    def all_info_files(self, path) :
        norm_path = os.path.normpath(path)
        info_dir = os.path.join(norm_path, 'info')
        try :
            for info_file in list_files_in_dir(info_dir):
                if not os.path.basename(info_file).endswith('.trashinfo') :
                    yield ('non_trashinfo', info_file)
                else :
                    yield ('trashinfo', info_file)
        except OSError: # when directory does not exist
            pass
