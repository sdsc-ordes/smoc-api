FROM ghcr.io/sdsc-ordes/modo-api:latest

WORKDIR /app
COPY ./server.py /app

USER root

RUN pip install \
  "fastapi ~= 0.109.2" \
  "uvicorn ~= 0.27.0.post1" \
  "s3fs == 2024.2.0"

USER modo_user

CMD ["uvicorn", "server:app", "--reload"]
