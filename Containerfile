# to test locally: podman run --rm -it --name assistonto_server -p 8080:8080 --env-file assistonto.env -v ~/sites/assistonto/assistonto.db:/opt/assistonto/assistonto.db:Z -v ~/sites/assistonto/assistonto_docs.db:/opt/assistonto/assistonto_docs.db:Z -v ~/secrets/openai.key:/opt/assistonto/openai.key:Z localhost/assistonto

FROM python:3

WORKDIR /assistonto

COPY requirements.txt .

RUN pip3 install --upgrade pip

RUN pip3 install -r requirements.txt

COPY src src/

COPY templates templates/

COPY static static/

COPY README.md .

COPY pyproject.toml .

RUN pip3 install -e .

EXPOSE 8080

CMD ["gunicorn", "--config", "src/assistonto/gunicorn_config.py", "src.assistonto.app:app"]