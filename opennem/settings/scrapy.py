"""
Scrapy settings for nemweb project

For simplicity, this file contains only settings considered important or
commonly used. You can find more settings consulting the documentation:

https://docs.scrapy.org/en/latest/topics/settings.html
"""

BOT_NAME = "opennem"
SPIDER_MODULES = ["opennem.spiders"]
NEWSPIDER_MODULE = "opennem.spiders"

LOG_LEVEL = "ERROR"
LOG_STDOUT = False

USER_AGENT = "opennem/v3.0.0 (+https://opennem.org.au)"
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 8
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;v=b3;q=0.9",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

DNSCACHE_ENABLED = True
DNS_TIMEOUT = 10

# SPIDER_MODULES = ["opennem.spiders"]
SPIDER_LOADER_WARN_ONLY = True

EXTENSIONS = {
    "opennem.middlewares.spider_store_meta.ExtensionSpiderStoreMeta": 200,
    "opennem.middlewares.random_agent.RandomUserAgentMiddleware": 210,
}

# Pipline docs:
# 1xx series - download handlers
# 2xx series - unpackers
# 3xx series -
# 4xx series - database processes
ITEM_PIPELINES = {
    # Generic Pipelines
    "opennem.pipelines.files.LinkExtract": 101,
    "opennem.pipelines.nem.UnzipSingleFilePipeline": 302,
    "opennem.pipelines.nem.ReadStringHandle": 310,
    "opennem.pipelines.nem.ExtractCSV": 320,
    "opennem.pipelines.nem.TableRecordSplitter": 330,
    # AEMO XLS Parsers
    "opennem.pipelines.aemo.registration_exemption.RegistrationExemptionGrouperPipeline": 350,
    "opennem.pipelines.aemo.general_information.GeneralInformationGrouperPipeline": 351,
    "opennem.pipelines.aemo.registration_exemption.RegistrationExemptionStorePipeline": 355,
    "opennem.pipelines.aemo.general_information.GeneralInformationStoragePipeline": 356,
    # AEMO Download monitor
    "opennem.pipelines.aemo.downloads.DownloadMonitorPipeline": 360,
    # Opennem storers
    "opennem.pipelines.nem.DatabaseStore": 400,
    "opennem.pipelines.nem.opennem.NemwebUnitScadaOpenNEMStorePipeline": 405,
    "opennem.pipelines.wem.facilities.WemStoreFacility": 410,
    "opennem.pipelines.wem.facility_scada.WemStoreFacilityScada": 411,
    "opennem.pipelines.wem.balancing_summary.WemStoreBalancingSummary": 412,
    "opennem.pipelines.wem.pulse.WemStorePulse": 414,
    "opennem.pipelines.wem.facility_scada.WemStoreLiveFacilityScada": 415,
    "opennem.pipelines.wem.facility_scada.WemStoreFacilityIntervals": 416,
    "opennem.pipelines.wem.facilities.WemStoreLiveFacilities": 417,
    "opennem.pipelines.wem.participant.WemStoreParticipant": 418,
    "opennem.pipelines.wem.participant.WemStoreLiveParticipant": 419,
    "opennem.pipelines.nem.summary.NemwebSummaryPipeline": 420,
    # APVI
    "opennem.pipelines.apvi.data.APVIStoreData": 450,
    # NPI
    "opennem.pipelines.npi.facilities.NPIStoreFacility": 455,
    # BOM Storers
    "opennem.pipelines.bom.StoreBomObservation": 470,
    # MMS Parsers and Storers
    "opennem.pipelines.nem.mms_dudetailsummary.AEMOMMSDudetailSummaryGrouper": 504,
    "opennem.pipelines.nem.mms.NemStoreMMSStations": 551,
    "opennem.pipelines.nem.mms.NemStoreMMSStationStatus": 552,
    "opennem.pipelines.nem.mms.NemStoreMMSDudetail": 553,
    "opennem.pipelines.nem.mms.NemStoreMMSDudetailSummary": 554,
    "opennem.pipelines.nem.mms.NemStoreMMSParticipant": 555,
    # DB bulk Inserterers
    "opennem.pipelines.csv.RecordsToCSVPipeline": 610,
    "opennem.pipelines.bulk_insert.BulkInsertPipeline": 620,
    #
}

# @TODO if DEBUG
HTTPCACHE_ENABLED = False
# HTTPCACHE_DIR = ".scrapy"

RETRY_ENABLED = True
RETRY_TIMES = 9
RETRY_HTTP_CODES = [400, 403, 500, 502, 503, 504, 522, 524, 408, 429]

# OpenNEM extensions
STOREMETA_ENABLED = True
