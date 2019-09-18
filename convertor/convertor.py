import sys
import shutil
from pathlib import Path
from docker.api.container import ContainerConfig
import json
import yaml
import argparse
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
    project_dir = Path(compose_file_name).absolute().resolve().parent
    options = {
        '--compatibility': False,
        '--env-file': None,
        '--file': [compose_file_name],
        '--help': False,
        '--host': None,
        '--log-level': None,
        '--no-ansi': False,
        '--project-directory': project_dir,
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

        # if keys not exist, set default, required by function ContainerConfig
        params = {}
        for key in keys:
            if key in create_option:
                params[key] = create_option[key]
            else:
                params[key] = None
                if key in ["detach", "stdin_open", "tty"]:
                    params[key] = False

        create_options = ContainerConfig(project.config_version.vstring, **params)

        # delete empty fields
        delete_list = []
        for k, v in create_options.items():
            if not v:
                delete_list.append(k)
        for k in delete_list:
            del create_options[k]

        delete_list = []
        for k, v in create_options["HostConfig"].items():
            if not v:
                delete_list.append(k)
        for k in delete_list:
            del create_options["HostConfig"][k]

        if service.network_mode.network_mode == project.name + "_default":
            try:
                del create_options["HostConfig"]["NetworkMode"]
            except KeyError:
                pass
            try:
                del create_options["NetworkingConfig"]
            except KeyError:
                pass

        restart_policy = "always"
        try:
            restart_policy = create_options["HostConfig"]["RestartPolicy"]["Name"]
            if restart_policy == "no":
                restart_policy = "never"
        except KeyError:
            pass

        # set folder reference if build option in compose file
        build_opt = service.options.get("build", {})
        image = create_options["Image"]
        del create_options["Image"]
        if build_opt:
            image = "${{MODULES.{}}}".format(name)

        modules[name] = {
            "version": "1.0",
            "type": "docker",
            "status": "running",
            "restartPolicy": restart_policy,
            "settings": {
                "image": image,
                "createOptions": create_options
            }
        }
    return modules


def convert(convert_type: str, compose_file_name: str, output_path: str, cr: str):
    project_dir = Path(compose_file_name).absolute().resolve().parent
    options = {
        '--compatibility': False,
        '--env-file': None,
        '--file': [compose_file_name],
        '--help': False,
        '--host': None,
        '--log-level': None,
        '--no-ansi': False,
        '--project-directory': project_dir,
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

    output_path = Path(output_path).absolute().resolve()

    modules = get_module_options(compose_file_name)
    template["modulesContent"]["$edgeAgent"]["properties.desired"]["modules"] = modules

    if convert_type == "file":
        # only create deployment manifest
        with open(str(output_path), "w") as fp:
            fp.write(json.dumps(template, indent=2))
        template_to_manifest(output_path, output_path)

    if convert_type == "project":
        # need some file copy operation if convert type is project
        if not output_path.is_dir():
            output_path.mkdir()
        modules_dir = output_path.joinpath("modules")
        modules_dir.mkdir()

        deployment_file = output_path.joinpath("deployment.template.json")
        with open(str(deployment_file), "w") as fp:
            fp.write(json.dumps(template, indent=2))

        # create module.json
        for name in project.service_names:
            service = project.get_service(name)
            build_opt = service.options.get("build", {})
            # make module directory
            if "context" in build_opt:
                shutil.copytree(build_opt["context"], str(modules_dir.joinpath(name)))

            # convert build options from compose file to docker cli command
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
                # create module.json in module folder
                module_json_path = modules_dir.joinpath(name).joinpath("module.json")
                with open(str(module_json_path), "w", encoding="utf8") as fp:
                    fp.write(json.dumps(module_json_template, indent=4))
                    fp.write("\n")

            # create .env
            env_file = output_path.joinpath(".env")
            with open(str(env_file), "w", encoding="utf8") as fp:
                fp.write("CONTAINER_REGISTRY_USERNAME=\n")
                fp.write("CONTAINER_REGISTRY_PASSWORD=\n")
                fp.write("CONTAINER_REGISTRY_ADDRESS={}\n".format(cr))


def template_to_manifest(input: str, output: str):
    def fillCreateOptions(target: dict, options: dict):
        # current Edge runtime only support 4096B createOptions in 8 fields
        create_option_string = json.dumps(options)
        block_size = 512
        n = len(create_option_string)
        limit = 512 * 8
        if n > limit:
            raise ValueError("createOptions too long, exceed {} bytes".format(limit))
        for i in range(0, n, block_size):
            suffix = "{:02}".format(i // block_size) if i else ""
            target["createOptions" + suffix] = create_option_string[i:min(i + block_size, n)]

    with open(input, "r", encoding="utf8") as fp:
        j = json.load(fp)
        try:
            del j["$schema-template"]
        except KeyError:
            pass
        system_modules = j["modulesContent"]["$edgeAgent"]["properties.desired"]["systemModules"]
        for k, module in system_modules.items():
            fillCreateOptions(module["settings"], module["settings"]["createOptions"])
        user_modules = j["modulesContent"]["$edgeAgent"]["properties.desired"]["modules"]
        for k, module in user_modules.items():
            if module["settings"]["image"].startswith("$"):
                module["settings"]["image"] = ""
            fillCreateOptions(module["settings"], module["settings"]["createOptions"])
        with open(output, "w", encoding="utf8") as fp:
            fp.write(json.dumps(j, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Compose to manifest")
    parser.add_argument("-t", "--type", type=str, help="Convert single file or project", required=True)
    parser.add_argument("-i", "--input", type=str, help="Input compose file path", required=True)
    parser.add_argument("-o", "--output", type=str, help="Output compose file path or project ", required=True)
    parser.add_argument("-r", "--registry", type=str, help="Container registry address", required=False)
    args = parser.parse_args()
    if not args.registry:
        # set default registry
        args.registry = "localhost:5000"
    convert(args.type, args.input, args.output, args.registry)


if __name__ == "__main__":
    main()
