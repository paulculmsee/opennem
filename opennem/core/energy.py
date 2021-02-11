"""
OpenNEM Energy Tools

"""
from decimal import Decimal, getcontext
from operator import attrgetter
from sys import maxsize
from typing import Callable, Generator, List, Optional, Union

import numpy as np

from opennem.schema.core import BaseConfig

MAX_INTERVALS = maxsize - 1

context = getcontext()
context.prec = 9


class Point(BaseConfig):
    x: Decimal
    y: Decimal


def trapozedoid(p1: Point, p2: Point) -> float:
    """Trapezoidal area between two points"""
    width = p2.y - p1.y
    area = p1.x * width + ((p2.x - p1.x) * width) / 2

    return float(area)


def zero_nulls(number: Union[int, float, None]) -> float:
    if not number:
        return 0.0

    return number


def list_chunk(series: List, chunk_size: int) -> Generator[List[Union[float, int]], None, None]:
    for i in range(0, len(series), chunk_size):
        yield np.array(series[i : i + chunk_size])


def energy_sum_averages(
    series: List[Union[int, float]], bucket_size_minutes: int, interval_size_minutes: int = 5
) -> List[float]:
    intervals_per_bucket = bucket_size_minutes / interval_size_minutes

    if int(intervals_per_bucket) != intervals_per_bucket:
        raise Exception("Invalid interval and bucket sizes. Interval size must divide into bucket")

    intervals_per_bucket = int(intervals_per_bucket)

    buckets_per_hour = bucket_size_minutes / 60

    intervals_per_hour = 60 / interval_size_minutes

    if int(intervals_per_hour) != intervals_per_hour:
        raise Exception("Invalid interval size.")

    intervals_per_hour = int(intervals_per_hour)

    return_series = []

    for series_chunk in list_chunk(series, intervals_per_bucket + 1):
        avg_series = [1] + (len(series_chunk) - 2) * [2] + [1]

        return_series.append(
            buckets_per_hour * (series_chunk * avg_series).sum() / intervals_per_hour
        )

    return return_series


def energy_sum(
    series: List[Union[int, float, None]],
    bucket_size_minutes: int,
    auc_function: Callable = trapozedoid,
) -> float:
    """Calcualte the energy sum of a series for an interval
    using the area under the curve
    """

    number_intervals = len(series) - 1
    interval_size = bucket_size_minutes / len(series)

    if len(series) < 1:
        raise Exception("Requires at least one value in the series")

    if bucket_size_minutes <= 0 or bucket_size_minutes > maxsize:
        raise Exception("Invalid bucket size")

    if bucket_size_minutes % 1 != 0:
        raise Exception("Not a round interval size in minutes")

    if number_intervals < 1 or number_intervals >= MAX_INTERVALS:
        raise Exception("Invalid number of intervals")

    # 0 out all nulls
    series = [zero_nulls(n) for n in series]

    y_series = [i * interval_size for i in range(len(series))]

    # build point objects from y_series and zeroed x values
    series_points = [Point(x=series[i], y=y) for i, y in enumerate(y_series)]

    # sort by y value ascending 0 ... N
    series_points.sort(key=attrgetter("y"))

    area = 0.0
    p1 = None
    p2 = None

    for i in range(number_intervals):
        p1 = series_points[i]
        p2 = series_points[i + 1]

        area += auc_function(p1, p2)

    # convert back to hours
    area = area / 60

    return area