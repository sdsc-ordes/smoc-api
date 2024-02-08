FROM python:3.11-slim

ENV PYTHONUNBUFFERED=true
WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/sdsc-ordes/smoc-api
LABEL org.opencontainers.image.description="Serve multi-omics digital objejcts"
LABEL org.opencontainers.image.licenses=Apache-2.0

##################################################
# Poetry setup
##################################################
FROM python as poetry

WORKDIR /app
# Install poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN python -c 'from urllib.request import urlopen; print(urlopen("https://install.python-poetry.org").read().decode())' | python -

# Copy necessary files only
COPY ./modo/ ./modo
COPY ./pyproject.toml ./pyproject.toml
COPY ./README.md ./README.md
COPY ./poetry.lock ./poetry.lock
RUN apt-get update && \
    apt-get install -y gcc

# Poetry install
RUN poetry install --no-interaction --no-ansi -vvv


##################################################
# SMOC server setup
##################################################
FROM python as runtime
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=poetry /app /app

# Set user
RUN useradd -ms /bin/bash modo_user
USER modo_user

# Test run
RUN modo --help

CMD ["modo"]
