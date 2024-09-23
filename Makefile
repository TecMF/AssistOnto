check:
	poetry run ruff check .

build:
	rm -rf assistonto/__pycache__/
	podman build -t assistonto .

deploy: build
	podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load
