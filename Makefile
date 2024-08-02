build:
	rm -r assistonto/__pycache__/
	podman build -t assistonto .

deploy:
	podman save localhost/assistonto | bzip2 | ssh vm-assistonto docker load
