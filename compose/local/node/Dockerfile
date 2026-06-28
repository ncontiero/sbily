FROM node:24.18.0-bookworm-slim@sha256:b31e7a42fdf8b8aa5f5ed477c72d694301273f1069c5a2f71d53c6482e99a2fc

WORKDIR /app

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV CI=true

RUN corepack enable pnpm

COPY ./package.json ./pnpm-workspace.yaml ./pnpm-lock.yaml /app/

RUN pnpm install --frozen-lockfile

ENV PATH=./node_modules/.bin/:$PATH

RUN chown node:node /app
RUN chown -R node:node /app/node_modules

USER node
