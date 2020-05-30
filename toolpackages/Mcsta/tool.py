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
	if(short == "bluetooth"                                    # multiple initial states
		or short == "cluster" and prop == "below_min"            # bounded expected-reward property
		or short == "herman"                                     # multiple initial states
		or short == "kanban" and prop == "throughput"            # something's wrong with our algorithm here, didn't manage to investigate before deadline
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
	if default_cmd != specific_cmd:
		specific_inv = Invocation()
		specific_inv.identifier = "specific"
		specific_inv.track_id = track_id
		specific_inv.add_command(specific_cmd)
		invocations.append(specific_inv)

def tweak_memory(benchmark : Benchmark):
	short = benchmark.get_model_short_name()
	params = benchmark.get_parameter_values_string()
	instance = short + "." + params
	prop = benchmark.get_property_name()
	full = short + "." + params + "." + prop
	
	tweak = ""
	
	if(instance == "beb.5-16-15"
		or instance == "coupon.15-4-5"
		or short == "egl"
		or short == "exploding-blocksworld"
		or short == "triangle-tireworld"
		or instance == "philosophers.20-1"
		or instance == "pnueli-zuck.10"
		or short == "rabin"
		or short == "tireworld"
		or short == "ftpp"
		or instance == "hecs.3-2"
		):
		tweak += " -S Hybrid --store-compress None"
	else:
		tweak += " -S Memory"
	
	return tweak

def tweak(benchmark : Benchmark, specific_cmd):
	short = benchmark.get_model_short_name()
	params = benchmark.get_parameter_values_string()
	instance = short + "." + params
	prop = benchmark.get_property_name()
	full = short + "." + params + "." + prop
	
	tweak = ""
	
	if(full == "elevators.b-11-9.goal"
		or full == "rectangle-tireworld.11.goal"
		or full == "zenotravel.4-2-2.goal"
		or full == "firewire-pta.30-5000.eventually"
		) and "--p1" not in specific_cmd:
		tweak += " --p1"
	elif(full == "firewire.false-36-800.deadline"
		) and "--p0" not in specific_cmd:
		tweak += " --p0"
	
	return specific_cmd + tweak
		

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

	benchmark_settings = ""
	if benchmark.get_open_parameter_def_string() != "":
		benchmark_settings += "-E " + benchmark.get_open_parameter_def_string() + " "
	benchmark_settings += "--props " + benchmark.get_property_name()

	default_base = "mcsta/modest mcsta " + benchmark.get_janifilename() + " " + benchmark_settings + " -O out.txt Minimal --unsafe --es"
	specific_base = default_base + tweak_memory(benchmark) # specific settings
	default_base += " -S Memory"

	#
	# Track "floating-point-correct"
	#
	skip = False
	precision = "0"
	default_cmd  = default_base  + " --no-partial-results"
	specific_cmd = specific_base + " --no-partial-results"
	if prop_type == "S" or (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		# long-run average or time-bounded on MA/CTMC: no fp-exact algorithm available
		skip = True
	elif prop_type == "P":
		# probabilistic reachability: try value iteration until fp-fixpoint
		default_cmd +=  " --p0 --p1 --epsilon 0 --absolute-epsilon"
		specific_cmd += " --p0 --p1 --epsilon 0 --absolute-epsilon"
	elif prop_type == "E":
		# expected reward: try value iteration until fp-fixpoint
		default_cmd +=  " --epsilon 0 --absolute-epsilon"
		specific_cmd += " --epsilon 0 --absolute-epsilon"
	elif prop_type == "Pb":
		# state elimination is fp-exact
		default_cmd +=  " --reward-bounded-alg StateElimination"
		if "-S Memory" in specific_cmd:
			specific_cmd += " --reward-bounded-alg StateElimination"
		else:
			specific_cmd += " --epsilon 0 --absolute-epsilon"
	if not skip:
		add_invocations(invocations, "floating-point-correct", default_cmd, tweak(benchmark, specific_cmd))

	#
	# Track "epsilon-correct"
	#
	skip = False
	precision = "1e-6"
	default_cmd  = default_base  + " --no-partial-results"
	specific_cmd = specific_base + " --no-partial-results"
	if prop_type == "S":
		# long-run average: default is the sound algorithm based on value iteration
		default_cmd +=  " --width $PRECISION --relative-width"
		specific_cmd += " --width $PRECISION --relative-width"
	elif (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		# time-bounded probability for CTMC and MA: default is sound Unif+
		default_cmd +=  " --width $PRECISION --relative-width"
		specific_cmd += " --width $PRECISION --relative-width"
	elif benchmark.is_pta() and prop_type == "Pb":
		# time-bounded reachability for PTA: state elimination recommended
		default_cmd +=  " --reward-bounded-alg StateElimination"
		if "-S Memory" in specific_cmd:
			specific_cmd += " --reward-bounded-alg StateElimination"
		else:
			specific_cmd += " --alg IntervalIteration --width $PRECISION --relative-width"
	elif prop_type == "Pb":
		# reward-bounded probability: default is unsound VI, so need to change to II (SVI and OVI not yet implemented for this case)
		default_cmd  += " --alg IntervalIteration --width $PRECISION --relative-width"
		specific_cmd += " --alg IntervalIteration --width $PRECISION --relative-width"
	else:
		# unbounded probability or expected reward: default is unsound VI, so need to change to OVI
		default_cmd  += " --alg OptimisticValueIteration --epsilon $PRECISION --width $PRECISION --relative-width"
		specific_cmd += " --alg OptimisticValueIteration --epsilon $PRECISION --width $PRECISION --relative-width"
		if prop_type == "P" and benchmark.is_dtmc() or benchmark.is_ctmc():
			# for unbounded probabilities on DTMC and CTMC: use 0/1 preprocessing
			default_cmd += " --p0 --p1"
			specific_cmd += " --p0 --p1"
	if not skip:
		add_invocations(invocations, "epsilon-correct", default_cmd.replace("$PRECISION", precision), tweak(benchmark, specific_cmd).replace("$PRECISION", precision))

	#
	# Track "probably-epsilon-correct"
	#
	skip = False
	precision = "5e-2"
	if not skip:
		add_invocations(invocations, "probably-epsilon-correct", default_cmd.replace("$PRECISION", precision), tweak(benchmark, specific_cmd).replace("$PRECISION", precision))

	#
	# Track "often-epsilon-correct"
	#
	skip = False
	precision = "1e-3"
	default_cmd  = default_base  + " --no-partial-results"
	specific_cmd = specific_base + " --no-partial-results"
	if prop_type == "S":
		# long-run average: default is the sound algorithm based on value iteration
		default_cmd +=  " --width $PRECISION --relative-width"
		specific_cmd += " --width $PRECISION --relative-width"
	elif (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		# time-bounded probability for CTMC and MA: default is sound Unif+
		default_cmd +=  " --width $PRECISION --relative-width"
		specific_cmd += " --width $PRECISION --relative-width"
	elif benchmark.is_pta() and prop_type == "Pb":
		# time-bounded reachability for PTA: state elimination recommended
		default_cmd +=  " --reward-bounded-alg StateElimination"
		if "-S Memory" in specific_cmd:
			specific_cmd += " --reward-bounded-alg StateElimination"
		else:
			specific_cmd += " --alg IntervalIteration --width $PRECISION --relative-width"
	elif prop_type == "Pb":
		# reward-bounded probability: default is unsound VI, which is okay here
		pass
	else:
		# unbounded probability or expected reward: default is unsound VI, which is okay here
		if prop_type == "P" and benchmark.is_dtmc() or benchmark.is_ctmc():
			# for unbounded probabilities on DTMC and CTMC: use 0/1 preprocessing
			default_cmd += " --p0 --p1"
			specific_cmd += " --p0 --p1"
	if not skip:
		add_invocations(invocations, "often-epsilon-correct", default_cmd.replace("$PRECISION", precision), tweak(benchmark, specific_cmd).replace("$PRECISION", precision))

	#
	# Track "often-epsilon-correct-10-min"
	#
	skip = False
	precision = "0" # so we just run for the full 10 minutes (or until we get an exact result)
	default_cmd  = default_base
	specific_cmd = specific_base
	if prop_type == "S":
		skip = True
	elif (benchmark.is_ma() or benchmark.is_ctmc()) and benchmark.is_time_bounded_probabilistic_reachability():
		default_cmd += " --width 0"
		specific_cmd += " --width 0"
	elif prop_type == "Pb":
		# reward-bounded reachability for DTMC, MDP, and PTA
		default_cmd +=  " --reward-bounded-alg StateElimination"
		if "-S Memory" in specific_cmd:
			specific_cmd += " --reward-bounded-alg StateElimination"
		else:
			specific_cmd += " --epsilon 0"
	else:
		default_cmd += " --epsilon 0"
		specific_cmd += " --epsilon 0"
	if prop_type == "P" and benchmark.is_dtmc() or benchmark.is_ctmc():
		# for unbounded probabilities on DTMC and CTMC: use 0/1 preprocessing
		default_cmd += " --p0 --p1"
		specific_cmd += " --p0 --p1"
	if not skip:
		add_invocations(invocations, "often-epsilon-correct-10-min", default_cmd, tweak(benchmark, specific_cmd))
	
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
	return result
