# AssistOnto

Test locally:

    ASSISTONTO_OPENAI_API_KEY=(head -1 ~/me/secrets/openai.key) ASSISTONTO_SECRET_KEY='sdfhdjhd' gunicorn --config gunicorn_config.py 'app:app'

Build container image and transfer it to server:

    podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load

Then delete old image, and run the new one:

    docker rm assistonto_server
    docker run --detach --name assistonto_server -p 8080:8080 --env-file /opt/assistonto/assistonto.env -v /opt/assistonto/assistonto.db:/opt/assistonto/assistonto.db localhost/assistonto
    systemctl restart assistonto