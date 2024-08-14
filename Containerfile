# to test locally: podman run --env-file dev.env -it --rm -p 8080:8080 assistonto # but api_key might need to be passed directly
FROM python:3

COPY requirements.txt /

RUN pip3 install --upgrade pip

RUN pip3 install -r requirements.txt

COPY . /

RUN pip3 install .

WORKDIR /assistonto

EXPOSE 8080

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]