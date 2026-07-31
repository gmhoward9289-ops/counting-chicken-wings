# Portable image. Runs identically on Fly.io, Railway, Render, or the EC2
# box -- nothing here is provider-specific.
#
# The database is built INTO the image rather than mounted at runtime. That
# works because the app never writes to it, and it means the image is fully
# self-contained: no volume, no init container, no first-run migration. Roll
# back the image and you roll back the data with it.

FROM python:3.12-slim

WORKDIR /app

# Dependency layer first so code edits do not invalidate the pip cache.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e ".[gui]"

COPY data/ ./data/

# Build the database, then assert every statistic still carries a citation.
# The audit exits non-zero on an uncited figure, so a bad data commit fails
# the image build rather than shipping.
RUN python -m counting_chicken_wings.build \
 && python -m counting_chicken_wings.audit

# Most platforms inject $PORT; default to 8000 for a bare `docker run`.
ENV PORT=8000
EXPOSE 8000

# Run unprivileged.
RUN useradd --create-home --uid 10001 wings && chown -R wings /app

USER wings

CMD ["sh", "-c", "uvicorn counting_chicken_wings.api:app --host 0.0.0.0 --port ${PORT}"]
