FROM python:3.7-slim
LABEL maintainer="Tal Almagor <tal@coretext.com>"

# working directory
ENV DOCCANO_HOME="/doccano"

# http://bugs.python.org/issue19846
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends --fix-missing \
    software-properties-common \
    build-essential \
    gcc \
    curl \
    unzip \
    bzip2 \
 && apt-get clean -y \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /tmp/requirements.txt \
 && pip install awscli

COPY app ${DOCCANO_HOME}/app
WORKDIR ${DOCCANO_HOME}/app

COPY docker/docker-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# ENV PYTHONPATH "${PYTHONPATH}:${DOCCANO_HOME}"
# CMD ["python", "manage.py", "runserver"]
