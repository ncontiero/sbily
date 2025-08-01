FROM node:22.17.1-bookworm-slim AS client-base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable

WORKDIR /app

FROM client-base AS client-deps

COPY ./package.json ./pnpm-lock.yaml* ./pnpm-workspace.yaml* ./
COPY ./emails/package.json ./emails/

RUN pnpm install --frozen-lockfile
# RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
# RUN --mount=type=cache,id=s/<service id>-/pnpm/store,target=/pnpm/store pnpm install --frozen-lockfile

FROM client-base AS client-builder
COPY --from=client-deps /app/node_modules /app/node_modules
COPY --from=client-deps /app/emails/node_modules /app/emails/node_modules
COPY . /app

ARG DJANGO_AWS_STORAGE_BUCKET_NAME
ARG DJANGO_AWS_S3_CUSTOM_DOMAIN
ARG STRIPE_PUBLIC_KEY

ENV DJANGO_AWS_STORAGE_BUCKET_NAME=${DJANGO_AWS_STORAGE_BUCKET_NAME}
ENV DJANGO_AWS_S3_CUSTOM_DOMAIN=${DJANGO_AWS_S3_CUSTOM_DOMAIN}
ENV STRIPE_PUBLIC_KEY=${STRIPE_PUBLIC_KEY}

RUN pnpm run build
RUN pnpm run build:email

# define an alias for the specific python version used in this file.
FROM python:3.12.10-slim-bookworm AS python

# Python build stage
FROM python AS python-build-stage

ARG DJANGO_AWS_S3_CUSTOM_DOMAIN
ARG BUILD_ENVIRONMENT=production

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg dependencies
  libpq-dev \
  # geoip2 dependencies
  libmaxminddb0 libmaxminddb-dev mmdb-bin \
  wget

RUN wget -nv -t 3 -P ./config/geoip \
  https://${DJANGO_AWS_S3_CUSTOM_DOMAIN}/geoip/GeoLite2-Country.mmdb \
  https://${DJANGO_AWS_S3_CUSTOM_DOMAIN}/geoip/GeoLite2-City.mmdb

# Requirements are installed here to ensure they will be cached.
COPY ./requirements .

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r ${BUILD_ENVIRONMENT}.txt


# Python 'run' stage
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG PORT=5000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

RUN addgroup --system django \
  && adduser --system --ingroup django django


# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg dependencies
  libpq-dev \
  # geoip2 dependencies
  libmaxminddb0 libmaxminddb-dev mmdb-bin \
  # entrypoint
  wait-for-it \
  # Translations dependencies
  gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy GeoIP database
COPY --from=python-build-stage ./config/geoip ./config/geoip
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/


COPY --chown=django:django ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY --chown=django:django ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY --chown=django:django ./compose/production/django/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY --chown=django:django ./compose/production/django/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY --chown=django:django ./compose/production/django/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower

# copy application code to WORKDIR
COPY --from=client-builder --chown=django:django ${APP_HOME} ${APP_HOME}

# make django owner of the WORKDIR directory as well.
RUN chown -R django:django ${APP_HOME}

USER django

RUN DATABASE_URL="" \
  DJANGO_SETTINGS_MODULE="config.settings.test"

ENTRYPOINT ["/entrypoint"]
