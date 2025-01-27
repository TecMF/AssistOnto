check:
	poetry run ruff check .

build: requirements.txt
	rm -rf assistonto/__pycache__/
	podman build --tag assistonto --annotation "git_version=$$(git rev-parse --short HEAD)" .

requirements.txt: pyproject.toml
	poetry export -f requirements.txt --output requirements.txt

deploy: build
	podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load
