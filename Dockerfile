FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads && chmod 777 downloads

RUN useradd -m appuser
USER appuser

EXPOSE 8721

CMD ["gunicorn", "--bind", "0.0.0.0:8721", "--workers", "4", "--timeout", "120", "wsgi:app"] 