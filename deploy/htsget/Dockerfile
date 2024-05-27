FROM rust:1.75.0 AS builder

WORKDIR /build

RUN cargo install cargo-strip

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/umccr/htsget-rs.git --branch htsget-actix-v0.6.1 .


RUN cargo build --features s3-storage --release && cargo strip

FROM debian:stable-slim

RUN apt update && apt install -y libc6-dev awscli && rm -rf /var/lib/apt/lists/*

RUN aws configure set region us-west-1

COPY --from=builder /etc/ssl/certs/ /etc/ssl/certs/
COPY --from=builder /build/target/release/htsget-actix /usr/local/bin/htsget-actix

ENV HTSGET_TICKET_SERVER_ADDR 0.0.0.0:8080
ENV HTSGET_DATA_SERVER_ADDR 0.0.0.0:8081

EXPOSE 8080
EXPOSE 8081

CMD [ "htsget-actix" ]
