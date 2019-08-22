# compose-to-manifest
Convert Docker Compose project to Azure IoT Edge deployment manifest.

## Requirements
1. Make sure docker is running on your system before using this tool.
2. Python version >= `3.6.0`.
## Installation
```bash
pip install compose-to-manifest
```


## Usage
```
python3 convertor.py [-h] -t [file|project] -i docker_compose_file_path -o output_path [-r your_docker_container_registry_address]
```

## Examples
```bash
git clone https://github.com/VSChina/compose-to-manifest
```
In compose-to-manifest folder  
1. Convert single file
    ```bash
    compose-to-manifest -t file -i example/flask-redis/docker-compose.yml -o example/flask-redis/deployment.template.json
    ```
2. Convert project
    ```bash
    compose-to-manifest -t project -i example/flask-redis/docker-compose.yml -o example/flask-redis-edge
    ```
