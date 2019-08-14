# compose-to-manifest
Convert Docker Compose project to Azure IoT Edge deployment manifest

## Installation
```bash
git clone https://github.com/VSChina/compose-to-manifest --recursive
cd compose-to-manifest
pip3 install -r compose/requirements.txt
```
Make sure docker is running on your system before using this tool.

## Usage
```
python3 convertor.py [-h] -t [file|project] -i docker_compose_file_path -o output_path [-r your_docker_container_registry_address]
```

## Example
In compose-to-manifest folder  
1. Convert single file
    ```bash
    python3 convertor.py -t file -i example/flask-redis/docker-compose.yml -o example/flask-redis/deployment.template.json
    ```
2. Convert project
    ```bash
    python3 convertor.py -t project -i example/flask-redis/docker-compose.yml -o example/flask-redis-edge
    ```
