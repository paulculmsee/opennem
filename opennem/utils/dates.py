import logging
import math
from datetime import date, datetime, timedelta, timezone
from typing import Generator, Optional, Tuple, Union

import pytz
# ParserError isn't a concrete type
from dateutil.parser import ParserError, parse  # type: ignore
from dateutil.relativedelta import relativedelta

from opennem.core.networks import NetworkSchema
from opennem.core.normalizers import normalize_whitespace
from opennem.utils.timezone import UTC, is_aware, make_aware

logger = logging.getLogger(__name__)

# Date formats
# See: https://docs.python.org/3.8/library/datetime.html#strftime-and-strptime-behavior
DATE_FORMATS = [
    "%Y/%m/%d,%H:%M:%S",
    "%Y%m%d",
    #
    "%d/%m/%y %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%d/%m/%Y %I:%M:%S %p",  # excel format
    "%Y%m%d%H%M%S",  # bom format
]

DATE_CURRENT = datetime.now()
DATE_YESTERDAY = DATE_CURRENT - timedelta(days=1)
DATE_CURRENT_YEAR = DATE_CURRENT.year


def optimized_data_parser(date_str: str) -> Optional[datetime]:
    """
    Turns out that dateutil's date parser is slow since
    it does a lot of string parsing. Here we try matching
    the date using known string formats.
    """
    dt_return = None

    date_str = normalize_whitespace(date_str).strip()

    for date_format_str in DATE_FORMATS:
        try:
            dt_return = datetime.strptime(date_str, date_format_str)
        except (KeyError, OverflowError, ValueError, AttributeError):
            continue
        if dt_return:
            return dt_return

    return dt_return


def parse_date(
    date_str: Union[str, datetime],
    date_format: Optional[str] = None,
    network: Optional[NetworkSchema] = None,
    dayfirst: bool = True,
    yearfirst: bool = False,
    is_utc: bool = False,
    timezone: timezone = None,
    use_optimized: bool = True,
) -> Optional[datetime]:
    dt_return = None

    if isinstance(date_str, datetime):
        dt_return = date_str

    elif isinstance(date_str, str):
        # avoid strptime if we can
        try:
            dt_return = datetime.fromisoformat(date_str.replace("/", "-"))
        except ValueError:
            pass

        if not dt_return and date_format:
            dt_return = datetime.strptime(date_str, date_format)

        if not dt_return and use_optimized:
            dt_return = optimized_data_parser(date_str)

        if not dt_return:
            try:
                dt_return = parse(date_str, dayfirst=dayfirst, yearfirst=yearfirst)
            except ParserError:
                raise ValueError("Invalid date string passed")

    else:
        raise ValueError("Require a datetime or string object to parse date")

    if network:
        tz = network.get_timezone()

        if tz:
            if is_aware(dt_return):
                if hasattr(tz, "localize"):
                    dt_return = tz.localize()  # type: ignore
                else:
                    dt_return = dt_return.replace(tzinfo=tz)
            else:
                dt_return = make_aware(dt_return, timezone=tz)

    if is_utc:
        tz = UTC

        if dt_return and is_aware(dt_return):
            if tz and hasattr(tz, "localize"):
                dt_return = tz.localize()  # type: ignore
            else:
                dt_return = dt_return.replace(tzinfo=tz)
        else:
            dt_return = make_aware(dt_return, timezone=tz)  # type: ignore

    if timezone:
        dt_return = make_aware(dt_return, timezone=timezone)  # type: ignore

    return dt_return


def date_series(
    start: Union[datetime, date] = None,
    end: Union[datetime, date] = None,
    length: int = 30,
    interval: Union[timedelta, relativedelta] = timedelta(days=1),
    reverse: bool = False,
) -> Generator[datetime, None, None]:
    """
    Generate a datetime series

    @NOTE probably don't need reverse since you can provide a negative interval

    """
    if start and isinstance(start, datetime):
        start = start.date()

    if end and isinstance(end, datetime):
        end = end.date()

    if not start:
        start = datetime.now().date()

    if end:
        # Calculating the number of intervals
        # is different between timedelta and
        # relative times
        if isinstance(interval, timedelta):
            length = int(abs((end - start) / interval))

        # currently only supports up to granuality months
        elif isinstance(interval, relativedelta):
            rd = relativedelta(start, end)

            length = rd.years * 12 + rd.months + 1

    next_record = start

    for _ in range(length):
        yield next_record

        if reverse:
            next_record -= interval
        else:
            next_record += interval


total_months = lambda dt: dt.month + 12 * dt.year  # noqa: E731


def total_weeks(d1: Union[datetime, date], d2: Union[datetime, date]) -> int:
    monday1 = d1 - timedelta(days=d1.weekday())
    monday2 = d2 - timedelta(days=d2.weekday())

    return abs(int((monday2 - monday1).days / 7))


def month_series(
    start: Union[datetime, date],
    end: Union[datetime, date],
    length: Optional[int] = None,
    reverse: bool = False,
) -> Generator[datetime, None, None]:
    """
    Generate a series of months
    """
    step = 1

    if end < start:
        step = -1

    if start == end:
        yield datetime(start.year, start.month, 1)

    for tot_m in range(total_months(start) - 1, total_months(end) - 2, step):
        y, m = divmod(tot_m, 12)
        yield datetime(y, m + 1, 1)


def week_series(
    start: Union[datetime, date],
    end: Union[datetime, date],
    length: Optional[int] = None,
) -> Generator[Tuple[int, int], None, None]:
    """
    Generate week series M -> S
    """
    reverse = False

    if end < start:
        reverse = True

    length = total_weeks(start, end)

    for week_i in range(0, length):
        if reverse:
            cur_date = start - timedelta(weeks=week_i)
        else:
            cur_date = start + timedelta(weeks=week_i)

        cur_cal = cur_date.isocalendar()

        yield cur_cal[0], cur_cal[1]


def chop_delta_microseconds(delta: timedelta) -> timedelta:
    """Removes microsevonds from a timedelta"""
    return delta - timedelta(microseconds=delta.microseconds)


def chop_datetime_microseconds(dt: datetime) -> datetime:
    """Removes the microseconds portion of a datetime"""
    if not dt.microsecond:
        return dt

    return dt - timedelta(microseconds=dt.microsecond)


def get_date_component(format_str: str, dt: datetime = None) -> str:
    """
    Get the format string part out of a date

    ex.
    >>> get_date_component("%Y")
    > 2020
    """
    if dt:
        return dt.strftime(format_str)
    return datetime.now().strftime(format_str)


def subtract_week(subject: datetime) -> datetime:
    return subject - timedelta(days=7)


def subtract_days(subject: Optional[datetime] = None, days: int = 30) -> datetime:
    if not subject:
        subject = datetime.now(timezone.utc)

    return subject - timedelta(days=days)


def is_valid_isodate(date: str, check_timezone: bool = False) -> bool:
    """Check if a string is a valid ISO formatted datestring"""
    dt = None

    try:
        dt = datetime.fromisoformat(date)
    except ValueError:
        return False

    if check_timezone:
        if dt.tzinfo:
            return True
        else:
            return False

    return True


def get_quarter(dt: datetime) -> int:
    """Get the quarter from a datetime"""
    return math.ceil(dt.month / 3.0)


def get_end_of_last_month(dt: datetime) -> datetime:
    """Get the end of the previous month"""
    dtn = dt.replace(day=1) - timedelta(days=1)

    return dtn


def strip_timezone(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None)


def optionally_parse_string_datetime(
    value: Optional[Union[str, datetime, date]] = None
) -> Optional[Union[str, datetime, date]]:
    """Parse a string or date or datetime back into a datetime optionally"""
    if not value:
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logger.error("Could not parse optional date: {}".format(value))
            return None

    if isinstance(value, datetime):
        # @TODO here optionally set to network time
        return value

    return value


def get_last_complete_day_for_network(network: NetworkSchema) -> datetime:
    tz = pytz.timezone(network.timezone)

    # today_midnight in NEM time
    today_midnight = datetime.now(tz).replace(
        tzinfo=network.get_fixed_offset(), microsecond=0, hour=0, minute=0, second=0
    )

    return today_midnight


def unix_timestamp_to_aware_datetime(timestamp: int, timezone: str) -> datetime:
    """ Convert a unix timstamp to an aware datetime """
    return pytz.timezone(timezone).localize(datetime.fromtimestamp(timestamp))
