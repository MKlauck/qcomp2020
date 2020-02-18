from benchmark import *
from utility import *
import tool

"""
This script creates the list of benchmarks, for which the method 'is_on_benchmark_list' in tool.py returns True.
"""
if __name__ == "__main__":
    benchmarks = get_all_benchmarks(os.path.join(settings.benchmark_dir(), "index.json"))
    benchmark_list = []
    progressbar = Progressbar(len(benchmarks), "Processing benchmarks")
    num_b = 0
    for b in benchmarks:
        num_b = num_b + 1
        progressbar.print_progress(num_b)
        b.check_validity()
        if tool.is_on_benchmark_list(b):
            benchmark_list.append([b.get_model_short_name(), b.get_model_type().upper(), b.get_parameter_values_string(), b.get_property_name(), b.get_short_property_type()])
    save_csv(benchmark_list, settings.benchmark_list_filename())
    print("\nSaved {} benchmark list items to file '{}'".format(len(benchmark_list), settings.benchmark_list_filename()))

