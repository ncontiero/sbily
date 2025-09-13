FROM node:22.19.0-bookworm-slim AS client-base

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
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS python-build-stage

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

ARG APP_HOME=/app
ARG DJANGO_AWS_S3_CUSTOM_DOMAIN

WORKDIR ${APP_HOME}

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
COPY pyproject.toml uv.lock ./
# RUN --mount=type=cache,id=s/1f3a83f7-4b84-4c12-9846-655c759ecbe7-/root/.cache/uv,target=/root/.cache/uv \
#     --mount=type=cache,id=s/7c2232d3-9bcc-4fdc-9328-e5c76f039369-/root/.cache/uv,target=/root/.cache/uv \
#     --mount=type=cache,id=s/70de0546-f921-450d-a7d1-8f9c7877bbc3-/root/.cache/uv,target=/root/.cache/uv \
#     uv sync --locked --no-install-project --no-dev
# Railway does not accept the same image for multiple cached services
RUN uv sync --locked --no-install-project --no-dev

COPY --from=client-builder ${APP_HOME} ${APP_HOME}

# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --locked --no-dev
# Railway does not accept the same image for multiple cached services
RUN uv sync --locked --no-dev

# Python 'run' stage
FROM python:3.13-slim-bookworm AS python-run-stage

ARG APP_HOME=/app
ARG PORT=5000

WORKDIR ${APP_HOME}

RUN addgroup --system django \
  && adduser --system --ingroup django django


# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg dependencies
  libpq5 \
  # geoip2 dependencies
  libmaxminddb0 \
  # entrypoint
  wait-for-it \
  # Translations dependencies
  gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

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

# Copy the application from the builder
COPY --from=python-build-stage --chown=django:django ${APP_HOME} ${APP_HOME}

# make django owner of the WORKDIR directory as well.
RUN chown django:django ${APP_HOME}

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

USER django

RUN DATABASE_URL="" \
  DJANGO_SETTINGS_MODULE="config.settings.test"

ENTRYPOINT ["/entrypoint"]
