FROM python:3.12-slim

WORKDIR /app

# (Submodule removal step completed; database fetching moved later in build process)

# Set default NES_DB_URL for container
ENV NES_DB_URL=file+memcached:///app/nes-db/v2

COPY pyproject.toml poetry.lock README.md ./
COPY nes/ ./nes/
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --extras api --only=main

COPY docs/ ./docs/

# Fetch the public database late in the build process to maximize caching of code dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/NewNepal-org/NepalEntityService-database.git ./nes-db

EXPOSE 8080

CMD ["nes-api"]