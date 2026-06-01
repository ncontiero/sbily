FROM node:24.16.0-bookworm-slim@sha256:242549cd46785b480c832479a730f4f2a20865d61ea2e404fdb2a5c3d3b73ecf

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
