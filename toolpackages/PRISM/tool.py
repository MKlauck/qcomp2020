from benchmark import Benchmark
from invocation import Invocation
from execution import Execution
from utility import *
from shutil import copyfile
import sys, importlib
import tmptool
import re

#
# Tooling for PRISM
#

# configuration
prism_bin = './fix-syntax ./prism'
prism_mem_args = '-javamaxmem 11g -cuddmaxmem 4g'

# instance specific settings

specific_settings = {}

def get_specific_setting(benchmark: Benchmark):
    """ returns the instance specific settings that were configured"""
    id = benchmark.get_identifier()
    if id not in specific_settings:
        return ''
    return specific_settings[id][0]

loaded = False
def assert_loaded():
    if not loaded:
        copyfile("tool.py", os.path.join(sys.path[0], "tmptool.py"))
        importlib.reload(sys.modules["tmptool"])

def get_name():
    """ should return the name of the tool as listed on http://qcomp.org/competition/2020/"""
    return "PRISM"

def is_benchmark_supported(benchmark : Benchmark):
    """returns True if the provided benchmark is supported by the tool and if the given benchmark should appear on the generated benchmark list"""

    # Check for unsupported input languages: everything but PRISM currently
    if benchmark.is_prism():
        # Temporarily disable pacman - very slow
#         if benchmark.get_model_short_name() == "pacman":
#             return False
        # Check for unsupported property types: just reward bounded currently
        if benchmark.is_reward_bounded_probabilistic_reachability() or benchmark.is_reward_bounded_expected_reward():
            return False
#        print("{},{},{},{}".format(benchmark.get_identifier(),benchmark.get_model_type(),benchmark.get_property_type(),benchmark.get_max_num_states()))
        return True
    else:
        return False

def get_prism_invocation_model_prop_instance(benchmark : Benchmark):
    args = "{} {} --property {}".format(benchmark.get_prism_program_filename(), benchmark.get_prism_property_filename(), benchmark.get_property_name())
    if benchmark.get_open_parameter_def_string() != "":
        args += " -const {}".format(benchmark.get_open_parameter_def_string())
    return args

def get_invocations(benchmark : Benchmark):
    """
    Returns a list of invocations that invoke the tool for the given benchmark.
    It can be assumed that the current directory is the directory from which execute_invocations.py is executed.
    For QCOMP 2020, this should return a list of invocations for all tracks in which the tool can take part. For each track an invocation with default settings has to be provided and in addition, an optimized setting (e.g., the fastest engine and/or solution technique for this benchmark) can be specified. Only information about the model type, the property type and the state space size are allowed to be used to tweak the parameters.
   
    If this benchmark is not supported, an empty list has to be returned.
    """

    if not is_benchmark_supported(benchmark):
        return []

    # Gather options that are needed for this particular benchmark for any invocation of PRISM
    benchmark_instance = get_prism_invocation_model_prop_instance(benchmark);
    
    invocations = []

    basic_args = "{}".format(prism_mem_args);

    # epsilon-correct (all models but PTAs), default settings
    if (benchmark.get_model_type() != "pta"):
        # Use interval iteration generally (or uniformisation for time-bounded CTMCs)
        default_args = "-ii"
        # Choose engine heuristically
        default_args += " -heuristic speed"
        # Required precision (default anyway)
        default_args += " -e 1e-6"
        # Usual II settings when there is plenty of memory
        default_args += " -ddextraactionvars 100"
        # Increase maxiters (since QComp has a timeout anyway)
        default_args += " -maxiters 1000000"
        default_inv = Invocation()
        default_inv.identifier = "default"
        default_inv.track_id = "epsilon-correct"
        default_inv.add_command(prism_bin + " " + basic_args + " " +  default_args + " " +  benchmark_instance)
        invocations.append(default_inv)

    # epsilon-correct (all models but PTAs), specific settings
    if (benchmark.get_model_type() != "pta"):
        # Choose method/engine
        # Use interval iteration generally (or uniformisation for time-bounded CTMCs)
        if benchmark.get_model_short_name() == "haddad-monmege":
            specific_args = "-exact"
        elif (benchmark.get_num_states_tweak() == None or benchmark.get_num_states_tweak() >= 20000000):
            specific_args = "-ii -mtbdd"
        else:
            specific_args = "-ii -heuristic speed"
        # Required precision (default anyway)
        specific_args += " -e 1e-6"
        # Usual II settings when there is plenty of memory
        specific_args += " -ddextraactionvars 100"
        # Increase maxiters (since QComp has a timeout anyway)
        specific_args += " -maxiters 1000000"
        specific_inv = Invocation()
        specific_inv.identifier = "specific"
        specific_inv.track_id = "epsilon-correct"
        specific_inv.add_command(prism_bin + " " + basic_args + " " +  specific_args + " " +  benchmark_instance)
        invocations.append(specific_inv)
    
    # often-epsilon-correct (all models), default settings
    if (True):
        # Choose engine heuristically
        default_args = "-heuristic speed"
        # Required precision (just use default 1e-6, as agreed for QComp'19)
        default_args += " -e 1e-6"
        # Increase maxiters (since QComp has a timeout anyway)
        default_args += " -maxiters 1000000"
        default_inv = Invocation()
        default_inv.identifier = "default"
        default_inv.track_id = "often-epsilon-correct"
        default_inv.add_command(prism_bin + " " + basic_args + " " +  default_args + " " +  benchmark_instance)
        invocations.append(default_inv)
        
    # often-epsilon-correct (all models), specific settings
    if (True):
        # Choose method/engine
        if benchmark.get_model_short_name() == "haddad-monmege":
            specific_args = "-exact"
        elif (benchmark.get_num_states_tweak() == None or benchmark.get_num_states_tweak() >= 20000000):
            specific_args = "-mtbdd"
        else:
            specific_args = "-heuristic speed"
        # Required precision (just use default 1e-6, as agreed for QComp'19)
        specific_args += " -e 1e-6"
        # Increase maxiters (since QComp has a timeout anyway)
        specific_args += " -maxiters 1000000"
        specific_inv = Invocation()
        specific_inv.identifier = "specific"
        specific_inv.track_id = "often-epsilon-correct"
        specific_inv.add_command(prism_bin + " " + basic_args + " " +  specific_args + " " +  benchmark_instance)
        invocations.append(specific_inv)
        
    # probably-epsilon-correct (all models but PTAs), default settings
    if (benchmark.get_model_type() != "pta"):
        # Use interval iteration generally (or uniformisation for time-bounded CTMCs)
        if (benchmark.get_model_type() == "ctmc" and benchmark.is_time_bounded_probabilistic_reachability()):
            default_args = ""
        else:
            default_args = "-ii -e 5e-2"
        # Choose engine heuristically
        default_args += " -heuristic speed"
        # Usual II settings when there is plenty of memory
        default_args += " -ddextraactionvars 100"
        # Increase maxiters (since QComp has a timeout anyway)
        default_args += " -maxiters 1000000"
        default_inv = Invocation()
        default_inv.identifier = "default"
        default_inv.track_id = "probably-epsilon-correct"
        default_inv.add_command(prism_bin + " " + basic_args + " " +  default_args + " " +  benchmark_instance)
        invocations.append(default_inv)

    # probably-epsilon-correct (all models but PTAs), specific settings
    if (benchmark.get_model_type() != "pta"):
        # Choose method/engine
        # Use interval iteration generally (or uniformisation for time-bounded CTMCs)
        if benchmark.get_model_short_name() == "haddad-monmege":
            specific_args = "-exact"
        elif (benchmark.get_model_type() == "ctmc" and benchmark.is_time_bounded_probabilistic_reachability()):
            specific_args = ""
        elif (benchmark.get_num_states_tweak() == None or benchmark.get_num_states_tweak() >= 20000000):
            specific_args = "-ii -e 5e-2 -mtbdd"
        else:
            specific_args = "-ii -e 5e-2 -heuristic speed"
        # Usual II settings when there is plenty of memory
        specific_args += " -ddextraactionvars 100"
        # Increase maxiters (since QComp has a timeout anyway)
        specific_args += " -maxiters 1000000"
        specific_inv = Invocation()
        specific_inv.identifier = "specific"
        specific_inv.track_id = "probably-epsilon-correct"
        specific_inv.add_command(prism_bin + " " + basic_args + " " +  specific_args + " " +  benchmark_instance)
        invocations.append(specific_inv)
    
    return invocations

def grep_for_result(benchmark : Benchmark, log) :
    # match 'Result: x (...)' and 'Result (...): x (...)' style results
    m = re.search('^Result.*: ([^( \n]+)', log, re.MULTILINE)
    if m is None:
        return m
    return m.group(1)

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
    return grep_for_result(benchmark, log)
