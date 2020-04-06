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

def is_benchmark_supported(benchmark : Benchmark, trackId):
    """returns True if the provided benchmark is supported by the tool and if the given benchmark should appear on the generated benchmark list"""

    if benchmark.is_pta() and benchmark.is_prism():
        # Some PTAs from Prism are not supported because either
        # modest can't apply digital clocks semantic due to open constraints, or
        # modest puts the time as branch-rewards on the models, which are not supported for time-bounded properties
        if benchmark.get_model_short_name() in ["firewire-pta", "zeroconf-pta"]:
            return "time-bounded" not in benchmark.get_property_type()
        else:
            return False
    if benchmark.is_prism_inf() and benchmark.is_ctmc():
        # Storm does not support the CTMCs with infinite state-spaces
        return False

    # Time bounded queries on continuous time models can not be solved exactly
    if trackId in ["correct", "floating-point-correct"]:
        if "time-bounded" in benchmark.get_property_type() and (benchmark.is_ma() or benchmark.is_ctmc()):
            return False
    return True


def get_invocations(benchmark : Benchmark):
    """
    Returns a list of invocations that invoke the tool for the given benchmark.
    It can be assumed that the current directory is the directory from which execute_invocations.py is executed.
    For QCOMP 2020, this should return a list of invocations for all tracks in which the tool can take part. For each track an invocation with default settings has to be provided and in addition, an optimized setting (e.g., the fastest engine and/or solution technique for this benchmark) can be specified. Only information about the model type, the property type and the state space size are allowed to be used to tweak the parameters.
   
    If this benchmark is not supported, an empty list has to be returned.
    """
    # decide whether we want to use storm-dft (which supports galileo fault trees without repair)
    use_storm_dft = False
    if benchmark.is_galileo():
       has_repair  = False
       for p in benchmark.get_file_parameters():
           if p["name"] == "R" and p["value"] == True:
               has_repair = True
       if not has_repair: 
           use_storm_dft = True
           
    # Gather the precision settings for the corresponding track
    track_settings = dict()
    track_comments = dict()
    track_settings['correct'] = ' --exact '
    track_comments['correct'] = 'Use exact arithmethic with rationals.'
    track_settings['floating-point-correct'] = ' --exact floats --general:precision 1e-20 '
    track_comments['floating-point-correct'] = 'Use exact arithmethic with floats. The precision needs to be set to increase precision when printing the result to stdout '
    track_settings['epsilon-correct'] = ' --sound --precision 1e-6 '
    track_comments['epsilon-correct'] = 'Use sound model checking methods.'
    track_settings['probably-epsilon-correct'] = ' --sound --precision 5e-2 '
    track_comments['probably-epsilon-correct'] = 'Use sound model checking.'
    track_settings['often-epsilon-correct'] = ' --timebounded:precision 1e-3 '
    track_comments['often-epsilon-correct'] = 'Use potentially unsound but fast solution methods. Use default precision (1e-6) everywhere except for timebounded queries, for which solution methods give epsilon guarantees.' 
    track_settings['often-epsilon-correct-10-min'] = ' --signal-timeout 60 --general:precision 1e-12 --gmm++:precision 1e-12 --native:precision 1e-12 --minmax:precision 1e-12 --timebounded:precision 1e-6 ' + ("" if use_storm_dft else "--lra:precision 1e-12 ")
    track_comments['often-epsilon-correct-10-min'] = 'Only force termination 60 seconds after receiving SIGTERM. Use potentially unsound but fast solution methods. Take a high precision to make sure that we make use of the 10 minutes. Time bounded queries can not be answered that precisely due to numerics.'
    
    
    invocations = []
    
    for trackId in track_settings:
                
        if not is_benchmark_supported(benchmark, trackId):
            continue
        # Check whether this is a job for storm-dft
        if use_storm_dft:        
            # We now have to obtain the correct property.
            # Unfortunately, this is necessary because the gallileo files do not contain any information of the property
            # The code below might easily break if we pick a different benchmark set
            benchmark_settings = "--dftfile {} ".format(benchmark.get_galileo_filename())
            if benchmark.is_time_bounded_probabilistic_reachability():
                time_bound = 1
                for p in benchmark.get_parameters():
                    if p["name"] == "TIME_BOUND":
                        time_bound = p["value"]
                benchmark_settings += "--timebound {} --max".format(time_bound)
            elif benchmark.is_unbounded_expected_time():
                benchmark_settings += "--expectedtime --min"

            benchmark_settings += track_settings[trackId]
            default_inv = Invocation()
            default_inv.track_id = trackId
            default_inv.identifier = "default"
            default_inv.note = "Use Storm-dft with the requested property. " + track_comments[trackId]
            default_inv.add_command("~/storm/build/bin/storm-dft {}".format(benchmark_settings))
            invocations.append(default_inv)
            continue # with next trackId

        # Gather options that are needed for this particular benchmark for any invocation of Storm
        preprocessing_steps = []
        benchmark_settings = ""
        if (benchmark.is_prism() or benchmark.is_prism_ma()) and not benchmark.is_pta():
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
                if benchmark.get_model_short_name() == "wlan-large":
                    # This is actually a stochastic timed automaton. Distributions have to be unrolled first
                    moconv_options.append(" --unroll-distrs")
            if len(moconv_options) != 0:
                preprocessing_steps.append("~/modest/modest convert {} {} --output {} --overwrite".format(benchmark.get_janifilename(), " ".join(moconv_options), "converted_" + benchmark.get_janifilename()))
                if benchmark.get_open_parameter_def_string() != "":
                    preprocessing_steps[-1] += " --experiment {}".format(benchmark.get_open_parameter_def_string())
                benchmark_settings = "--jani {} --janiproperty {}".format("converted_" + benchmark.get_janifilename(), benchmark.get_property_name())
            else:
                benchmark_settings = "--jani {} --janiproperty {}".format(benchmark.get_janifilename(), benchmark.get_property_name())
                if benchmark.get_open_parameter_def_string() != "":
                    benchmark_settings += " --constants {}".format(benchmark.get_open_parameter_def_string())

        benchmark_settings += track_settings[trackId]
        benchmark_settings += " --engine portfolio --ddlib sylvan --sylvan:maxmem 6114 --sylvan:threads 4"
        benchmark_comment = "Use Storm with protfolio engine. Use sylvan as library for Dds, restricted to 6GB memory and 4 threads. " + track_comments[trackId]
        # default settings
        default_inv = Invocation()
        default_inv.identifier = "default"
        # Apparently, a note is not needed
        # default_inv.note = benchmark_comment
        default_inv.track_id = trackId
        for prep in preprocessing_steps:
            default_inv.add_command(prep)
        default_inv.add_command("~/storm/build/bin/storm {}".format(benchmark_settings))
        invocations.append(default_inv)

        # specific settings                     !!!!only information about model type, property type and state space size via benchmark.get_num_states_tweak() may be used for tweaking
        # Omitted because there is no significant benefit
        # if benchmark.get_num_states_tweak() is not None:
        #    specific_inv = Invocation()
        #    specific_inv.identifier = "specific"
        #    specific_inv.track_id = trackId
        #    for prep in preprocessing_steps:
        #        specific_inv.add_command(prep)
        #    specific_inv.add_command("~/storm/build/bin/storm {} --hints:states {}".format(benchmark_settings, benchmark.get_num_states_tweak()))
        #    invocations.append(specific_inv)

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
    if "Storm-dft" in log:
        pos = log.find("Result: [")
        if pos >= 0:
            pos = pos + len("Result: [")
            pos_e = log.find("]\n", pos)
            if pos_e >= 0:
                return log[pos:pos_e]

    pos1 = log.find("Model checking property \"{}\":".format(benchmark.get_property_name()))
    if pos1 < 0:
        return None
    for pre_result_str in ["Result (for initial states): ", "Result till abort (for initial states): "]:
        pos2 = log.find(pre_result_str, pos1)
        if pos2 < 0: continue
        pos2 += len(pre_result_str)
        eol_pos = log.find("\n", pos2)
        result = log[pos2:eol_pos]
        pos_appr = result.find("(approx. ")
        if pos_appr >= 0:
            result = result[:pos_appr]
        return result
    return None