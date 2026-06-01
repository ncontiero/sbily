FROM traefik:v3.6.14@sha256:4cda3393930dceff030e144b46260e96e1337c9cfaa4fed81c90cb8f4d498f57
RUN mkdir -p /etc/traefik/acme \
  && touch /etc/traefik/acme/acme.json \
  && chmod 600 /etc/traefik/acme/acme.json
COPY ./compose/production/traefik/traefik.yml /etc/traefik
