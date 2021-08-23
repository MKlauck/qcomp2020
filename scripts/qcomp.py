import os, sys
import tool
from execute_tool import execute
from utility import Settings
from collections import OrderedDict

if __name__ == "__main__":
    # Gather tool packages
    if len(sys.argv) == 1:
        print(
            "Usage: {} path/to/first/toolpackage path/to/second/toolpackage/ path/to/third/toolpackage ...".format(
                sys.argv[0]
            )
        )
        exit(1)

    tools = OrderedDict()
    for arg in sys.argv[1:]:
        try:
            tool_package_path = os.path.expanduser(arg)
            if not os.path.isdir(tool_package_path):
                print("ERROR: Path {} does not exist".format(tool_package_path))
                raise AssertionError("Path {} does not exist".format(tool_package_path))
            tool_package_path = os.path.realpath(tool_package_path)
            settings = Settings(tool_package_path)
            if not os.path.isfile(settings.invocations_filename()):
                print(
                    "ERROR: Invocations file {} does not exist".format(
                        settings.invocations_filename()
                    )
                )
                raise AssertionError(
                    "Invocations file {} does not exist".format(
                        settings.invocations_filename()
                    )
                )
            if not os.path.isfile(settings.toolscript_filename()):
                print(
                    "ERROR: Tool script file {} does not exist".format(
                        settings.toolscript_filename()
                    )
                )
                raise AssertionError(
                    "Tool script file {} does not exist".format(
                        settings.toolscript_filename()
                    )
                )
            toolname = tool.get_name()
            if toolname in tools:
                print("ERROR: Found multiple tools with name {}".format(toolname))
                raise AssertionError(
                    "ERROR: Found multiple tools with name {}".format(toolname)
                )
            tools[toolname] = tool_package_path
            print("Found tool #{}: '{}'".format(len(tools), toolname))
        except Exception:
            input(
                "Error when checking for tool package '{}'. Press Return to continue or CTRL+C to abort.".format(
                    tool_package_path
                )
            )

    print(
        "\nSelected {} tool{}: {}".format(
            len(tools), "" if len(tools) == 1 else "s", ", ".join(tools)
        )
    )
    if len(Settings().clean_up_dirs()) > 0:
        print(
            "WARNING: This script potentially removes files in the following directories:\n\t"
            + "\n\t".join(settings.clean_up_dirs())
            + "\nThis is to perform clean-up operations after executing a tool. Make sure that these directories do not contain important data."
        )
        input("Press Return to continue or CTRL+C to abort.")

    i = 0
    for tool in tools:
        try:
            i += 1
            print(
                "\n\nExecuting benchmarks for tool {}/{}: '{}'.".format(
                    i, len(tools), tool
                )
            )
            execute(Settings(tools[tool]), False)
        except Exception:
            print("An unexpected error occurred while executing '{}'.".format(tool))
