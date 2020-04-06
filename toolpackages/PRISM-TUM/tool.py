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
    return "PRISM-TUM"

def is_benchmark_supported(benchmark : Benchmark):
    """returns True if the provided benchmark is supported by the tool and if the given benchmark should appear on the generated benchmark list"""
    if not benchmark.is_prism() or benchmark.is_prism_inf():
        return False
    if benchmark.get_model_type() not in {"ctmc", "dtmc", "mdp"}:
        return False
    if benchmark.get_property_type() not in {"prob-reach", "prob-reach-step-bounded"}:
        return False
    if benchmark.is_ctmc() and benchmark.get_property_type() == "prob-reach-step-bounded":
        return False
    return True

def is_on_benchmark_list(benchmark : Benchmark):
    """ Returns true, if the given benchmark should appear on the generated benchmark list."""
    return is_benchmark_supported(benchmark)

def get_invocations(benchmark : Benchmark):
    """
    Returns a list of invocations that invoke the tool for the given benchmark.
    It can be assumed that the current directory is the directory from which execute_invocations.py is executed.
    For QCOMP 2020, this should return a list of invocations for all tracks in which the tool can take part. For each track an invocation with default settings has to be provided and in addition, an optimized setting (e.g., the fastest engine and/or solution technique for this benchmark) can be specified. Only information about the model type, the property type and the state space size are allowed to be used to tweak the parameters.
   
    If this benchmark is not supported, an empty list has to be returned.
    """

    if not is_benchmark_supported(benchmark):
        return []

    prec = dict()
    prec["epsilon-correct"] = "0.000001"
    prec["probably-epsilon-correct"] = "0.05"
    prec["often-epsilon-correct"] = "0.001"
    prec["often-epsilon-correct-10-min"] = "0.001"

    result = []

    for track in prec.keys():

        benchmark_settings = "./pet.sh reachability --precision {} --relative-error --only-result -m {} -p {} --property {}" \
            .format(prec[track], benchmark.get_prism_program_filename(), benchmark.get_prism_property_filename(), benchmark.get_property_name())
        if benchmark.get_open_parameter_def_string() != "":
            benchmark_settings += " --const {}".format(benchmark.get_open_parameter_def_string())
        if "haddad" in benchmark.get_prism_program_filename() or "gathering" in benchmark.get_prism_program_filename():
             benchmark_settings = "./fix-syntax " + benchmark_settings

        # default settings PET eps-corr
        default_inv = Invocation()
        default_inv.identifier = "default"
        default_inv.note = "Default settings."
        default_inv.track_id = track
        default_inv.add_command(benchmark_settings)

        result += [default_inv]
        
        if track == "epsilon-correct" or benchmark.get_model_type() == "ctmc" or "haddad" in benchmark.get_prism_program_filename() or "csma" in benchmark.get_prism_program_filename() or "wlan" in benchmark.get_prism_program_filename() or "gathering" in benchmark.get_prism_program_filename():
            #smc is prob eps correct, cannot handle ctmc and haddad monmege cannot be parsed by it
            continue
        if benchmark.get_num_states_tweak() is None:
            #need this info
            continue

        smc_settings = "./smc.sh {} {} -prop {} -heuristic RTDP_ADJ -RTDP_ADJ_OPTS 1 -colourParams S:{},Av:10,e:{},d:0.05,p:0.05,post:64" \
            .format(benchmark.get_prism_program_filename(), benchmark.get_prism_property_filename(), benchmark.get_property_name(), benchmark.get_num_states_tweak(), prec[track])
        if benchmark.get_open_parameter_def_string() != "":
            smc_settings += " -const {}".format(benchmark.get_open_parameter_def_string())
        if "haddad" in benchmark.get_prism_program_filename() or "gathering" in benchmark.get_prism_program_filename():
            smc_settings = "./fix-syntax " + smc_settings
            
        # SMC invocations
        SMC_inv = Invocation()
        SMC_inv.identifier = "specific"
        SMC_inv.note = "Statistical model checking with limited information (no transition probabilities)"
        SMC_inv.track_id = track
        SMC_inv.add_command(smc_settings)

        result += [SMC_inv]

    return result

    



def get_result(benchmark : Benchmark, execution : Execution):
    """
    Returns the result of the given execution on the given benchmark.
    This method is called after executing the commands of the associated invocation.
    One can either find the result in the tooloutput (as done here) or
    read the result from a file that the tool has produced.
    The returned value should be either 'true', 'false', or a decimal number.
    """
    invocation = execution.invocation
    log = execution.concatenate_logs()

    if "PRISM-games" in log:
        # SMC
        pos = log.find("Result (maximum probability): ")
        if pos < 0:
            pos = log.find("Result (minimum probability): ")
            if pos < 0:
                return None
        pos = pos + len("Result (---imum probability): ")
        eol_pos = log.find("\n", pos)
        return log[pos:eol_pos]
    else:
        # PET
        pos = log.find("Output:\n")
        if pos < 0:
            return None
        pos = pos + len("Output:\n")
        eol_pos = log.find("\n", pos)
        if pos == eol_pos:
            return None
        return log[pos:eol_pos]


