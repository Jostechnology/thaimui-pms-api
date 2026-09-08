# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9-slim-bookworm

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1 


# Install build deps. update and install share one layer so the package index
# can't go stale between them (a cached update layer + fresh install layer is
# the classic "Unable to fetch some archives" cause). ForceIPv4 + Retries
# defeat an unreachable IPv6 mirror and transient CDN index/pool skew.
RUN apt-get update -o Acquire::ForceIPv4=true -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
        -o Acquire::ForceIPv4=true -o Acquire::Retries=5 \
        python3-dev default-libmysqlclient-dev gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
WORKDIR /
COPY . /
ARG ENV 
ADD ${ENV} ./
EXPOSE 5000
# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
# RUN useradd appuser && chown -R appuser /
# USER appuser

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
ENTRYPOINT ["/entrypoint.sh"]
