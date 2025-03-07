# Copyright (C) 2011-2021 Andrea Francia Bereguardo(PV) Italy
import os
import unittest

import pytest
from mock import Mock
from six import StringIO

from trashcli.empty.empty_cmd import EmptyCmd
from trashcli.fs import FileRemover, FileSystemContentReader, \
    FileSystemDirReader, TopTrashDirRulesFileSystemReader
from trashcli.fstab import VolumesListing
from .files import require_empty_dir, make_dirs, set_sticky_bit, \
    make_unreadable_dir, make_empty_file, make_readable
from .support import MyPath, volumes_mock


@pytest.mark.slow
class TestTrashEmptyCmd(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = MyPath.make_temp_dir()
        self.unreadable_dir = self.tmp_dir / 'data/Trash/files/unreadable'
        self.volumes_listing = Mock(spec=VolumesListing)
        self.volumes_listing.list_volumes.return_value = [self.unreadable_dir]
        self.err = StringIO()
        self.environ = {'XDG_DATA_HOME': self.tmp_dir / 'data'}
        self.empty = EmptyCmd(
            argv0='trash-empty',
            out=StringIO(),
            err=self.err,
            volumes_listing=self.volumes_listing,
            now=None,
            file_reader=TopTrashDirRulesFileSystemReader(),
            file_remover=FileRemover(),
            content_reader=FileSystemContentReader(),
            dir_reader=FileSystemDirReader(),
            version=None,
            volumes=volumes_mock()
        )

    def test_trash_empty_will_skip_unreadable_dir(self):
        make_unreadable_dir(self.unreadable_dir)

        self.empty.run_cmd([], self.environ, uid=123)

        assert ("trash-empty: cannot remove %s\n" % self.unreadable_dir ==
                self.err.getvalue())

    def tearDown(self):
        make_readable(self.unreadable_dir)
        self.tmp_dir.clean_up()


class TestEmptyCmdWithMultipleVolumes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = MyPath.make_temp_dir()
        self.top_dir = self.temp_dir / 'topdir'
        self.volumes_listing = Mock(spec=VolumesListing)
        self.volumes_listing.list_volumes.return_value = [self.top_dir]
        require_empty_dir(self.top_dir)
        self.environ = {}
        self.empty = EmptyCmd(
            argv0='trash-empty',
            out=StringIO(),
            err=StringIO(),
            volumes_listing=self.volumes_listing,
            now=None,
            file_reader=TopTrashDirRulesFileSystemReader(),
            file_remover=FileRemover(),
            content_reader=FileSystemContentReader(),
            dir_reader=FileSystemDirReader(),
            version=None,
            volumes=volumes_mock(),
        )

    def test_it_removes_trashinfos_from_method_1_dir(self):
        self.make_proper_top_trash_dir(self.top_dir / '.Trash')
        make_empty_file(self.top_dir / '.Trash/123/info/foo.trashinfo')

        self.empty.run_cmd([], self.environ, uid=123)

        assert not os.path.exists(
            self.top_dir / '.Trash/123/info/foo.trashinfo')

    def test_it_removes_trashinfos_from_method_2_dir(self):
        make_empty_file(self.top_dir / '.Trash-123/info/foo.trashinfo')

        self.empty.run_cmd([], self.environ, uid=123)

        assert not os.path.exists(
            self.top_dir / '.Trash-123/info/foo.trashinfo')

    def test_it_removes_trashinfo_from_specified_trash_dir(self):
        make_empty_file(self.temp_dir / 'specified/info/foo.trashinfo')

        self.empty.run_cmd(['--trash-dir', self.temp_dir / 'specified'],
                       self.environ, uid=123)

        assert not os.path.exists(
            self.temp_dir / 'specified/info/foo.trashinfo')

    @staticmethod
    def make_proper_top_trash_dir(path):
        make_dirs(path)
        set_sticky_bit(path)

    def tearDown(self):
        self.temp_dir.clean_up()
