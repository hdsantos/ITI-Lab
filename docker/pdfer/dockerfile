FROM ubuntu:24.04

WORKDIR /app

COPY pdfer /app/pdfer

RUN chmod +x /app/pdfer \
    && mkdir -p /app/store

EXPOSE 8080

ENTRYPOINT ["/app/pdfer"]

