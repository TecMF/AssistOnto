# AssistOnto

## Test locally

    hatch shell # we use hatch for development (see pyproject.toml)
    # run from the assistonto directory, with (test) assistonto.db
    # in root directory, and the variables in dev.env in the environment
    hatch run dev:server

## Build & Deploy

Build container image and transfer it to server:

    rm -r assistonto/__pycache__/
    podman build -t assistonto .
    podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load

Then delete old container, and run the new one:

    service assistonto stop
    docker rm assistonto_server
    docker run --detach --name assistonto_server -p 8080:8080 --env-file /opt/assistonto/assistonto.env -v /opt/assistonto/assistonto.db:/opt/assistonto/assistonto.db localhost/assistonto
    service assistonto start

To make deployment faster, I have been mounting the code as a volume
inside the container instead of deploying. This way we only need to
deploy when we change or update dependencies.

Run SQLite on the server:
    sudo -u assistonto ./sqlite3 /opt/assistonto/assistonto.db

## Configuration

Use the following environment variables:
    ASSISTONTO_DB_PATH=assistonto.db # path to database
    ASSISTONTO_SECRET_KEY=dkfjkdgj # Flask secret key
    ASSISTONTO_MODELS='{"<model_name>": {"default": "true", "url": "<model_url>", "credentials": "<api_key>"}, "<another_model": {"credentials": {"file": "<file_containing_api_key"}}}'
    ASSISTONTO_MAX_MESSAGES_SHOWN=100
