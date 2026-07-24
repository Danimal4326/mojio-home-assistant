"""Constants for the Mojio integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "mojio"
LOGGER: Final = logging.getLogger(__package__)

CONF_TENANT: Final = "tenant"

# The SDK maps "audi" onto the audi-us-phoenix-production tenant. Any raw
# tenant string is still accepted.
DEFAULT_TENANT: Final = "audi"

DEFAULT_SCAN_INTERVAL: Final = 300
MIN_SCAN_INTERVAL: Final = 60
MAX_SCAN_INTERVAL: Final = 3600

ATTRIBUTION: Final = "Data provided by Mojio"
