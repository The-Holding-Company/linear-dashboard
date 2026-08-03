FROM python:3.13-alpine

WORKDIR /app
COPY src/ src/
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /app/dist

ENTRYPOINT ["/entrypoint.sh"]
