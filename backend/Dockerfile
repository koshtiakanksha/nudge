FROM python:3.12-slim AS base

# System deps: psycopg2/cryptography build deps, plus minimal libs Prophet's
# cmdstan needs if you choose to compile it at build time (see note below).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: pre-install Prophet's cmdstan backend at build time so real
# Prophet forecasting is available immediately rather than falling back to
# the moving-average projection. This adds several minutes to the build.
# Uncomment to enable:
# RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
