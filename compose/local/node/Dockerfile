FROM node:24.17.0-bookworm-slim@sha256:c2d5ade763cacfb03fe9cb8e8af5d1be5041ff331921fa26a9b231ca3a4f780a

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
