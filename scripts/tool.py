from benchmark import Benchmark
from invocation import Invocation
from execution import Execution
from utility import *
from shutil import copyfile
import sys, importlib
import tmptool

loaded = False
def assert_loaded():
    if not loaded:
        copyfile("tool.py", os.path.join(sys.path[0], "tmptool.py"))
        importlib.reload(sys.modules["tmptool"])

def get_name():
    """ should return the name of the tool as listed on http://qcomp.org/competition/2020/"""
    return "Storm"

def is_benchmark_supported(benchmark : Benchmark):
    """ Auxiliary function that returns True if the provided benchmark is supported by the tool"""

    if benchmark.is_pta() and benchmark.is_prism():
        # The PTAs from Prism are not supported because either
        # modest can't apply digital clocks semantic due to open constraints, or
        # modest puts branch-rewards on the models (these are not supported by Storm)
        return False
    if benchmark.is_prism_inf() and benchmark.is_ctmc():
        # Storm does not support the CTMCs with infinite state-spaces
        return False
    return True

def is_on_benchmark_list(benchmark : Benchmark):
    """ Returns true, if the given benchmark should appear on the generated benchmark list."""

    # do not include for models that storm does not support
    if not is_benchmark_supported(benchmark):
        return False

    # do not include models with small state spaces, except it's the haddad-monmege one (because we like that)
    if benchmark.get_max_num_states() is not None and benchmark.get_max_num_states() < 10000 and benchmark.get_model_short_name() != "haddad-monmege":
        return False

    # do not select dfts with a file parameter "R" that is set to true
    if benchmark.is_galileo():
        for p in benchmark.get_file_parameters():
            if p["name"] == "R" and p["value"] == True:
                return False

    return True

def get_invocations(benchmark : Benchmark):
    """
    Returns a list of invocations that invoke the tool for the given benchmark.
    It can be assumed that the current directory is the directory from which execute_invocations.py is executed.
    For QCOMP 2020, this should return a list of invocations for all tracks in which the tool can take part. For each track an invocation with default settings has to be provided and in addition, an optimized setting (e.g., the fastest engine and/or solution technique for this benchmark) can be specified. Only information about the model type, the property type and the state space size are allowed to be used to tweak the parameters.
   
    If this benchmark is not supported, an empty list has to be returned.
    """

    if not is_benchmark_supported(benchmark):
        return []

    # Gather options that are needed for this particular benchmark for any invocation of Storm
    preprocessing_steps = []
    benchmark_settings = ""
    if benchmark.is_prism() or benchmark.is_prism_ma() and not benchmark.is_pta():
        benchmark_settings = "--prism {} --prop {} {}".format(benchmark.get_prism_program_filename(), benchmark.get_prism_property_filename(), benchmark.get_property_name())
        if benchmark.get_open_parameter_def_string() != "":
            benchmark_settings += " --constants {}".format(benchmark.get_open_parameter_def_string())
        if benchmark.is_ctmc():
            benchmark_settings += " --prismcompat"
    else:
        # For jani input, it might be the case that preprocessing is necessary using moconv
        moconv_options = []
        features = benchmark.get_jani_features()
        for f in ["arrays", "derived-operators", "functions", "state-exit-rewards"]:
            if f in features: features.remove(f)
        if "nondet-selection" in features:
            moconv_options.append("--remove-disc-nondet")
            features.remove("nondet-selection")
        if len(features) != 0:
            print("Unsupported jani feature(s): {}".format(features))
        if benchmark.is_pta():
            moconv_options.append("--digital-clocks")

        if len(moconv_options) != 0:
            preprocessing_steps.append("mono /modest/moconv.exe {} {} --output {} --overwrite".format(benchmark.get_janifilename(), " ".join(moconv_options), "converted_" + benchmark.get_janifilename()))
            if benchmark.get_open_parameter_def_string() != "":
                preprocessing_steps[-1] += " --experiment {}".format(benchmark.get_open_parameter_def_string())
            benchmark_settings = "--jani {} --janiproperty {}".format("converted_" + benchmark.get_janifilename(), benchmark.get_property_name())
        else:
            benchmark_settings = "--jani {} --janiproperty {}".format(benchmark.get_janifilename(), benchmark.get_property_name())
            if benchmark.get_open_parameter_def_string() != "":
                benchmark_settings += " --constants {}".format(benchmark.get_open_parameter_def_string())

    invocations = []


    # default settings
    default_inv = Invocation()
    default_inv.identifier = "default"
    default_inv.track_id = "epsilon-correct"
    if len(preprocessing_steps) != 0:
        for prep in preprocessing_steps:
            default_inv.add_command(prep)
    default_inv.add_command("./storm {}".format(benchmark_settings))
    invocations.append(default_inv)

    # specific settings                     !!!!only information about model type, property type and state space size may be used for tweaking
    specific_inv = Invocation()
    specific_inv.identifier = "specific"
    specific_inv.track_id = "epsilon-correct"
    if len(preprocessing_steps) != 0:
        for prep in preprocessing_steps:
            specific_inv.add_command(prep)
    specific_inv.add_command("~/storm/build/bin/storm {} --engine hybrid".format(benchmark_settings))
    invocations.append(specific_inv)

    ####TODO: add default and specific invocations for other track_ids 'correct', 'probably-epsilon-correct', 'often-epsilon-correct', 'often-epsilon-correct-10-min'

    return invocations


def get_result(benchmark : Benchmark, execution : Execution):
    """
    Returns the result of the given execution on the given benchmark.
    This method is called after executing the commands of the associated invocation.
    One can either find the result in the tooloutput (as done here) or
    read the result from a file that the tool has produced.
    The returned value should be either 'true', 'false', a decimal number, or a fraction.
    """
    invocation = execution.invocation
    log = execution.concatenate_logs()
    pos = log.find("Model checking property \"{}\":".format(benchmark.get_property_name()))
    if pos < 0:
        return None
    pos = log.find("Result (for initial states): ", pos)
    if pos < 0:
        return None
    pos = pos + len("Result (for initial states): ")
    eol_pos = log.find("\n", pos)
    return log[pos:eol_pos]