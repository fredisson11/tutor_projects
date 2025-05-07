FROM python:3.12.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpq5 \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev

COPY requirements.txt requirements.txt
RUN pip install -v --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --no-create-home my_user

COPY . .

RUN chmod +x /app/entrypoint.sh && \
    chown -R my_user /app && \
    chmod -R 755 /app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
