"""
OpenNEM Time Series Schema

Defines a tiem series and methods to extract start and end times based on max/min from
SCADA or other ranes and the start/end used in SQL queries

All ranges and queries are _inclusive_ of start/end dates

End is the most recent time chronoligally ordered:

[start] === series === [end]

"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union

from datetime_truncate import truncate as date_trunc

from opennem.api.time import human_to_period
from opennem.schema.core import BaseConfig
from opennem.schema.network import NetworkSchema
from opennem.schema.time import TimeInterval, TimePeriod
from opennem.utils.dates import get_end_of_last_month
from opennem.utils.interval import get_human_interval
from opennem.utils.version import CUR_YEAR


def valid_trunc(trunc: str) -> str:
    get_human_interval(trunc)
    return trunc


class DatetimeRange(BaseConfig):
    """Sime start/end date used for sql queries"""

    start_dt: datetime

    # Alias last
    end_dt: datetime

    interval: TimeInterval

    @property
    def trunc(self) -> str:
        return self.interval.interval_human

    @property
    def start(self) -> Union[datetime, date]:
        if self.interval.interval >= 1440:
            return self.start_dt.date()
        return self.start_dt

    @property
    def end(self) -> Union[datetime, date]:
        if self.interval.interval >= 1440:
            return self.end_dt.date()
        return self.end_dt

    @property
    def length(self) -> int:
        """Return the number of buckets in the range"""
        count = 1
        _comp = self.start
        _delta = get_human_interval(self.trunc)

        while _comp < self.end:
            _comp += _delta
            count += 1

        return count


class TimeSeries(BaseConfig):
    """A time series. Consisting of a start and
    end date (inclusive), a bucket size, timezone info
    and methods to extract DatetimeRange's for sql queries
    """

    # Start and end dates
    start: datetime
    end: datetime

    # The network for this date range
    # used for timezone and offsets
    network: NetworkSchema

    # The interval which provides the bucket size
    interval: TimeInterval

    # The length of the series to extract
    period: TimePeriod

    # extract a particular year
    year: Optional[int]

    def get_range(self) -> DatetimeRange:
        """Return a DatetimeRange from the time series for queries"""
        start = self.start
        end = self.end

        # subtract the period (ie. 7d from the end for start if not all)
        if self.period != human_to_period("all"):
            start = self.end - get_human_interval(self.period.period_human)

        else:
            start = date_trunc(start, self.interval.trunc)
            end = date_trunc(get_end_of_last_month(end), "day")
            self.year = None

        if self.year:
            if self.year > end.year:
                raise Exception("Specified year is great than end year")

            start = start.replace(year=self.year, month=1, day=1)
            start = date_trunc(start, self.interval.trunc)

            if self.year != CUR_YEAR:
                end = datetime(year=self.year, month=12, day=31, hour=0, minute=0, second=0)

        # if the interval size is a day or greater
        if self.interval.interval >= 1440:
            pass

        # Don't localize timezone for day, month, year truncs
        else:
            # Add one interval to make it inclusive
            start += get_human_interval(self.interval.interval_human)

            # localize times
            start = start.astimezone(self.network.get_fixed_offset())
            end = end.astimezone(self.network.get_fixed_offset())

        dtr = DatetimeRange(start_dt=start, end_dt=end, interval=self.interval)

        return dtr