import sys
import shutil
from pathlib import Path
from docker.api.container import ContainerConfig
import json
import argparse
sys.path.insert(0, str(Path(__file__).parent.joinpath("./compose")))
from compose.cli.command import project_from_options


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
                "username": "$CONTAINER_REGISTRY_USERNAME",
                "password": "$CONTAINER_REGISTRY_PASSWORD",
                "address": "$CONTAINER_REGISTRY_ADDRESS"
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

        try:
            del api_config["HostConfig"]["NetworkMode"]
        except KeyError:
            pass

        try:
            del api_config["NetworkingConfig"]
        except KeyError:
            pass

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


def convert(compose_file_name: str, cr: str):
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

    path_of_compose_file = Path(compose_file_name).absolute().resolve()
    project_name = path_of_compose_file.parts[-2]
    root = path_of_compose_file.parent.parent
    edge_solution = root.joinpath(project_name + "-edge")
    edge_solution.mkdir()
    modules_dir = edge_solution.joinpath("modules")
    modules_dir.mkdir()

    # create module.json
    for name in project.service_names:
        service = project.get_service(name)
        build_opt = service.options.get("build", {})
        # make module directory
        if "context" in build_opt:
            shutil.copytree(build_opt["context"], str(modules_dir.joinpath(name)))

        buildOptions = []
        dockerfile = "Dockerfile"
        if "dockerfile" in build_opt:
            dockerfile = build_opt["dockerfile"]
        if "args" in build_opt and build_opt["args"]:
            if isinstance(build_opt["args"], dict):
                for arg in build_opt["args"]:
                    buildOptions.append("--build-arg {}={}".format(arg, build_opt["args"][arg]))
            elif isinstance(build_opt["args"], list):
                for arg in build_opt["args"]:
                    buildOptions.append("--build-arg {}".format(arg))
        if "cache_from" in build_opt:
            for item in build_opt["cache_from"]:
                buildOptions.append("--cache-from {}".format(item))
        if "labels" in build_opt:
            if isinstance(build_opt["labels"], dict):
                for item in build_opt["labels"]:
                    buildOptions.append("--label {}={}".format(item, build_opt["labels"][item]))
            elif isinstance(build_opt["labels"], list):
                for item in build_opt["labels"]:
                    buildOptions.append("--label {}".format(item))
        if "shm_size" in build_opt:
            buildOptions.append("--shm-size {}".format(build_opt["shm_size"]))

        if "target" in build_opt:
            buildOptions.append("--target {}".format(build_opt["target"]))

        module_json_template = {
            "$schema-version": "0.0.1",
            "description": "",
            "image": {
                "repository": "{}/{}".format(cr, name),
                "tag": {
                    "version": "0.0.1",
                    "platforms": {
                        "amd64": dockerfile,
                    }
                },
                "buildOptions": buildOptions,
                "contextPath": "./"
            }
        }
        if build_opt:
            module_json_path = modules_dir.joinpath(name).joinpath("module.json")
            with open(str(module_json_path), "w", encoding="utf8") as fp:
                fp.write(json.dumps(module_json_template, indent=4))
                fp.write("\n")

    # create deployment.template.json
    modules = get_module_options(compose_file_name)
    template["modulesContent"]["$edgeAgent"]["properties.desired"]["modules"] = modules
    deployment_file = edge_solution.joinpath("deployment.template.json")
    with open(str(deployment_file), "w") as fp:
        fp.write(json.dumps(template, indent=2))

    # create .env
    env_file = edge_solution.joinpath(".env")
    with open(str(env_file), "w", encoding="utf8") as fp:
        fp.write("CONTAINER_REGISTRY_USERNAME=\n")
        fp.write("CONTAINER_REGISTRY_PASSWORD=\n")
        fp.write("CONTAINER_REGISTRY_ADDRESS=\n")


def main():
    parser = argparse.ArgumentParser(description="Compose to manifest")
    parser.add_argument("-i", "--input", type=str, help="Input compose file path", required=True)
    parser.add_argument("-r", "--registry", type=str, help="Container registry address", required=False)
    args = parser.parse_args()
    if not args.registry:
        args.registry = "http://localhost:5000"
    convert(args.input, args.registry)


if __name__ == "__main__":
    main()
