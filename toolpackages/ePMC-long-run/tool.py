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
    return "ePMC"

def is_benchmark_supported(benchmark : Benchmark):
    """returns True if the provided benchmark is supported by the tool and if the given benchmark should appear on the generated benchmark list"""

    # list of input models ePMC does not support
    if benchmark.is_pta():
        # PTAs are not supported by ePMC
        return False
    if benchmark.is_ma():
        # MAs are not supported by ePMC
        return False
#    if benchmark.get_short_property_type() == "S":
#        # Steady state properties are not supported by ePMC
#        return False
    if benchmark.is_prism_inf():
        # CTMCs with infinite state-spaces are not supported by ePMC
        return False

    # list of properties ePMC supports : unbounded and time-bounded probabilistic reachability; steady-state probability
    if (not benchmark.is_unbounded_probabilistic_reachability()) and (not benchmark.is_time_bounded_probabilistic_reachability()) and (not benchmark.is_steady_state_probability()) and (not benchmark.is_steady_state_reward()) and (not benchmark.is_unbounded_expected_reward()):
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
    epsilon = "1e-3"
    if benchmark.is_prism():
        # set parameters
        # --graphsolver-iterative-tolerance 1e-4 since the maximal difference is 1e-4
        benchmark_settings = "--model-input-files {} --model-input-type prism --property-input-files {} --property-input-names {} --translate-messages false --value-floating-point-output-native true --graphsolver-iterative-stop-criterion relative --graphsolver-iterative-tolerance {}".format(benchmark.get_prism_program_filename(), benchmark.get_prism_property_filename(), benchmark.get_property_name(), epsilon)
    else:
        # put properties in saparate files 
        benchmark_settings = "--model-input-files {} --model-input-type jani --property-input-names {} --translate-messages false --value-floating-point-output-native true --graphsolver-iterative-stop-criterion relative --graphsolver-iterative-tolerance {}".format(benchmark.get_janifilename(), benchmark.get_property_name(), epsilon)
    if benchmark.get_open_parameter_def_string() != "":
        benchmark_settings += " --const {}".format(benchmark.get_open_parameter_def_string())

    memsize = "10240m"
    invocations = []

    # default settings
    default_inv = Invocation()
    default_inv.identifier = "default"
    default_inv.track_id = "often-epsilon-correct"
    if len(preprocessing_steps) != 0:
        for prep in preprocessing_steps:
            default_inv.add_command(prep)
    default_inv.add_command("java -Xms{} -Xmx{} -jar ./epmc-standard.jar check {}".format(memsize, memsize, benchmark_settings))
    invocations.append(default_inv)

    #if (benchmark.is_ctmc() or benchmark.is_dtmc()):
        #for tId in ["floating-point-correct", "epsilon-correct", "often-epsilon-correct"]:
            ## specific settings                     !!!!only information about model type, property type and state space size via benchmark.get_num_states_tweak() may be used for tweaking
            #specific_inv = Invocation()
            #specific_inv.identifier = "specific"
            #specific_inv.track_id = tId
            #if len(preprocessing_steps) != 0:
                #for prep in preprocessing_steps:
                    #specific_inv.add_command(prep)
            #if tId == "floating-point-correct":
                #epsilon = "1e-14"
            #if tId == "epsilon-correct":
                #epsilon = "1e-6"
            #if tId == "often-epsilon-correct":
                #epsilon = "1e-3"
            #specific_inv.add_command("java -Xms{} -Xmx{} -jar ./epmc-qcomp.jar check {} --graph-solver-stopping-criterion relative --graphsolver-iterative-tolerance {} --engine on-the-fly-eliminator".format(memsize, memsize, benchmark_settings, epsilon))
            #invocations.append(specific_inv)

    #### TODO: add default and specific invocations for other track_ids 'correct', 'floating-point-correct', 'probably-epsilon-correct', 'often-epsilon-correct', 'often-epsilon-correct-10-min'
    ### remember that different tracks have different precisions

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
    pos = log.find("command-check-result-is ")
    if pos < 0:
        return None
    pos += len("command-check-result-is ");
    eol_pos = log.find("\n", pos)
    space_pos = log.find(" ", pos)
    if (eol_pos < space_pos):
        return log[pos:eol_pos].rstrip()
    else:
        return log[pos:space_pos].rstrip()
