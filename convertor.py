import sys
import shutil
from pathlib import Path
from docker.api.container import ContainerConfig
import json
import argparse
import logging
sys.path.insert(0, str(Path(__file__).parent.joinpath("./compose")))
from compose.cli.command import project_from_options

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

template = {
  "$schema-template": "2.0.0",
  "modulesContent": {
    "$edgeAgent": {
      "properties.desired": {
        "schemaVersion": "1.0",
        "runtime": {
          "type": "docker",
          "settings": {
            "minDockerVersion": "v1.25",
            "loggingOptions": "",
            "registryCredentials": {
              "REGISTRY0": {
                "username": "${CONTAINER_REGISTRY_USERNAME}",
                "password": "${CONTAINER_REGISTRY_PASSWORD}",
                "address": "${CONTAINER_REGISTRY_ADDRESS}"
              }
            }
          }
        },
        "systemModules": {
          "edgeAgent": {
            "type": "docker",
            "settings": {
              "image": "mcr.microsoft.com/azureiotedge-agent:1.0",
              "createOptions": {}
            }
          },
          "edgeHub": {
            "type": "docker",
            "status": "running",
            "restartPolicy": "always",
            "settings": {
              "image": "mcr.microsoft.com/azureiotedge-hub:1.0",
              "createOptions": {
                "HostConfig": {
                  "PortBindings": {
                    "5671/tcp": [
                      {
                        "HostPort": "5671"
                      }
                    ],
                    "8883/tcp": [
                      {
                        "HostPort": "8883"
                      }
                    ],
                    "443/tcp": [
                      {
                        "HostPort": "443"
                      }
                    ]
                  }
                }
              }
            }
          }
        },
        "modules": {
        }
      }
    },
    "$edgeHub": {
      "properties.desired": {
        "schemaVersion": "1.0",
        "routes": {
        },
        "storeAndForwardConfiguration": {
          "timeToLiveSecs": 7200
        }
      }
    }
  }
}


def get_module_options(compose_file_name: str, debug=False) -> dict:
    options = {
        '--compatibility': False,
        '--env-file': None,
        '--file': [compose_file_name],
        '--help': False,
        '--host': None,
        '--log-level': None,
        '--no-ansi': False,
        '--project-directory': None,
        '--project-name': None,
        '--skip-hostname-check': False,
        '--tls': False,
        '--tlscacert': None,
        '--tlscert': None,
        '--tlskey': None,
        '--tlsverify': False,
        '--verbose': False,
        '--version': False,
        '-h': False,
        'ARGS': ['--force-recreate'],
        'COMMAND': 'up'
    }

    project = project_from_options(".", options)
    modules = {}
    for name in project.service_names:
        service = project.get_service(name)
        create_option = service._get_container_create_options({}, 1)
        keys = [
            "image", "command", "hostname", "user", "detach", "stdin_open", "tty", "ports", "environment", "volumes",
            "network_disabled", "entrypoint", "working_dir", "domainname", "host_config", "mac_address", "labels",
            "stop_signal", "networking_config", "healthcheck", "stop_timeout", "runtime"
        ]

        # if keys not exist, set default
        params = {}
        for key in keys:
            if key in create_option:
                params[key] = create_option[key]
            else:
                params[key] = None
                if key in ["detach", "stdin_open", "tty"]:
                    params[key] = False

        api_config = ContainerConfig(project.config_version.vstring, **params)

        delete_list = []
        for k, v in api_config.items():
            if not v:
                delete_list.append(k)
        for k in delete_list:
            del api_config[k]

        delete_list = []
        for k, v in api_config["HostConfig"].items():
            if not v:
                delete_list.append(k)
        for k in delete_list:
            del api_config["HostConfig"][k]

        has_network_config = False
        try:
            del api_config["HostConfig"]["NetworkMode"]
            has_network_config = True
        except KeyError:
            pass

        try:
            del api_config["NetworkingConfig"]
            has_network_config = True
        except KeyError:
            pass
        if has_network_config:
            logging.warning("In service {}: Edge runtime doesn't support network configuration, "
                            "delete related fields".format(name))

        restart_policy = "always"
        try:
            restart_policy = api_config["HostConfig"]["RestartPolicy"]["Name"]
            if restart_policy == "no":
                restart_policy = "never"
        except KeyError:
            pass

        build_opt = service.options.get("build", {})
        image = api_config["Image"]
        del api_config["Image"]
        if build_opt:
            image = "${{MODULES.{}}}".format(name)

        if len(json.dumps(api_config)) >= 4 * 1024:
            logging.warning("In service {}: The length of createOptions is limited to 4096".format(name))

        modules[name] = {
            "version": "1.0",
            "type": "docker",
            "status": "running",
            "restartPolicy": restart_policy,
            "settings": {
                "image": image,
                "createOptions": api_config
            }
        }
    return modules


def convert(compose_file_name: str, output_file: str, cr: str):
    options = {
        '--compatibility': False,
        '--env-file': None,
        '--file': [compose_file_name],
        '--help': False,
        '--host': None,
        '--log-level': None,
        '--no-ansi': False,
        '--project-directory': None,
        '--project-name': None,
        '--skip-hostname-check': False,
        '--tls': False,
        '--tlscacert': None,
        '--tlscert': None,
        '--tlskey': None,
        '--tlsverify': False,
        '--verbose': False,
        '--version': False,
        '-h': False,
        'ARGS': ['--force-recreate'],
        'COMMAND': 'up'
    }
    project = project_from_options(".", options)

    # create deployment.template.json
    modules = get_module_options(compose_file_name)
    template["modulesContent"]["$edgeAgent"]["properties.desired"]["modules"] = modules

    with open(output_file, "w") as fp:
        fp.write(json.dumps(template, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Compose to manifest")
    parser.add_argument("-i", "--input", type=str, help="Input compose file path", required=True)
    parser.add_argument("-o", "--output", type=str, help="Output manifest file path", required=True)
    parser.add_argument("-r", "--registry", type=str, help="Container registry address", required=False)
    args = parser.parse_args()
    if not args.registry:
        args.registry = "localhost:5000"
    convert(args.input, args.output, args.registry)


if __name__ == "__main__":
    main()
