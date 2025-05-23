# AssistOnto

## Setting up RAG

Create a directory named `my_doc_dir` filled with plaintext documents,
then call

    poetry run assistonto docs --docdb-path my_assistonto_docs.db --add my_doc_dir

to add the documents to the vector database, with their base
filenames (without extension) as IDs. Then specify
`my_assistonto_docs.db` using the `ASSISTONTO_DOCDB_PATH`
environment variable.

## Test locally

    poetry shell # we use poetry for development (see pyproject.toml)
    # run from the root directory, with (test) assistonto.db
    # in assistonto directory, and the variables in dev.env in the environment
    poetry run assistonto server

## Build & Deploy

Build container image and transfer it to server:

    make build
    make deploy

Then delete old container, and run the new one:

    service assistonto stop
    docker rm assistonto_server
    docker run --detach --name assistonto_server -p 8080:8080 --env-file /opt/assistonto/assistonto.env -v /opt/assistonto/assistonto.db:/opt/assistonto/assistonto.db localhost/assistonto
    service assistonto start

To make deployment faster, I have been mounting the code as a volume
inside the container instead of deploying. This way we only need to
deploy when we change or update dependencies.
    -v /home/bclaro/AssistOnto/assistonto:/assistonto

Run SQLite on the server:
    sudo -u assistonto ./sqlite3 /opt/assistonto/assistonto.db

## Configuration

Use the following environment variables:
    ASSISTONTO_DB_PATH=assistonto.db # path to database
    ASSISTONTO_SECRET_KEY=dkfjkdgj # Flask secret key
    ASSISTONTO_MODELS='{"<model_name>": {"default": "true", "url": "<model_url>", "credentials": "<api_key>"}, "<another_model": {"credentials": {"file": "<file_containing_api_key"}}}'
    ASSISTONTO_MAX_MESSAGES_SHOWN=100
    ASSISTONTO_DOCDB_PATH=assistonto_docs.db
