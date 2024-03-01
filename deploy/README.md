# Server deployment

> [!WARNING]
> This is a work in progress and not production-ready yet.

## Context

This directory contains the necessary files to deploy a multi-omics digital objects (MODO) server.

The modo-server is meant to provide remote access to the MODOs. Currently, it can:

* [x] list available MODO
* [x] return their metadata
* [x] expose a MODO directly as a client-accessible S3 bucket / folder
* [ ] stream CRAM slices CRAM using htsget
* [ ] manage authentication and access control

The MODOs are stored in an s3 (minio) bucket, and an htsget server is deployed alongside the modo-server to handle slicing and streaming of CRAM files. A REST API is exposed to the client to interact with the remote MODOs.

All services are accessible at a single access point through an nginx reverse proxy on port 80.


```mermaid
flowchart TB
P0((80)) -.-> nginx
subgraph " "
  Vnginxdefaultconftemplate{{./nginx/default.conf.template}} -. "/etc/nginx/templates/default.conf.template" .-x nginx
  Vminiodata([minio-data]) x-. /bitnami/minio/data .-x minio
  Vminiodata x-. /data/s3 .-x htsget
  P1((9001)) -.-> minio
  nginx -.- modonetwork[/modo-network/]
  minio -.- modonetwork
  htsget -.- modonetwork
  modoserver[modo-server] -.- modonetwork

  classDef volumes fill:#fdfae4,stroke:#867a22
  class Vnginxdefaultconftemplate,Vminiodata,Vminiodata volumes
  classDef ports fill:#f8f8f8,stroke:#ccc
  class P0,P1 ports
  classDef nets fill:#fbfff7,stroke:#8bc34a
  class modonetwork nets
end

```

## Setup

> [!IMPORTANT]
> The instructions below are meant for local testing.
> Production use would require changing the default
> credentials and use authentication.

1. Start the server
```sh
cd deploy
docker compose up --build
```
2. Upload MODO(s) to the default bucket from the minio console (default is http://localhost:9001)
3. Login to the minio console (default credentials are minio/miniosecret)

## Usage

Once the server is started, a client can connect to the following endpoints:
* `http://localhost:80/htsget`: directly access the htsget server
* `http://localhost:80/s3`: directly access the s3 server
* `http://localhost:80/list`: list modos on the server
* `http://localhost:80/meta`: return all metadata on the server
