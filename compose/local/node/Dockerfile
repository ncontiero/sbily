FROM node:22.17.1-bookworm-slim

WORKDIR /app

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable pnpm

COPY ./package.json /app

RUN pnpm install

ENV PATH=./node_modules/.bin/:$PATH

RUN chown node:node /app

USER node
