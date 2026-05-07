FROM node:24.15.0-bookworm-slim

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
