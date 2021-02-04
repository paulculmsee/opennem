import logging
from pathlib import Path

from opennem.db import get_database_engine

from .schema import ContinuousAggregationPolicy, ViewDefinition

logger = logging.getLogger("opennem.db.views")

VIEW_PATH = Path(__file__).parent.parent / "fixtures" / "views"


AggregationPolicy30Minutes = ContinuousAggregationPolicy(
    interval="30 minutes", start_interval="2 hours"
)


_VIEW_MAP = [
    ViewDefinition(
        priority=1,
        name="mv_facility_energy_hour",
        filepath="mv_facility_energy_hour.sql",
        aggregation_policy=AggregationPolicy30Minutes,
    )
]


_query_drop_ca = "SELECT remove_continuous_aggregate_policy('{view_name}')"

_query_create_ca = """SELECT add_continuous_aggregate_policy('{view_name}',
    start_offset => {start_offset},
    end_offset => '{end_offset}',
    schedule_interval => INTERVAL '{schedule_size}');
"""


def get_view_content(viewdef: ViewDefinition) -> str:
    if not VIEW_PATH.is_dir():
        raise Exception("View directory: {} does not exist".format(VIEW_PATH))

    view_full_path = VIEW_PATH / Path(viewdef.filepath)

    if not view_full_path.is_file():
        raise Exception("View {} not found in view path:".format(view_full_path))

    view_content: str = ""

    with view_full_path.open() as fh:
        view_content = fh.read()

    return view_content


def purge_views() -> None:
    """Remove views that aren't in the view table"""
    pass


def init_views() -> None:
    logger.info("init views")

    v = _VIEW_MAP[0]
    print(get_view_content(v))


if __name__ == "__main__":
    init_views()