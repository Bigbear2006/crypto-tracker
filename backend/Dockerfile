FROM python:3.11-alpine

RUN apk update && apk add --no-cache postgresql-dev

WORKDIR app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .