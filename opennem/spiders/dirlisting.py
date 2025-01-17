import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Pattern
from urllib.parse import ParseResult, urlparse

import scrapy
from scrapy import Spider
from scrapy.http import Response

from opennem.core.crawlers.meta import CrawlStatTypes, crawler_get_meta
from opennem.schema.network import NetworkNEM
from opennem.utils.dates import parse_date

PADDING_WIDTH = 3

__is_number = re.compile(r"^\d+$")

__match_link_dt = re.compile(r"_(?P<datetime>\d{12})_")


def is_number(value: str) -> bool:
    if re.match(__is_number, value):
        return True
    return False


def get_link_datetime(link: str) -> Optional[datetime]:
    _dt_matches = re.search(__match_link_dt, link)

    if not _dt_matches:
        return None

    if "datetime" not in _dt_matches.groupdict().keys():
        return None

    _dt_str = _dt_matches.group("datetime")

    dt = datetime.strptime(_dt_str, "%Y%m%d%H%M")

    return dt


def parse_dirlisting(raw_string: str) -> Dict[str, Any]:
    """
    given a raw text directory listing like "     Saturday 11th June 2020      6789"
    will parse and return both the date and listing type

    @param raw_string - the raw directory listing string
    @return dict of the date in iso format and the type (file or directory)
    """
    components = raw_string.split(" " * PADDING_WIDTH)
    components = [i.strip() for i in components]
    components = list(filter(lambda x: x != "", components))

    _ltype = "dir"

    if not components or len(components) < 2:
        logging.debug(components)
        raise Exception(
            "Invalid line string: {}. Components are: {}".format(raw_string, components)
        )

    if is_number(components[1]):
        _ltype = "file"

    dt = parse_date(components[0], network=NetworkNEM)

    if type(dt) is not datetime:
        raise Exception(
            "{} is not a valid datetime. Original value was {}".format(dt, components[0])
        )

    return {
        "date": dt.isoformat(),
        "type": _ltype,
    }


def get_file_extensions(url: str) -> Optional[str]:
    url_parsed: ParseResult = urlparse(url)

    if not url_parsed.path:
        return None

    url_path = Path(url_parsed.path)

    return url_path.suffix


class DirlistingSpider(Spider):
    """
    spider that parses html directory listings produced by web servers


    """

    # process only the latest using crawl meta
    process_latest: bool = False

    limit: int = 0

    skip: int = 0

    start_url: Optional[str] = None

    supported_extensions = [".csv", ".zip"]

    filename_filter: Optional[Pattern] = None

    custom_settings: Optional[Dict] = {}

    filename: Optional[str] = None

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        starts = []

        if hasattr(self, "start_url") and self.start_url and type(self.start_url) is str:
            starts = [self.start_url]

        if hasattr(self, "start_urls") and self.start_urls and type(self.start_urls) is list:
            starts = self.start_urls

        for url in starts:
            yield scrapy.Request(url)

    def parse(self, response: Response) -> Generator[Dict[str, Any], None, None]:
        links = list(reversed([i.get() for i in response.xpath("//body/pre/a/@href")]))
        latest_processed: Optional[datetime] = None

        if self.process_latest:
            latest_processed = crawler_get_meta(self.name, CrawlStatTypes.latest_processed)

        if self.filename:
            self.skip = 0
            self.limit = 0

        parsed = 0

        if self.limit > 0 and self.skip > 0:
            self.limit = self.limit + self.skip

        for link in links:
            link = response.urljoin(link)
            link_dt = get_link_datetime(link)

            if link.endswith("/"):
                continue

            if self.limit and self.limit > 0 and (parsed >= self.limit):
                self.log(f"Reached limit of {self.limit}", logging.INFO)
                return None

            if get_file_extensions(link) not in self.supported_extensions:
                self.log(
                    "Not a supported extension: {} {}".format(
                        link[-4:].lower(),
                        ", ".join(self.supported_extensions),
                    ),
                    logging.INFO,
                )
                continue

            if self.process_latest and latest_processed and link_dt:
                if latest_processed >= link_dt:
                    logging.debug("Last processed skipping: {}".format(link))
                    continue

            if (
                self.filename_filter
                and isinstance(self.filename_filter, Pattern)
                and not self.filename_filter.match(link)
            ):
                self.log(f"Filter skip file {link}", logging.DEBUG)
                continue

            if self.filename and self.filename not in link:
                self.log(f"Filter skip file {link}", logging.DEBUG)
                continue

            parsed += 1

            if self.skip and self.skip >= parsed:
                self.log(
                    f"Skipping entry {link}",
                    logging.DEBUG,
                )
                continue

            self.log("Getting {}".format(link), logging.INFO)

            yield {"link": link, "link_dt": link_dt}
