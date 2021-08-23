from benchmark import Benchmark
from invocation import Invocation
from execution import Execution
from utility import *
from shutil import copyfile,move
import sys, importlib
import tmptool

def load(settings):
    try:
        move(os.path.join(sys.path[0], "tmptool.py"), os.path.join(sys.path[0], "tmptool2.py"))
        copyfile(settings.toolscript_filename_name(), os.path.join(sys.path[0], "tmptool.py"))
        importlib.reload(sys.modules["tmptool"])
    finally:
        if os.path.exists(os.path.join(sys.path[0], "tmptool2.py")):
            move(os.path.join(sys.path[0], "tmptool2.py"), os.path.join(sys.path[0], "tmptool.py"))
    
def get_name(settings):
    """ should return the name of the tool as listed on http://qcomp.org/competition/2020/"""
    load(settings)
    return tmptool.get_name()

def get_invocations(settings, benchmark : Benchmark):
    """
    Returns a list of invocations that invoke the tool for the given benchmark.
    It can be assumed that the current directory is the directory from which execute_invocations.py is executed.
    For QCOMP 2019, this should return a list of size at most two, where
    the first entry (if present) corresponds to the default configuration of the tool and
    the second entry (if present) corresponds to an optimized setting (e.g., the fastest engine and/or solution technique for this benchmark).
    Please only provide two invocations if there is actually a difference between them.
    If this benchmark is not supported, an empty list has to be returned.
    For testing purposes, the script also allows to return more than two invocations.
    """
    load(settings)
    return tmptool.get_invocations(benchmark)


def get_result(settings, benchmark : Benchmark, execution : Execution):
    """
    Returns the result of the given execution on the given benchmark.
    This method is called after executing the commands of the associated invocation.
    One can either find the result in the tooloutput (as done here) or
    read the result from a file that the tool has produced.
    The returned value should be either 'true', 'false', a decimal number, or a fraction.
    """
    load(settings)
    return tmptool.get_result(benchmark, execution)
