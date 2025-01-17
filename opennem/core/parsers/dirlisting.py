"""OpenNEM Directory Listing Parser

Used to parse default http server directory listings and returns a list of file
objects

Currently supports:

    * IIS default listings and variations
    * Extracing metadata from AEMO filenames
"""

import html
import logging
import re
from datetime import datetime
from enum import Enum
from operator import attrgetter
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Union

from pydantic import ValidationError, validator
from scrapy.http import HtmlResponse

from opennem.core.downloader import url_downloader
from opennem.core.normalizers import is_number, strip_double_spaces
from opennem.schema.core import BaseConfig

logger = logging.getLogger("opennem.parsers.dirlisting")

__iis_line_match = re.compile(
    r"(?P<modified_date>.*[AM|PM])\ {2,}(?P<file_size>(\d{1,}|\<dir\>))\ <a href=['\"]?(?P<link>[^'\" >]+)['\"]>(?P<filename>[^\<]+)"
)


# AEMO files have a created timestamp in their filenames. This extracts it.
_aemo_created_date_match = re.compile(r"\_(?P<date_created>\d{12})\_")


def parse_dirlisting_datetime(datetime_string: Union[str, datetime]) -> Optional[datetime]:
    """Parses dates from directory listings. Primarily used for modified time"""

    # sometimes it already parses via pydantic
    if isinstance(datetime_string, datetime):
        return datetime_string

    datetime_string = strip_double_spaces(datetime_string.strip())

    if not datetime_string:
        logger.error("No dirlisting datetime string")

    _FORMAT_STRINGS = ["%A, %B %d, %Y %I:%M %p"]

    datetime_parsed: Optional[datetime] = None

    for _fs in _FORMAT_STRINGS:
        try:
            datetime_parsed = datetime.strptime(datetime_string, _fs)
        except ValueError:
            pass

    if not datetime_string:
        logger.error("Error parsing dirlisting datetime string: {}".format(datetime_string))

    return datetime_parsed


class DirlistingEntryType(Enum):
    file = "file"
    directory = "directory"


class DirlistingEntry(BaseConfig):
    filename: Path
    link: str
    modified_date: Optional[datetime]
    aemo_created_date: Optional[datetime]
    file_size: Optional[int]
    entry_type: DirlistingEntryType = DirlistingEntryType.file

    _validate_modified_date = validator("modified_date", allow_reuse=True, pre=True)(
        parse_dirlisting_datetime
    )

    @validator("aemo_created_date", always=True)
    def _validate_aemo_created_date(cls, value: Any, values: Dict[str, Any]) -> Optional[datetime]:
        if value:
            raise Exception("aemo_created_date is derived, not set")

        # no need to check if this exists since ValidationError will occur if not
        _filename_value = values["filename"]

        _created_date_match = re.search(_aemo_created_date_match, str(_filename_value))

        if not _created_date_match:
            return None

        _dt_str = _created_date_match.group("date_created")

        dt = None

        try:
            dt = datetime.strptime(_dt_str, "%Y%m%d%H%M")
        except ValueError:
            return None

        return dt

    @validator("file_size", allow_reuse=True, pre=True)
    def _parse_dirlisting_filesize(cls, value: str) -> Optional[int]:
        if is_number(value):
            return value

        return None

    @validator("entry_type", always=True)
    def _validate_entry_type(cls, value: Any, values: Dict[str, Any]) -> DirlistingEntryType:
        if not values["file_size"]:
            return DirlistingEntryType.directory

        if values["link"].endswith("/"):
            return DirlistingEntryType.directory

        return DirlistingEntryType.file


class DirectoryListing(BaseConfig):
    url: str
    entries: List[DirlistingEntry] = []

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def file_count(self) -> int:
        return len(self.get_files())

    @property
    def directory_count(self) -> int:
        return len(self.get_directories())

    def apply_filter(self, pattern: str) -> None:
        self.entries = list(filter(lambda x: re.match(pattern, x.link), self.entries))

    def get_files(self) -> List[DirlistingEntry]:
        return list(filter(lambda x: x.entry_type == DirlistingEntryType.file, self.entries))

    def get_directories(self) -> List[DirlistingEntry]:
        return list(filter(lambda x: x.entry_type == DirlistingEntryType.directory, self.entries))

    def get_most_recent_files(
        self, reverse: bool = True, limit: Optional[int] = None
    ) -> List[DirlistingEntry]:
        _entries = list(sorted(self.get_files(), key=attrgetter("modified_date"), reverse=reverse))

        if not limit:
            return _entries

        return _entries[:limit]

    def get_files_modified_since(self, modified_date: datetime) -> List[DirlistingEntry]:
        return list(filter(lambda x: x.modified_date > modified_date, self.get_files()))


def parse_dirlisting_line(dirlisting_line: str) -> Optional[DirlistingEntry]:
    """Parses a single line from a dirlisting page"""
    if not dirlisting_line:
        return None

    matches = re.search(__iis_line_match, dirlisting_line)

    model: Optional[DirlistingEntry] = None

    if not matches:
        logger.error("Could not match dirlisting line: {}".format(dirlisting_line))
        return None

    try:
        model = DirlistingEntry(**matches.groupdict())
    except ValidationError as e:
        logger.error("Error in validating dirlisting line: {}".format(e))
    except ValueError as e:
        logger.error("Error parsing dirlisting line: {}".format(e))

    return model


def get_dirlisting(url: str) -> DirectoryListing:
    """Parse a directory listng into a list of DirlistingEntry models"""
    dirlisting_content = url_downloader(url)

    resp = HtmlResponse(url=url, body=dirlisting_content, encoding="utf-8")

    _dirlisting_models: List[DirlistingEntry] = []

    for i in resp.css("body pre").get().split("<br>"):
        # it catches the containing block so skip those
        if "pre>" in i:
            continue

        model = parse_dirlisting_line(html.unescape(i.strip()))

        if model:

            # append the base URL to the model link
            model.link = resp.urljoin(model.link)

            _dirlisting_models.append(model)

    model = DirectoryListing(url=url, entries=_dirlisting_models)

    return model
