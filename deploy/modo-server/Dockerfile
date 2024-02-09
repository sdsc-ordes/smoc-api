FROM ghcr.io/sdsc-ordes/smoc-api:latest

WORKDIR /app
COPY ./server.py /app

USER root

RUN pip install \
  fastapi \
  uvicorn \
  s3fs

USER modo_user

CMD ["uvicorn", "server:app", "--reload"]
