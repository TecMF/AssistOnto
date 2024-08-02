# AssistOnto

## Test locally

    hatch shell # we use hatch for development (see pyproject.toml)
    # run from the assistonto directory, with (test) assistonto.db in root directory
    ASSISTONTO_SECRET_KEY='sdfhdjhd' ASSISTONTO_OPENAI_API_KEY=(head -1 ~/me/secrets/openai.key) hatch run dev:server

## Build & Deploy

Build container image and transfer it to server:

    rm -r assistonto/__pycache__/
    podman build -t assistonto .
    podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load

Then delete old container, and run the new one:

    systemctl stop assistonto
    docker rm assistonto_server
    docker run --detach --name assistonto_server -p 8080:8080 --env-file /opt/assistonto/assistonto.env -v /opt/assistonto/assistonto.db:/opt/assistonto/assistonto.db localhost/assistonto
    systemctl start assistonto

## Configuration

Use the following environment variables:
    ASSISTONTO_DB_PATH=assistonto.db # path to database
    ASSISTONTO_SECRET_KEY=dkfjkdgj # Flask secret key
    ASSISTONTO_OPENAI_API_KEY=kdjfkdgj # OpenAi API key

And do check out and modify the `default_settings.py` file.