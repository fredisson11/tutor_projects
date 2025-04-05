FROM python:3.11-alpine3.18
LABEL maintainer="mgoryn68@gmail.com"

ENV PYTHONUNBUFFERED=1

WORKDIR /app/


COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser \
        --disabled-password \
        --no-create-home \
        my_user

RUN chown -R my_user /files/media
RUN chmod -R 755 /files/media

RUN mkdir -p /files/media

COPY . .

RUN chown -R my_user /app

RUN chmod -R 755 /app

EXPOSE 8000

# Команда запуску контейнера
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
