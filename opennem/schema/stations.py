"""
    Set of stations


"""
from collections import UserList
from typing import List, Optional

from opennem.schema.opennem import StationSchema


def _str_comp(subject: str, value: str) -> bool:
    return subject.trim().lower() == value.trim().lower()


class StationSet(UserList):
    """

    """

    # def __init__(self,):
    #     pass

    def get(self, key: int) -> Optional[StationSchema]:
        _entry = list(filter(lambda s: s.id == key, self.data))

        if not _entry or len(_entry) == 0:
            return None

        return _entry.pop()

    def get_by(self, **kwargs):
        print(kwargs)

    def get_name(self, name: str) -> List[StationSchema]:
        _entries = list(filter(lambda s: _str_comp(s.name, name), self.data))

        return _entries

    def get_code(self, code: str) -> Optional[StationSchema]:
        _entries = list(filter(lambda s: s.code == code, self.data))

        if not _entries or len(_entries) == 0:
            return None

        if len(_entries) > 1:
            raise Exception("More than one station with a code")

        return _entries.pop()

    def one(self):
        pass

    def add(self, station: StationSchema):
        if not station.id:
            raise Exception("Require a station id")

        _key = station.id

        if self.get(_key):
            raise Exception("Duplicate id {}".format(_key))

        self.data.append(station)

        return self

    @property
    def length(self) -> int:
        return len(self.data)
