# to test locally: podman run -e ASSISTONTO_SECRET_KEY='sdfhdjhd' -e ASSISTONTO_OPENAI_API_KEY=(head -1 ~/me/secrets/openai.key) -it --rm -p 8080:8080 assistonto
FROM python:3

COPY requirements.txt /

RUN pip3 install --upgrade pip

RUN pip3 install -r requirements.txt

COPY . /

RUN pip3 install .

WORKDIR /assistonto

EXPOSE 8080

CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]