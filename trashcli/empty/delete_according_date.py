from trashcli.empty.older_than import older_than
from trashcli.trash import parse_deletion_date


class DeleteAccordingDate:
    def __init__(self, contents_of, clock, max_age_in_days, errors):
        self.contents_of = contents_of
        self.clock = clock
        self.max_age_in_days = max_age_in_days
        self.errors = errors

    def ok_to_delete(self, trashinfo_path):
        contents = self.contents_of(trashinfo_path)
        now_value = self.clock.get_now_value(self.errors)
        deletion_date = parse_deletion_date(contents)
        if deletion_date is not None:
            if older_than(self.max_age_in_days, now_value, deletion_date):
                return True
        return False