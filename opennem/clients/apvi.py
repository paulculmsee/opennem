"""APVI Client for Rooftop Data

"""
import logging
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional

import pytz
import requests
from pydantic import validator

from opennem.importer.rooftop import ROOFTOP_CODE
from opennem.schema.core import BaseConfig
from opennem.schema.network import NetworkNEM
from opennem.utils.dates import get_date_component, parse_date
from opennem.utils.version import get_version

logger = logging.getLogger(__name__)

APVI_DATA_URI = "https://pv-map.apvi.org.au/data"

APVI_NETWORK_CODE = "APVI"

APVI_DATE_QUERY_FORMAT = "%Y-%m-%d"

APVI_EARLIEST_DATE = "2013-05-07"

STATE_POSTCODE_PREFIXES = {
    "NSW": "2",
    "VIC": "3",
    "QLD": "4",
    "SA": "5",
    "WA": "6",
    "TAS": "7",
    "NT": "0",
}

WA_NON_SWIS = ["66", "67"]


class APVIForecastInterval(BaseConfig):
    trading_interval: datetime
    network_id: str = APVI_NETWORK_CODE
    state: str
    facility_code: Optional[str]
    generated: Optional[float]

    _validate_state = validator("state", pre=True, allow_reuse=True)(lambda x: x.strip().upper())

    @validator("trading_interval", pre=True)
    def _validate_trading_interval(cls, value: Any) -> datetime:
        interval_time = parse_date(
            value,
            dayfirst=False,
            yearfirst=True,
        )

        if not interval_time:
            raise Exception(f"Invalid APVI forecast interval: {value}")

        # All APVI data is in NEM time
        interval_time = interval_time.astimezone(NetworkNEM.get_timezone())  # type: ignore

        return interval_time

    @validator("facility_code", always=True, pre=True)
    def _validate_facility_code(cls, value: Any, values: Dict[str, Any]) -> str:
        """Generate an OpenNEM derived facility code for APVI facilities"""
        state = values["state"]

        return "{}_{}_{}".format(ROOFTOP_CODE, APVI_NETWORK_CODE, state.upper())


class APVIStateRooftopCapacity(BaseConfig):
    state: str
    capacity_registered: float
    facility_code: Optional[str]
    unit_number: int

    @validator("facility_code", always=True, pre=True)
    def _validate_facility_code(cls, value: Any, values: Dict[str, Any]) -> str:
        """Generate an OpenNEM derived facility code for APVI facilities"""
        state = values["state"]

        return "{}_{}_{}".format(ROOFTOP_CODE, APVI_NETWORK_CODE, state.upper())


class APVIForecastSet(BaseConfig):
    crawled_at: Optional[datetime]
    intervals: List[APVIForecastInterval]
    capacities: Optional[List[APVIStateRooftopCapacity]]


_apvi_request_session = requests.Session()
_apvi_request_session.headers.update({"User-Agent": f"OpenNEM/{get_version()}"})


def get_apvi_rooftop_data() -> Optional[APVIForecastSet]:
    """Obtains and parses APVI forecast data"""
    day = get_date_component(APVI_DATE_QUERY_FORMAT)

    logger.debug("Getting APVI data for day {}".format(day))

    _resp = _apvi_request_session.post(APVI_DATA_URI, data={"day": day})

    if not _resp.ok:
        logger.error("Invalid APVI Return: {}".format(_resp.status_code))
        return None

    _resp_json = None

    try:
        _resp_json = _resp.json()
    except JSONDecodeError as e:
        logger.error("Error decoding APVI response: {}".format(e))
        return None

    _required_keys = ["postcode", "postcodeCapacity", "installations"]

    for _req_key in _required_keys:
        if _req_key not in _resp_json:
            logger.error(f"Invalid APVI response: {_req_key} field not found")
            return None

    postcode_gen = _resp_json["postcode"]
    postcode_capacity = _resp_json["postcodeCapacity"]
    installations = _resp_json["installations"]

    # brisbane has no DST so its effectively NEM time
    _run_at = datetime.now().astimezone(pytz.timezone("Australia/Brisbane"))
    _interval_records = []

    for record in postcode_gen:
        for state, prefix in STATE_POSTCODE_PREFIXES.items():

            generated = sum(
                [
                    float(v) / 100 * postcode_capacity[k]
                    for k, v in record.items()
                    if k.startswith(prefix)
                    and v
                    and k in postcode_capacity
                    and k[:2] not in WA_NON_SWIS
                ]
            )

            if not generated:
                continue

            _interval_records.append(
                APVIForecastInterval(
                    **{
                        "network_id": "APVI",
                        "trading_interval": record["ts"],
                        "state": state,
                        "generated": generated,
                    }
                )
            )

    _state_capacities = {}

    # Calcualte state capacities
    for postcode_prefix, capacity_val in postcode_capacity.items():
        for state, prefix in STATE_POSTCODE_PREFIXES.items():
            if state not in _state_capacities:
                _state_capacities[state] = 0

            if postcode_prefix.startswith(prefix):
                _state_capacities[state] += capacity_val

    # derive state capacity models
    _state_capacity_models = []

    for state, state_capacity in _state_capacities.items():
        capacity_registered = state_capacity

        if state.lower() in installations:
            unit_number = installations[state.lower()]

        _state_capacity_models.append(
            APVIStateRooftopCapacity(
                state=state, capacity_registered=capacity_registered, unit_number=unit_number
            )
        )

    apvi_forecast_set = APVIForecastSet(
        crawled=_run_at, intervals=_interval_records, capacities=_state_capacity_models
    )

    return apvi_forecast_set


if __name__ == "__main__":
    cr = get_apvi_rooftop_data()

    with open("apvi.json", "w") as fh:
        fh.write(cr.json(indent=4))
