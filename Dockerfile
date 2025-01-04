FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p downloads && \
    chown -R 1000:1000 /app && \
    chmod -R 755 /app && \
    chmod 1777 /app/downloads

COPY . .

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8721

CMD ["gunicorn", "--bind", "0.0.0.0:8721", "--workers", "4", "--timeout", "300", "--keep-alive", "5", "--worker-class", "gevent", "wsgi:app"] 