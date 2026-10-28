Move notification delivery out of the sendalerts process into Celery workers with a Redis broker, so that delivery can scale across several worker machines. Keep every existing integration working.
