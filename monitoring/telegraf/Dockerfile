FROM telegraf:1.33

USER root
RUN apt-get update \
	&& DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 \
	&& rm -rf /var/lib/apt/lists/*

COPY ami_metrics.py /usr/local/bin/ami_metrics.py
COPY log_metrics.py /usr/local/bin/log_metrics.py
RUN chmod 755 /usr/local/bin/ami_metrics.py /usr/local/bin/log_metrics.py

USER telegraf
