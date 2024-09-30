check:
	poetry run ruff check .

build:
	rm -rf assistonto/__pycache__/
	podman build --tag assistonto --annotation "git_version=$$(git rev-parse --short HEAD)" .

deploy: build
	podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load
