import os
import sys
import time
import math
import csv
import json
from decimal import *

from collections import OrderedDict

def load_json(path : str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        return json.load(json_file, object_pairs_hook=OrderedDict)

def save_json(json_data, path : str):
    with open(path, 'w') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent='\t')

def load_csv(path : str):
    with open(path, 'r') as csv_file:
        return list(csv.reader(csv_file, delimiter='\t'))

def save_csv(csv_data, path : str):
    with open(path, 'w') as csv_file:
        writer = csv.writer(csv_file, delimiter='\t')
        writer.writerows(csv_data)

def ensure_directory(path : str):
    if not os.path.exists(path):
        os.makedirs(path)

def is_valid_filename(name : str, invalid_chars = None):
    if invalid_chars is not None:
        for c in invalid_chars:
            if c in name:
                return False
    try:
        if os.path.isfile(name):
            return True
        open(name, 'a').close()
        os.remove(name)
    except IOError:
        return False
    return True

def is_bool(expr):
    if isinstance(expr, bool):
        return True
    try:
        return expr.lower() in ["true", "false"]
    except:
        return False

def is_number(expr):
    if is_bool(expr):
        return False
    try:
        Decimal(expr)
    except (TypeError, InvalidOperation):
        return False
    return True

def is_interval(expr):
    try:
        if is_number(expr["lower"]) and is_number(expr["upper"]):
            return True
    except (InvalidOperation, KeyError, TypeError):
        pass
    return False

def is_number_or_interval(expr):
    return is_number(expr) or is_interval(expr)

def try_to_bool_or_decimal(expr):
    if is_bool(expr):
        return bool(expr)
    if is_number(expr):
        return Decimal(expr)
    return expr

def get_decimal_representation(number):
    if is_number(number):
        return Decimal(number)
    else:
        return Decimal(number["num"]) / Decimal(number["den"])

def get_absolute_error(reference_value, result_value : Decimal):
    if is_interval(reference_value):
        u = Decimal(reference_value["upper"])
        l = Decimal(reference_value["lower"])
        if result_value.is_infinite() and not u.is_infinite():
            return Decimal(math.inf)
        elif result_value < l:
            return get_absolute_error(l, result_value)
        elif result_value > u:
            return get_absolute_error(u, result_value)
        else:
            return Decimal(0)
    if result_value.is_infinite() and reference_value.is_infinite():
        return Decimal(0)
    return abs(Decimal(reference_value) - Decimal(result_value))

def get_relative_error(reference_value : Decimal, result_value : Decimal):
    if is_interval(reference_value):
        u = Decimal(reference_value["upper"])
        l = Decimal(reference_value["lower"])
        if result_value.is_infinite() and not u.is_infinite():
            return Decimal(math.inf)
        elif result_value < l:
            return get_relative_error(l, result_value)
        elif result_value > u:
            return get_relative_error(u, result_value)
        else:
            return Decimal(0)
    if reference_value == 0:
        if result_value == 0:
            return Decimal(0)
        else:
            return Decimal(math.inf)
    elif reference_value.is_infinite():
        if result_value.is_infinite():
            return Decimal(0)
        else:
            return Decimal(math.inf)
    return get_absolute_error(reference_value, result_value) / reference_value

def is_result_correct(reference, result):
    if is_number_or_interval(reference) != is_number(result):
        return False
    if is_number_or_interval(reference):
        if settings.is_relative_precision():
            return get_relative_error(reference, result) <= settings.goal_precision()
        else:
            return get_absolute_error(reference, result) <= settings.goal_precision()
    else:
        return reference == result

class Progressbar(object):
    def __init__(self, max_value, label="Progress", width=50, delay=0.5):
        self.progress = 0
        self.max_value = max_value
        self.label = label
        self.width = width
        self.delay = delay
        self.last_time_printed = time.time()
        sys.stdout.write("\n")
        self.print_progress(0)

    def print_progress(self, value):
        now = time.time()
        if now - self.last_time_printed >= self.delay or value == self.max_value or value == 0:
            progress = (value * self.width) // self.max_value
            sys.stdout.write("\r{}: [{}{}] {}/{} ".format(self.label, '#'*progress, ' '*(self.width-progress), value, self.max_value))
            sys.stdout.flush()
            self.last_time_printed = now
            return True
        return False

class Settings(object):
    def __init__(self):
        self.settings_filename = "settings.json"
        self.json_data = OrderedDict()
        if os.path.isfile(self.settings_filename):
            self.json_data = load_json(self.settings_filename)
        if self.set_defaults():
            self.save()

    def set_defaults(self):
        set_an_option = False
        if not "benchmarks-directory" in self.json_data:
            self.json_data["benchmarks-directory"] = os.path.realpath(os.path.join(sys.path[0], "../benchmarks/"))
            set_an_option = True
        if not "logs-directory" in self.json_data:
            self.json_data["logs-directory"] = os.path.join(os.path.realpath(os.curdir), "logs/")
            set_an_option = True
        if not "invocations-file" in self.json_data:
            self.json_data["invocations-file"] = os.path.join(os.path.realpath(os.curdir), "invocations.json")
            set_an_option = True
        if not "results-file" in self.json_data:
            self.json_data["results-file"] = os.path.join(os.path.realpath(os.curdir), "results.json")
            set_an_option = True
        if not "results-table-file" in self.json_data:
            self.json_data["results-table-file"] = os.path.join(os.path.realpath(os.curdir), "results.csv")
            set_an_option = True
        if not "benchmark-list-file" in self.json_data:
            self.json_data["benchmark-list-file"] = os.path.join(os.path.realpath(os.curdir), "benchmarks.csv")
            set_an_option = True
        if not "time-limit" in self.json_data:
            self.json_data["time-limit"] = 1800
            set_an_option = True
        if not "goal-precision" in self.json_data:
            self.json_data["goal-precision"] = 1E-5
            set_an_option = True
        if not "relative-precision" in self.json_data:
            self.json_data["relative-precision"] = True
            set_an_option = True
        return set_an_option

    def benchmark_dir(self):
        """ Retrieves the directory where the qcomp benchmarks lie. """
        return self.json_data["benchmarks-directory"]

    def logs_dir(self):
        """ Retrieves the directory in which the tool logs are stored. """
        return self.json_data["logs-directory"]

    def invocations_filename(self):
        """ Retrieves the filename to which the tool invocations are stored (and read from). """
        return self.json_data["invocations-file"]

    def results_filename(self):
        """ Retrieves the filename to which the tool execution results are stored (and read from). """
        return self.json_data["results-file"]

    def results_table_filename(self):
        """ Retrieves the filename to which the tool execution result table is stored. """
        return self.json_data["results-table-file"]

    def benchmark_list_filename(self):
        """ Retrieves the filename to which the benchmark list is stored. """
        return self.json_data["benchmark-list-file"]

    def time_limit(self):
        """ Retrieves the time limit for tool executions (in seconds). """
        return int(self.json_data["time-limit"])

    def goal_precision(self):
        """ Retrieves the precision the tools have to achieved for numerical results. """
        return Decimal(self.json_data["goal-precision"])

    def is_relative_precision(self):
        """ Retrieves whether the precision is with respect to the relative error. """
        return bool(self.json_data["relative-precision"])

    def save(self):
        save_json(self.json_data, self.settings_filename)
        print("Settings saved to {}.".format(os.path.realpath(self.settings_filename)))

settings = Settings()

