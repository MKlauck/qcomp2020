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
    return "Storm-static"

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
        benchmark_settings += " --ddlib sylvan --sylvan:maxmem 6114 --sylvan:threads 4"
        benchmark_comment = "Use sylvan as library for Dds, restricted to 6GB memory and 4 threads. " + track_comments[trackId]
        
        # default settings
        default_inv = Invocation()
        default_inv.identifier = "default"
        # default_inv.note = benchmark_comment
        default_inv.track_id = trackId
        for prep in preprocessing_steps:
            default_inv.add_command(prep)
        default_inv.add_command("~/storm/build/bin/storm {}".format(benchmark_settings))
        invocations.append(default_inv)

        # specific settings
        # Storm-static selects for each benchmark the best config among sparse, hybrid, ddbisim and exact (same for all tracks)
        # We obtained this via previous experiments:
        best_configs = dict()
        best_configs["beb.4-8-7.LineSeized"] = "hybrid"
        best_configs["beb.5-16-15.LineSeized"] = "N/A"
        best_configs["bitcoin-attack.20-6.P_MWinMax"] = "ddbisim"
        best_configs["bluetooth.1.time"] = "ddbisim"
        best_configs["cabinets.3-2-true.Unavailability"] = "sparse"
        best_configs["cabinets.3-2-true.Unreliability"] = "ddbisim"
        best_configs["cluster.128-2000-20.premium_steady"] = "sparse"
        best_configs["cluster.128-2000-20.qos1"] = "hybrid"
        best_configs["cluster.64-2000-20.below_min"] = "hybrid"
        best_configs["consensus.4-4.disagree"] = "sparse"
        best_configs["consensus.4-4.steps_min"] = "sparse"
        best_configs["consensus.6-2.disagree"] = "ddbisim"
        best_configs["consensus.6-2.steps_min"] = "ddbisim"
        best_configs["coupon.15-4-5.collect_all_bounded"] = "ddbisim"
        best_configs["coupon.15-4-5.exp_draws"] = "ddbisim"
        best_configs["coupon.9-4-5.collect_all_bounded"] = "ddbisim"
        best_configs["coupon.9-4-5.exp_draws"] = "ddbisim"
        best_configs["crowds.5-20.positive"] = "ddbisim"
        best_configs["crowds.6-20.positive"] = "ddbisim"
        best_configs["csma.3-4.all_before_max"] = "hybrid"
        best_configs["csma.3-4.time_max"] = "hybrid"
        best_configs["csma.4-2.all_before_max"] = "hybrid"
        best_configs["csma.4-2.time_max"] = "hybrid"
        best_configs["dpm.4-8-5.PmaxQueuesFullBound"] = "N/A"
        best_configs["dpm.6-6-5.PminQueue1Full"] = "sparse"
        best_configs["eajs.5-250-11.ExpUtil"] = "ddbisim"
        best_configs["eajs.6-300-13.ExpUtil"] = "ddbisim"
        best_configs["echoring.100.MaxOffline1"] = "sparse"
        best_configs["egl.10-2.messagesB"] = "ddbisim"
        best_configs["egl.10-2.unfairA"] = "hybrid"
        best_configs["egl.10-8.messagesB"] = "ddbisim"
        best_configs["egl.10-8.unfairA"] = "hybrid"
        best_configs["elevators.b-11-9.goal"] = "sparse"
        best_configs["embedded.8-12.actuators"] = "exact"
        best_configs["embedded.8-12.up_time"] = "exact"
        best_configs["exploding-blocksworld.10.goal"] = "N/A"
        best_configs["firewire-pta.30-5000.eventually"] = "sparse"
        best_configs["firewire.false-36-800.deadline"] = "ddbisim"
        best_configs["fms.8.productivity"] = "N/A"
        best_configs["ftpp.2-2-true.Unavailability"] = "N/A"
        best_configs["ftwc.8-5.TimeMax"] = "sparse"
        best_configs["ftwc.8-5.TimeMin"] = "sparse"
        best_configs["haddad-monmege.100-0.7.exp_steps"] = "exact"
        best_configs["haddad-monmege.100-0.7.target"] = "exact"
        best_configs["hecs.false-1-1.Unreliability"] = "sparse"
        best_configs["hecs.false-2-2.Unreliability"] = "sparse"
        best_configs["hecs.false-3-2.Unreliability"] = "N/A"
        best_configs["herman.15.steps"] = "ddbisim"
        best_configs["kanban.5.throughput"] = "hybrid"
        best_configs["majority.2100.change_state"] = "sparse"
        best_configs["mapk_cascade.4-30.activated_time"] = "sparse"
        best_configs["mapk_cascade.4-30.reactions"] = "hybrid"
        best_configs["nand.40-4.reliable"] = "hybrid"
        best_configs["nand.60-4.reliable"] = "hybrid"
        best_configs["oscillators.8-10-0.1-1-0.1-1.0.power_consumption"] = "sparse"
        best_configs["oscillators.8-10-0.1-1-0.1-1.0.time_to_synch"] = "sparse"
        best_configs["pacman.100.crash"] = "hybrid"
        best_configs["pacman.60.crash"] = "hybrid"
        best_configs["philosophers.16-1.MaxPrReachDeadlock"] = "hybrid"
        best_configs["philosophers.16-1.MaxPrReachDeadlockTB"] = "hybrid"
        best_configs["philosophers.16-1.MinExpTimeDeadlock"] = "hybrid"
        best_configs["philosophers.20-1.MaxPrReachDeadlock"] = "hybrid"
        best_configs["philosophers.20-1.MaxPrReachDeadlockTB"] = "N/A"
        best_configs["philosophers.20-1.MinExpTimeDeadlock"] = "N/A"
        best_configs["pnueli-zuck.10.live"] = "hybrid"
        best_configs["pnueli-zuck.5.live"] = "hybrid"
        best_configs["polling.18-16.s1_before_s2"] = "hybrid"
        best_configs["rabin.10.live"] = "hybrid"
        best_configs["readers-writers.40.exp_time_many_requests"] = "sparse"
        best_configs["readers-writers.40.prtb_many_requests"] = "hybrid"
        best_configs["rectangle-tireworld.11.goal"] = "exact"
        best_configs["resource-gathering.1300-100-100.expgold"] = "ddbisim"
        best_configs["resource-gathering.1300-100-100.expsteps"] = "sparse"
        best_configs["resource-gathering.1300-100-100.prgoldgem"] = "hybrid"
        best_configs["sms.3-true.Unavailability"] = "hybrid"
        best_configs["sms.3-true.Unreliability"] = "sparse"
        best_configs["speed-ind.2100.change_state"] = "sparse"
        best_configs["stream.1000.exp_buffertime"] = "sparse"
        best_configs["stream.1000.pr_underrun"] = "sparse"
        best_configs["stream.1000.pr_underrun_tb"] = "sparse"
        best_configs["tireworld.45.goal"] = "N/A"
        best_configs["triangle-tireworld.441.goal"] = "N/A"
        best_configs["vgs.5-10000.MaxPrReachFailedTB"] = "N/A"
        best_configs["vgs.5-10000.MinExpTimeFailed"] = "N/A"
        best_configs["wlan-large.2.E_or"] = "sparse"
        best_configs["wlan-large.2.P_max"] = "sparse"
        best_configs["wlan.4-0.cost_min"] = "hybrid"
        best_configs["wlan.4-0.sent"] = "hybrid"
        best_configs["wlan.5-0.cost_min"] = "hybrid"
        best_configs["wlan.5-0.sent"] = "hybrid"
        best_configs["wlan.6-0.cost_min"] = "hybrid"
        best_configs["wlan.6-0.sent"] = "hybrid"
        best_configs["zenotravel.4-2-2.goal"] = "hybrid"
        best_configs["zeroconf-pta.200.incorrect"] = "exact"
        best_configs["zeroconf.1000-8-false.correct_max"] = "sparse"
        best_configs["zeroconf.1000-8-false.correct_min"] = "sparse"
        
        try:
            config = best_configs[benchmark.get_identifier()]
        except KeyError:
            print("Unable to find best config for {}. Is this a new benchmark?".format(benchmark.get_identifier()))
            config = "N/A"
        
        
        if config in ["N/A", "sparse"]:
            # This is like the default config and thus does not need a rerun
            continue
        elif config == "hybrid":
            benchmark_settings += " --engine hybrid"
        elif config == "ddbisim":
            benchmark_settings += " --engine dd-to-sparse --bisimulation"
        elif config == "exact":
            if trackId in ["correct", "floating-point-correct"]:
                benchmark_settings += " --engine sparse"
            else:
                benchmark_settings += " --engine sparse --exact"
        else:
            assert False, "Unhandled config"
        
        specific_inv = Invocation()
        specific_inv.identifier = "specific"
        specific_inv.track_id = trackId
        for prep in preprocessing_steps:
            specific_inv.add_command(prep)
        specific_inv.add_command("~/storm/build/bin/storm {}".format(benchmark_settings))
        invocations.append(specific_inv)

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