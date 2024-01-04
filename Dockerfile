FROM python:3.10-alpine3.18

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./app /app
WORKDIR /app
EXPOSE 8000

# Create a Python virtual environment
RUN python -m venv /py

# Upgrade pip
RUN /py/bin/pip install --upgrade pip

# Install PostgreSQL client and build dependencies
RUN apk add --update --no-cache postgresql-client jpeg-dev
RUN apk add --update --no-cache --virtual .tmp-build-deps \
        build-base postgresql-dev musl-dev zlib zlib-dev

# Install Python dependencies
RUN /py/bin/pip install -r /tmp/requirements.txt

# Clean up
RUN rm -rf /tmp
RUN apk del .tmp-build-deps

# Add a non-root user
RUN adduser --disabled-password --no-create-home django-user && \
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    chown -R django-user:django-user /vol && \
    chmod -R 755 /vol

ENV PATH="/py/bin:$PATH"

USER django-user
