from trashcli.trash_dirs_scanner import trash_dir_found

class Emptier:
    def __init__(self, delete_mode, trash_dir_reader, trashcan):
        self.delete_mode = delete_mode
        self.trash_dir_reader = trash_dir_reader
        self.trashcan = trashcan

    def do_empty(self, trash_dirs, environ, parsed_days):
        for event, args in trash_dirs:
            if event == trash_dir_found:
                trash_dir_path, volume = args
                for trashinfo_path in self.trash_dir_reader.list_trashinfo(
                        trash_dir_path):
                    if self.delete_mode.ok_to_delete(trashinfo_path, environ,
                                                     parsed_days):
                        self.trashcan.delete_trashinfo_and_backup_copy(
                            trashinfo_path)
                for orphan in self.trash_dir_reader.list_orphans(
                        trash_dir_path):
                    self.trashcan.delete_orphan(orphan)
