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
	return "modes"

def is_benchmark_supported(benchmark : Benchmark):
	"""returns True if the provided benchmark is supported by the tool and if the given benchmark should appear on the generated benchmark list"""
	
	short = benchmark.get_model_short_name()
	prop = benchmark.get_property_name()
	prop_type = benchmark.get_short_property_type()
	if(short == "bluetooth"                                    # multiple initial states
		or short == "herman"                                     # multiple initial states
		or short == "oscillators"                                # model file too large, cannot be parsed
		or short == "repudiation_malicious"                      # open clock constraints
		):
		return False
	
	return True

def add_invocations(invocations, track_id, default_cmd):
	default_inv = Invocation()
	default_inv.identifier = "default"
	default_inv.track_id = track_id
	default_inv.add_command(default_cmd)
	invocations.append(default_inv)

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

	default_base = "modes/modest modes --unsafe --max-run-length 0 " + benchmark.get_janifilename() + " " + benchmark_settings + " -O out.txt Minimal"

	#
	# Track "probably-epsilon-correct"
	#
	precision = "5e-2"
	default_cmd  = default_base  + " --width $PRECISION --relative-width"
	if benchmark.is_dtmc() or benchmark.is_ctmc():
		add_invocations(invocations, "probably-epsilon-correct", default_cmd.replace("$PRECISION", precision))

	#
	# Track "often-epsilon-correct"
	#
	precision = "1e-3"
	if benchmark.is_dtmc() or benchmark.is_ctmc():
		add_invocations(invocations, "often-epsilon-correct", default_cmd.replace("$PRECISION", precision))

	#
	# Track "often-epsilon-correct-10-min"
	#
	if benchmark.is_dtmc() or benchmark.is_ctmc():
		default_cmd  = default_base  + " -N 2147483647"
	else:
		default_cmd  = default_base  + " --width 2e-2 --relative-width --lss Interruptible 1000000 -L 1000"
		if benchmark.is_pta():
			default_cmd  += " --digital-clocks"
	add_invocations(invocations, "often-epsilon-correct-10-min", default_cmd)
	
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
