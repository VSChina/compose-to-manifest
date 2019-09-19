# iotedge-compose
Convert Docker Compose project to Azure IoT Edge deployment manifest.

## Requirements
1. Make sure docker is running on your system before using this tool.
2. Python version >= `3.6.0`.
## Installation
```bash
pip3 install iotedge-compose
```


## Usage
```
iotedge-compose [-h] -t [file|project] -i docker_compose_file_path -o output_path [-r your_docker_container_registry_address]
```

## Examples
1. Convert single file
    ```bash
    iotedge-compose -t file -i example/flask-redis/docker-compose.yml -o example/flask-redis/deployment.template.json
    ```
2. Convert project
    ```bash
    iotedge-compose -t project -i example/flask-redis/docker-compose.yml -o example/flask-redis-edge
    ```
