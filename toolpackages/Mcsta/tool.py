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
	return "mcsta"

def is_benchmark_supported(benchmark : Benchmark):
	"""returns True if the provided benchmark is supported by the tool and if the given benchmark should appear on the generated benchmark list"""
	
	short = benchmark.get_model_short_name()
	prop = benchmark.get_property_name()
	if(short == "bluetooth" # multiple initial states
		or short == "cluster" and prop == "below_min"            # bounded expected-reward property
		or short == "herman"                                     # multiple initial states
		or short == "kanban" and prop == "throughput"            # something's wrong with our algorithm here, didn't manage to investigate before deadline, hope to fix for second round
		or short == "mapk_cascade" and prop == "reactions"       # bounded expected-reward property
		or short == "oscillators"                                # model file too large, cannot be parsed
		or short == "repudiation_malicious"                      # open clock constraints
		or short == "resource-gathering" and prop == "expgold"   # bounded expected-reward property
		or short == "resource-gathering" and prop == "prgoldgem" # unsupported property
		or short == "sms" and prop == "Unavailability"           # Zeno MA model: not supported for long-run average rewards
		):
		return False
	
	return True

def add_invocations(invocations, track_id, default_cmd, specific_cmd):
	default_inv = Invocation()
	default_inv.identifier = "default"
	default_inv.track_id = track_id
	default_inv.add_command(default_cmd)
	invocations.append(default_inv)
	specific_inv = Invocation()
	specific_inv.identifier = "specific"
	specific_inv.track_id = track_id
	specific_inv.add_command(specific_cmd)
	invocations.append(specific_inv)

# Run with python3 qcomp2020_generate_invocations.py
def get_invocations(benchmark : Benchmark):
	"""
	Returns a list of invocations that invoke the tool for the given benchmark.
	It can be assumed that the current directory is the directory from which execute_invocations.py is executed.
	For QCOMP 2020, this should return a list of invocations for all tracks in which the tool can take part. For each track an invocation with default settings has to be provided and in addition, an optimized setting (e.g., the fastest engine and/or solution technique for this benchmark) can be specified. Only information about the model type, the property type and the state space size are allowed to be used to tweak the parameters.
   
	If this benchmark is not supported, an empty list has to be returned.
	"""

	if not is_benchmark_supported(benchmark):
		return []
	short = benchmark.get_model_short_name()
	prop = benchmark.get_property_name()
	prop_type = benchmark.get_short_property_type()
	params = benchmark.get_parameter_values_string()
	instance = short + "." + params
	size = benchmark.get_num_states_tweak()

	invocations = []

	benchmark_settings = "--props " + benchmark.get_property_name()
	if benchmark.get_open_parameter_def_string() != "":
		benchmark_settings += " -E " + benchmark.get_open_parameter_def_string()

	default_base = "mcsta/modest mcsta " + benchmark.get_janifilename() + " " + benchmark_settings + " -O out.txt Minimal"
	specific_base = default_base + " --unsafe" # specific settings: only information about model type, property type and state space size via benchmark.get_num_states_tweak() may be used for tweaking

	#
	# Track "floating-point-correct"
	#
	precision = "0"
	default_cmd  = default_base  + " --no-partial-results --epsilon 0 --absolute-epsilon"
	specific_cmd = specific_base + " --no-partial-results --epsilon 0 --absolute-epsilon"
	if prop_type == "S" or (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		return []
	if prop_type == "P":
		default_cmd +=  " --p0 --p1"
		specific_cmd += " --p0 --p1"
	elif prop_type == "Pb":
		default_cmd +=  " --p0"
		specific_cmd += " --p0"
	if (size is None or size >= 100000000) and not benchmark.is_pta():
		specific_cmd += " -S Disk --store-compress None"
	elif benchmark.is_pta() or size < 50000000: # OOM with -S Memory:  "beb.5-16-15", "coupon.15-4-5", "egl", "exploding-blocksworld", "triangle-tireworld", "philosophers.20-1", "pnueli-zuck.10", "rabin", "tireworld", "ftpp", "hecs.3-2" # OOM with -S Memory
		specific_cmd += " -S Memory"
	else:
		specific_cmd += " --store-compress None"
	add_invocations(invocations, "floating-point-correct", default_cmd, specific_cmd)

	#
	# Track "epsilon-correct"
	#
	precision = "1e-6"
	default_cmd  = default_base  + " --no-partial-results --width $PRECISION --relative-width"
	specific_cmd = specific_base + " --no-partial-results --width $PRECISION --relative-width"
	if prop_type == "S":
		# long-run average: default is the sound algorithm based on value iteration, nothing to configure
		pass
	elif (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		# time-bounded probability for CTMC and MA: default is sound Unif+, nothing to configure
		pass
	elif prop_type == "Pb":
		# reward-bounded probability: default is unsound VI, so need to change to II (SVI and OVI not yet implemented for this case)
		default_cmd  += " --alg IntervalIteration"
		specific_cmd += " --alg IntervalIteration"
	else:
		# unbounded probability or expected reward: default is unsound VI, so need to change to OVI
		default_cmd  += " --alg OptimisticValueIteration --epsilon $PRECISION"
		specific_cmd += " --alg OptimisticValueIteration --epsilon $PRECISION"
		if prop_type == "P" and benchmark.is_dtmc() or benchmark.is_ctmc():
			# tweaking for unbounded probabilities on DTMC and CTMC: use 0/1 preprocessing
			specific_cmd += " --p0 --p1"
	if (size is None or size >= 100000000) and not benchmark.is_pta():
		specific_cmd += " -S Disk --store-compress None"
	elif benchmark.is_pta() or size < 50000000: # OOM with -S Memory:  "beb.5-16-15", "coupon.15-4-5", "egl", "exploding-blocksworld", "triangle-tireworld", "philosophers.20-1", "pnueli-zuck.10", "rabin", "tireworld", "ftpp", "hecs.3-2" # OOM with -S Memory
		specific_cmd += " -S Memory"
	else:
		specific_cmd += " --store-compress None"
	add_invocations(invocations, "epsilon-correct", default_cmd.replace("$PRECISION", precision), specific_cmd.replace("$PRECISION", precision))

	#
	# Track "probably-epsilon-correct"
	#
	precision = "5e-2"
	add_invocations(invocations, "probably-epsilon-correct", default_cmd.replace("$PRECISION", precision), specific_cmd.replace("$PRECISION", precision))

	#
	# Track "often-epsilon-correct"
	#
	precision = "1e-3"
	default_cmd  = default_base  + " --no-partial-results --width $PRECISION --relative-width"
	specific_cmd = specific_base + " --no-partial-results --width $PRECISION --relative-width"
	if prop_type == "P" and benchmark.is_dtmc() or benchmark.is_ctmc():
		# tweaking for unbounded probabilities on DTMC and CTMC: use 0/1 preprocessing
		specific_cmd += " --p0 --p1"
	if (size is None or size >= 100000000) and not benchmark.is_pta():
		specific_cmd += " -S Disk --store-compress None"
	elif benchmark.is_pta() or size < 50000000: # OOM with -S Memory:  "beb.5-16-15", "coupon.15-4-5", "egl", "exploding-blocksworld", "triangle-tireworld", "philosophers.20-1", "pnueli-zuck.10", "rabin", "tireworld", "ftpp", "hecs.3-2" # OOM with -S Memory
		specific_cmd += " -S Memory"
	else:
		specific_cmd += " --store-compress None"
	add_invocations(invocations, "often-epsilon-correct", default_cmd.replace("$PRECISION", precision), specific_cmd.replace("$PRECISION", precision))

	#
	# Track "often-epsilon-correct-10-min"
	#
	precision = "0" # so we just run for the full 10 minutes (or until we get an exact result)
	default_cmd  = default_base
	specific_cmd = specific_base
	if prop_type == "S":
		return []
	elif (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		default_cmd += " --width 0"
		specific_cmd += " --width 0"
	else:
		default_cmd += " --epsilon 0"
		specific_cmd += " --epsilon 0"
	if prop_type == "P" and benchmark.is_dtmc() or benchmark.is_ctmc():
		# tweaking for unbounded probabilities on DTMC and CTMC: use 0/1 preprocessing
		specific_cmd += " --p0 --p1"
	if (size is None or size >= 100000000) and not benchmark.is_pta():
		specific_cmd += " -S Disk --store-compress None"
	elif benchmark.is_pta() or size < 50000000: # OOM with -S Memory:  "beb.5-16-15", "coupon.15-4-5", "egl", "exploding-blocksworld", "triangle-tireworld", "philosophers.20-1", "pnueli-zuck.10", "rabin", "tireworld", "ftpp", "hecs.3-2" # OOM with -S Memory
		specific_cmd += " -S Memory"
	else:
		specific_cmd += " --store-compress None"
	add_invocations(invocations, "often-epsilon-correct-10-min", default_cmd, specific_cmd)
	
	#
	# Done
	#
	return invocations


def get_result(benchmark : Benchmark, execution : Execution):
	"""
	Returns the result of the given execution on the given benchmark.
	This method is called after executing the commands of the associated invocation.
	One can either find the result in the tooloutput (as done here) or
	read the result from a file that the tool has produced.
	The returned value should be either 'true', 'false', a decimal number, or a fraction.
	"""
	if not os.path.exists("out.txt"):
		return None
	with open("out.txt", "r") as out_file:
		log = out_file.read()
	pos = log.find("\": ")
	if pos < 0:
		return None
	pos = pos + len("\": ")
	eol_pos = log.find("\n", pos)
	result = log[pos:eol_pos]
	#if(result == "Tru"):
	#	return "True"
	#elif(result == "Fals"):
	#	return "False"
	#else:
	#	return result
	return result
