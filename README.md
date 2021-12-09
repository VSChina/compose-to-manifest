# iotedge-compose
Convert Docker Compose project to Azure IoT Edge deployment manifest.

## Requirements
1. Make sure docker is running on your system before using this tool.
2. Python version >= `3.6.0`.
## Installation
```bash
pip install --user iotedge-compose
```


## Usage
```
iotedge-compose [-h] -t [file|project] -i docker_compose_file_path -o output_path [-r your_docker_container_registry_address]
```

## Examples
1. Convert single file
    ```bash
    iotedge-compose -t file -i example/flask-redis/docker-compose.yml -o example/flask-redis/deployment.json
    ```
2. Convert project
    ```bash
    iotedge-compose -t project -i example/flask-redis/docker-compose.yml -o example/flask-redis-edge
    ```

## Support
The team monitors the issue section on regular basis and will try to assist with troubleshooting or questions related IoT Edge tools on a best effort basis.
	
A few tips before opening an issue. Try to generalize the problem as much as possible. Examples include
- Removing 3rd party components
- Reproduce the issue with provided deployment manifest used
- Specify whether issue is reproducible on physical device or simulated device or both
Also, Consider consulting on the [docker docs channel](https://github.com/docker/docker.github.io) for general docker questions.
