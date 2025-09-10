FROM python:3.11-slim

# Create a non-root user for better security
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  git \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip3 install --upgrade pip && \
  pip3 install -r requirements.txt

# Copy application code
COPY . .

# Change ownership to the app user
RUN chown -R app:app /app

# Create workspace directory for OI file outputs
RUN mkdir -p /app/workspace && chown -R app:app /app/workspace

# Switch to non-root user
USER app

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false
