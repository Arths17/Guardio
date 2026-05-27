FROM python:3.11-slim

# Use a dedicated non-root user for security
ARG USER=guardio
ARG UID=1000
ARG GID=1000

ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PATH="/home/${USER}/.local/bin:${PATH}"

WORKDIR /srv/guardio

# Install runtime deps first (cached layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user and ensure ownership
RUN groupadd -g ${GID} ${USER} \
	&& useradd -m -u ${UID} -g ${GID} ${USER} || true \
	&& chown -R ${USER}:${USER} /srv/guardio

USER ${USER}

EXPOSE 8000

# Healthcheck for container orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/live || exit 1

# Run uvicorn with multiple workers for production
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
