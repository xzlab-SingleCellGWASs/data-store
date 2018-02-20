import logging
from time import time

from .timeout import Timeout
from . import Visitation, WalkerStatus
from dss import notifications


logger = logging.getLogger(__name__)


_SECONDS_ALLOWED = 250


class ProcessNotifications(Visitation):
    def walker_walk(self) -> None:
        while True:
            seconds_remaining = int(_SECONDS_ALLOWED - (time() - start_time))

            if 1 > seconds_remaining:
                return

            with Timeout(seconds_remaining) as timeout:
                k = notifications.process_queue()

                if 0 == k:
                    self._status = WalkerStatus.finished.name
                    return

            if timeout.did_timeout:
                logger.warning(f'{self.work_id} timed out during reindex')
                return
