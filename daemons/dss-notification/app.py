import os
import sys

import domovoi
import requests

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'domovoilib'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from dss.logging import configure_daemon_logging
from dss.stepfunctions.visitation.process_notifications import ProcessNotifications


configure_daemon_logging()
app = domovoi.Domovoi(configure_logs=False)


@app.scheduled_function('rate(5 minutes)')
def kickoff_notification_visitation(event, context):
    visitation_id = ProcessNotifications.start(
        replica='',
        bucket='',
        number_of_workers=1
    )
