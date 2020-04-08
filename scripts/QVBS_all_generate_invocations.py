from benchmark import *
from utility import *
from invocation import Invocation
import tool

"""
This script creates a list of invocations that can then be executed via 'execute_invocations.py'
If a benchmark list has been created before, only benchmarks on this benchmark list are considered.
"""
if __name__ == "__main__":
    benchmarks = get_all_benchmarks(settings,os.path.join(settings.benchmark_dir(), "index.json"))
    benchmark_list = None
    if os.path.isfile(settings.benchmark_list_filename()):
        benchmark_list = load_csv(settings.benchmark_list_filename())
        progressbar = Progressbar(len(benchmark_list), "Processing benchmarks")
    else:
        progressbar = Progressbar(len(benchmarks), "Processing benchmarks")

    invocations = []
    num_b = 0
    for b in benchmarks:
        if benchmark_list is not None:
            on_benchmark_list = False
            for entry in benchmark_list:
                entry_id = "{}.{}.{}".format(entry[0], entry[2], entry[3])
                if entry_id == b.get_identifier():
                    on_benchmark_list = True
                    benchmark_list.remove(entry)
                    break
            if not on_benchmark_list:
                continue
        num_b = num_b + 1
        progressbar.print_progress(num_b)
        b.check_validity()
        invocations_b = tool.get_invocations(b)
        if invocations_b is not None:
            if isinstance(invocations_b, Invocation):
                invocations_b = [invocations_b]
            for i in invocations_b:
                i_json = OrderedDict([("benchmark-id", b.get_identifier())])
                i_json.update(i.to_json())
                invocations.append(i_json)
    save_json(invocations, settings.invocations_filename())
    print("\nSaved {} invocations to file '{}'".format(len(invocations), settings.invocations_filename()))
    if benchmark_list is not None and len(benchmark_list) != 0:
        print("Unable to find the following entries of the benchmark list:")
        for b in benchmark_list:
            print('\t'.join(b))