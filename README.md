# compose-to-manifest
Convert Docker Compose project to Azure IoT Edge deployment manifest

## Installation
```bash
git clone https://github.com/VSChina/compose-to-manifest --recursive
cd compose-to-manifest
git checkout single_file
pip3 install -r compose/requirements.txt
```

## Usage
```
python3 convertor.py [-h] -i docker_compose_file_path -o output_file_path [-r your_docker_container_registry_address]
```

## Example
In compose-to-manifest folder
```
python3 convertor.py -i example/flask-redis/docker-compose.yml -o deployment.template.json
```
