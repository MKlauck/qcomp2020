from benchmark import *
from utility import *
from invocation import Invocation
from collections import Counter
import tool_current
import sys
import html

# Gather tool packages
if len(sys.argv) == 1:
    print("Usage: {} invocation-track-id path/to/first/toolpackage path/to/second/toolpackage/ path/to/third/toolpackage ...".format(sys.argv[0]))
    exit(1)
    
tools = OrderedDict()
track_id = sys.argv[1]
for arg in sys.argv[2:]:
    try:
        tool_package_path = os.path.expanduser(arg)
        if not os.path.isdir(tool_package_path):
            print("ERROR: Path {} does not exist".format(tool_package_path))
            raise AssertionError("Path {} does not exist".format(tool_package_path))
        tool_package_path = os.path.realpath(tool_package_path)
        settings = Settings(tool_package_path)
        if not os.path.isfile(settings.invocations_filename_name()):
            print("ERROR: Invocations file {} does not exist".format(settings.invocations_filename_name()))
            raise AssertionError("Invocations file {} does not exist".format(settings.invocations_filename_name()))
        if not os.path.isfile(settings.toolscript_filename_name()):
            print("ERROR: Tool script file {} does not exist".format(settings.toolscript_filename_name()))
            raise AssertionError("Tool script file {} does not exist".format(settings.toolscript_filename_name()))
        toolname = tool_current.get_name(settings)
        if toolname in tools:
            print("ERROR: Found multiple tools with name {}".format(toolname))
            raise AssertionError("ERROR: Found multiple tools with name {}".format(toolname))
        tools[toolname] = tool_package_path        
        print("Found tool #{}: '{}'".format(len(tools), toolname))
    except Exception:
        input("Error when checking for tool package '{}'. Press Return to continue or CTRL+C to abort.".format(tool_package_path))

print("\nSelected {} tool{}: {}".format(len(tools), "" if len(tools) == 1 else "s", ", ".join(tools)))   

settings = Settings()

toolnames = []
for tool in tools:
    toolnames.append(tool)
    tooldir = tools[tool]
    if not os.path.isdir(tooldir): raise AssertionError("Unable to find directory {}".format(os.path.join(os.path.curdir, tooldir)))
        
configs = ["default", "specific"]
first_tool_col = 6
num_cols = first_tool_col + len(tools) # * len(configs)
qcomp_root = os.path.realpath(os.path.join(sys.path[0], "../"))
output_dir = os.path.join(qcomp_root, "competition/2020/results")
if not os.path.exists(output_dir): raise AssertionError("Output directory {} does not exist".format(output_dir))
ensure_directory(os.path.join(output_dir, "logs/"))
benchmarks_csv = load_csv(os.path.join(sys.path[0], "qcomp2020_benchmarks.csv"))
benchmark_ids = []
for benchmark_csv in benchmarks_csv: benchmark_ids.append("{}.{}.{}".format(benchmark_csv[0], benchmark_csv[3], benchmark_csv[4]))
tool_times = OrderedDict()
supported_tools = OrderedDict()
for id in benchmark_ids:
    supported_tools[id] = OrderedDict()
    tool_times[id] = OrderedDict()
    for tool in tools:
        tool_times[id][tool] = []
        supported_tools[id][tool] = []

def write_line(tablefile, indention, content):
    tablefile.write("\t"*indention + content + "\n")

def create_log_page(toolname, benchmark_identifier, result_json):
    tooldir =  os.path.join(settings.logs_dir(), toolname)
    benchmark = get_benchmark_from_id(settings, benchmark_identifier)
    if not "log" in result_json:
        raise AssertionError("Expected a log file.")
    logfilepath = "{}/logs/{}".format(tooldir, result_json["log"])
    with open(logfilepath, 'r') as logfile:
        logs = logfile.read().split("#" * 40)
    ensure_directory(output_dir + "/logs/" + toolname)
    f_path = os.path.join("logs/" + toolname, os.path.basename(logfilepath)[:-4] + ".html")
    with open(os.path.join(output_dir, f_path), 'w') as f:
        indention = 0
        write_line(f, indention, "<!DOCTYPE html>")
        write_line(f, indention, "<html>")
        write_line(f, indention, "<head>")
        indention += 1
        write_line(f, indention, '<meta charset="UTF-8">')
        write_line(f, indention, "<title>{} - {} {} {}</title>".format(toolname, b.get_model_short_name(), b.get_property_name(), b.get_parameter_values_string()))
        write_line(f, indention, '<link rel="stylesheet" type="text/css" href="{}">'.format("../../../../../style.css"))
        indention -= 1
        write_line(f, indention, '</head>')
        write_line(f, indention, '<body>')
        write_line(f, indention, '<h1>{}</h1>'.format(toolname))

        write_line(f, indention, '<div class="box">')
        indention += 1
        write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Benchmark</div></div>')
        write_line(f, indention, '<table style="margin-bottom: 0.75ex;">')
        indention += 1
        write_line(f, indention, '<tr><td>Model:</td><td><a href="{}">{}</a> <span class="tt">v.{}</span> ({})</td></tr>'.format("../../../../../benchmarks/index.html#{}".format(b.get_model_short_name()), b.get_model_short_name(), b.index_json["version"], b.get_model_type().upper()))
        write_line(f, indention, '<tr><td>Parameter(s)</td><td>{}</td></tr>'.format(", ".join(['<span class="tt">{}</span> = {}'.format(p["name"], p["value"]) for p in b.get_parameters()])))
        write_line(f, indention, '<tr><td>Property:</td><td><span class="tt">{}</span> ({})</td></tr>'.format(b.get_property_name(), b.get_property_type()))
        indention -= 1
        write_line(f, indention, "</table>")
        indention -= 1
        write_line(f, indention, "</div>")

        write_line(f, indention, '<div class="box">')
        indention += 1
        write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Invocation ({})</div></div>'.format(result_json["invocation-id"]))
        f.write('\t' * indention + '<pre style="overflow: auto; padding-bottom: 1.5ex; margin-bottom: 0ex;  margin-top: 0ex;">')
        f.write("\n".join(result_json["commands"]))
        f.write('</pre>\n')
        indention -= 1
        write_line(f, indention, "</div>")

        write_line(f, indention, '<div class="box">')
        indention += 1
        write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Execution</div></div>')
        write_line(f, indention, '<table style="margin-bottom: 0.75ex;">')
        indention += 1
        if result_json["timeout"]:
            write_line(f, indention, '<tr><td>Walltime:</td><td style="color: red;">&gt {}s (Timeout)</td></tr>'.format(settings.time_limit()))
        else:
            write_line(f, indention, '<tr><td>Walltime:</td><td style="tt">{}s</td></tr>'.format(result_json["wallclock-time"]))
            return_codes = []
            for log in logs:
                pos = log.find("Return code:\t")
                if pos < 0:
                    raise AssertionError("Log does not contain return code")
                pos += len("Return code:\t")
                return_codes.append(log[pos:log.find("\n",pos)].strip())
            if result_json["execution-error"]:
                write_line(f, indention, '<tr><td>Return code:</td><td style="tt; color: red;">{}</td></tr>'.format(", ".join(return_codes)))
            else:
                write_line(f, indention, '<tr><td>Return code:</td><td style="tt">{}</td></tr>'.format(", ".join(return_codes)))
        first = True
        for note in result_json["notes"]:
            write_line(f, indention, '<tr><td>{}</td><td>{}</td></tr>'.format("Note(s):" if first else "", note))
            first = False
        if "relative-error" in result_json:
            write_line(f, indention, '<tr><td>Relative Error:</td><td style="tt{}">{}</td></tr>'.format("" if result_json["result-correct"] else "; color: red", result_json["relative-error"]))
        indention -= 1
        write_line(f, indention, "</table>")
        indention -= 1
        write_line(f, indention, "</div>")

        for log in logs:
            pos = log.find("\n", log.find("Output:\n")) + 1
            pos_end = log.find("#############################", pos)
            if pos_end < 0:
                pos_end = len(log)
            log_str = log[pos:pos_end].strip()
            if len(log_str) != 0:
                write_line(f, indention, '<div class="box">')
                indention += 1
                write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Log</div></div>')
                f.write("\t" * indention + '<pre style="overflow:auto; padding-bottom: 1.5ex">')
                f.write(html.escape(log_str))
                write_line(f, indention, '</pre>')
                indention -= 1
                write_line(f, indention, "</div>")

            pos = log.find("##############################Output to stderr##############################\n")
            if pos >= 0:
                pos = log.find("\n", pos) + 1
                write_line(f, indention, '<div class="box">')
                indention += 1
                write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">STDERR</div></div>')
                f.write("\t" * indention + '<pre style="overflow:auto; padding-bottom: 1.5ex">')
                pos_end = log.find("#############################", pos)
                if pos_end < 0:
                    pos_end = len(log)
                f.write(html.escape(log[pos:pos_end].strip()))
                write_line(f, indention, '</pre>')
                indention -= 1
                write_line(f, indention, "</div>")
        write_line(f, indention, "</body>")
        write_line(f, indention, "</html>")
    return f_path

def get_result_str(toolname, benchmark_identifier):
    results_dir = os.path.join(settings.logs_dir(), toolname)
    if not os.path.exists(results_dir):
        return ""

    results = []
    all_results = load_json(os.path.join(results_dir, "results.json"))
    for res in all_results:
        if res["benchmark-id"] == benchmark_identifier and res["invocation-track-id"] == track_id:
            results.append(res)
    if len(results) == 0:
        return ""

    results_str = []
    for invid in ["default", "specific"]:
        for res in results:
            if res["invocation-id"] == invid:
                link_attributes = ""
                if res["timeout"]:
                    res_str = "TO"
                    link_attributes = " class='timeout'"
                elif res["execution-error"] or not "result" in res:
                    res_str = "ERR"
                    link_attributes = " class='error'"
                elif "result" in res and "result-correct" in res and not res["result-correct"]:
                    res_str = "INC"
                    link_attributes = " class='incorrect'"
                else:
                    if not (track_id == "often-epsilon-correct-10-min"): 
                        res_str = "%.1f" % res["wallclock-time"]
                        tool_times[benchmark_identifier][toolname].append(res["wallclock-time"])
                    else:
                        if "relative-error" in res:
                            res_str = "%.3f" % res["relative-error"]
                            tool_times[benchmark_identifier][toolname].append(res["relative-error"])
                        else:
                            benchmark = get_benchmark_from_id(settings, res["benchmark-id"])
                            if benchmark.has_reference_result():   #result is a boolean value
                                correct = is_result_correct(settings, benchmark.get_reference_result(), try_to_bool_or_number(res["result"]), "often-epsilon-correct")
                                if(correct):
                                    res_str = "%.3f" % 0.000
                                    tool_times[benchmark_identifier][toolname].append(0.000)
                                else:
                                    res_str = "%.3f" % 1.000
                                    tool_times[benchmark_identifier][toolname].append(1.000)
                            else:
                                res_str = "%.3f" % 0.000
                                print(res["benchmark-id"])      #check these results by hand, there is no reference result
                                tool_times[benchmark_identifier][toolname].append(0.000)
                supported_tools[benchmark_identifier][toolname].append(res_str)
                logpage = create_log_page(toolname, benchmark_identifier, res)
                results_str.append("<a href='{}' {}>{}</a>".format(logpage, link_attributes, res_str))
    if len(results) != len(results_str):
        raise AssertionError("Invalid invocations.")
    return " / ".join(results_str)



    for inv in invocations:
        if inv["benchmark-id"] == b.get_identifier() and len(inv["commands"]) > 0 and inv["commands"][0].strip() != "":
            inv_ids.append(inv["invocation-id"])
    if inv_ids != [] and inv_ids != ["default"] and inv_ids != ["default", "specific"] and inv_ids != ["specific",
                                                                                                       "default"]:
        print("Invalid inv ids {} for {} / {}".format(inv_ids, tool, b.get_identifier()))
    if supportedModelProp and supportedOrig:
        b_entry.append("{}/{}".format(len(inv_ids), "y"))
    elif len(inv_ids) > 0:
        b_entry.append("{}/{}".format(len(inv_ids), "n"))
    else:
        b_entry.append("")
    inv_counts[tool] += len(inv_ids)

def create_quantile_plot_csv(tool_subset = tools, n = None, default_times = True):
    """ :param n: A benchmark is only considered in the plot, if it is supported by at least n tools"""
    results_index = 0 if default_times else -1
    if n is None: n = len(tool_subset)
    comp_tool = None
    if not is_number(n):
        comp_tool = n
        n = len(tool_subset)
    sorted_times = OrderedDict()
    num_supported_benchmarks = Counter()
    num_selected_benchmarks = 0
    for tool in tool_subset: sorted_times[tool] = []
    for id in benchmark_ids:
        num_supported_tools = 0
        is_supported_by_comp_tool = False
        for tool in tool_subset:
            if len(supported_tools[id][tool]) > 0:
                num_supported_tools += 1
                if tool == comp_tool:
                    is_supported_by_comp_tool = True
        if num_supported_tools >= n or is_supported_by_comp_tool:
            num_selected_benchmarks += 1
            for tool in tool_subset:
                if len(supported_tools[id][tool]) > 0:
                    if supported_tools[id][tool][results_index] not in ["TO", "ERR", "INC"]:
                        sorted_times[tool].append(tool_times[id][tool][results_index])
                    num_supported_benchmarks[tool] += 1
    for tool in sorted_times:
        sorted_times[tool] = sorted(sorted_times[tool])
    header = ["n"]
    for tool in tool_subset: header += [tool, tool + "scaled", tool + "shifted"]
    result_csv = [header]
    for n in range(1, num_selected_benchmarks + 1):
        row = [n]
        for tool in tool_subset:
            if len(sorted_times[tool]) >= n:
                tooltime = sorted_times[tool][n-1]
                row.append(tooltime)
                if tooltime < 1.0:
                    row.append(10 ** ((tooltime-1) * 0.3))
                    row.append(1.0)
                else:
                    row.append(tooltime)
                    row.append(tooltime)
            else:
                row.append("")
                row.append("")
                row.append("")
        result_csv.append(row)
    caption = "Quantile plot for {} benchmarks: {}.".format(num_selected_benchmarks,", ".join(["{}({}/{})".format(tool, len(sorted_times[tool]), num_supported_benchmarks[tool]) for tool in tool_subset ]))
    return result_csv, caption

def create_scatter_plot_vs_all_csv(tool, default_times = True):
    result_csv = [["id", "Type", tool, tool + "shifted", "other", "othershifted"]]
    results_index = 0 if default_times else -1
    for id in benchmark_ids:
        if len(supported_tools[id][tool]) > 0:
            row = [id, get_benchmark_from_id(settings, id).get_model_type().lower()]
            res_str = supported_tools[id][tool][results_index]
            if res_str == "TO":
                row.append(4000)
                row.append(4000)
            elif res_str == "ERR":
                row.append(8000)
                row.append(8000)
            elif res_str == "INC":
                row.append(16000)
                row.append(16000)
            else:
                row.append(tool_times[id][tool][results_index])
                row.append(max(1, tool_times[id][tool][results_index]))
            compare_value = 4000
            for compare_tool in tools:
                if compare_tool == tool:
                    continue
                if len(supported_tools[id][compare_tool]) > 0 and supported_tools[id][compare_tool][results_index] not in {"TO", "ERR", "INC"}:
                    compare_value = min(tool_times[id][compare_tool][results_index], compare_value)
            row.append(compare_value)
            row.append(max(1,compare_value))
            result_csv.append(row)
    return result_csv

def create_scatter_plot_vs_all_csv_relative_error(tool, default_times = True):
    result_csv = [["id", "Type", tool, tool + "shifted", "other", "othershifted"]]
    results_index = 0 if default_times else -1
    for id in benchmark_ids:
        if len(supported_tools[id][tool]) > 0:
            row = [id, get_benchmark_from_id(settings, id).get_model_type().lower()]
            res_str = supported_tools[id][tool][results_index]
            if res_str == "TO":
                row.append(80000)
                row.append(80000)
            elif res_str == "ERR":
                row.append(80000)   #80000
                row.append(80000)
            elif res_str == "INC":
                row.append(80000) #800000
                row.append(80000)
            else:
                if not (tool_times[id][tool][results_index] <= 0):
                    row.append(tool_times[id][tool][results_index])
                else:                   #if relative-error is 0.0 write 1e-10 into csv because of logscale in plots
                    row.append(1E-20)
                row.append(max(1, tool_times[id][tool][results_index]))
            compare_value = 80000
            for compare_tool in tools:
                if compare_tool == tool:
                    continue
                if len(supported_tools[id][compare_tool]) > 0 and supported_tools[id][compare_tool][results_index] not in {"TO", "ERR", "INC"}:
                    compare_value = min(tool_times[id][compare_tool][results_index], compare_value)
            if compare_value <= 0:  #if relative-error is 0.0 write 1e-10 into csv because of logscale in plots
                row.append(1E-20)
            else:
                row.append(compare_value)
            row.append(max(1,compare_value))
            result_csv.append(row)
    return result_csv

def create_instances_plot(default_times = True):
    result_csv = [["tool", "solved", "accumulated", "average"]]
    for tool in tools:
        num_solved = 0
        sum_solved = 0
        for id in benchmark_ids:
            if len(supported_tools[id][tool]) > 0:
                results_index = 0 if default_times else -1
                if supported_tools[id][tool][results_index] not in {"TO", "ERR", "INC"}:
                    num_solved += 1
                    sum_solved += tool_times[id][tool][results_index]
        result_csv.append([tool, num_solved, sum_solved, sum_solved / num_solved])
    return result_csv



with open (os.path.join(output_dir, "table_" + track_id + ".html"), 'w') as tablefile:
    tablefile.write(r"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Benchmark results</title>
  <link rel="stylesheet" type="text/css" href="style.css">
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.13/css/jquery.dataTables.min.css">
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/buttons/1.2.4/css/buttons.dataTables.min.css">
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/fixedheader/3.1.2/css/fixedHeader.dataTables.min.css">

  <script type="text/javascript" language="javascript" charset="utf8" src="https://code.jquery.com/jquery-1.12.4.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/1.10.13/js/jquery.dataTables.min.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/fixedheader/3.1.2/js/dataTables.fixedHeader.min.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/buttons/1.2.4/js/dataTables.buttons.min.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/buttons/1.2.4/js/buttons.colVis.min.js"></script>

  <script>
    $(document).ready(function() {
      // Set correct file
      $("#content").load("data.html");
    } );

    function updateBest(table) 
    {
      // Remove old best ones
      table.cells().every( function() {
        $(this.node()).removeClass("bestDefault");
        $(this.node()).removeClass("bestSpecific");
      });
      table.rows().every( function ( rowIdx, tableLoop, rowLoop ) 
      {
            var bestValue = -1
            var bestIndex = []
            var bestSpecificValue = -1
            var bestSpecificIndex = -1
            $.each( this.data(), function( index, value )
            {
                if (index > 5 && table.column(index).visible()) 
                {
                    var text = $(value).text()
                    var pos = text.indexOf("/")
                    if (pos === -1) 
                    {
                        if (["TO", "ERR", "INC", ""].indexOf(text) < 0) 
                        {
                            var number = parseFloat(text);
                            if (bestValue == -1 || bestValue > number) 
                            {
                                // New best value
                                bestValue = number;
                                bestIndex = [index];
                            }
                            if (bestValue == -1 || bestValue == number) 
                            {
                                // New best value
                                bestIndex.push(index);
                            }
                        }
                    } 
                    else 
                    {
                        first = text.slice(0, pos-1)
                        if (["TO", "ERR", "INC", ""].indexOf(first) < 0) 
                        {
                            var number = parseFloat(first);
                            if (bestValue == -1 || bestValue > number) 
                            {
                                // New best value
                                bestValue = number;
                                bestIndex = [index];
                            }
                            if (bestValue == -1 || bestValue == number) 
                            {
                                // New best value
                                bestIndex.push(index);
                            }
                        }
                        second = text.slice(pos+2)
                        if (["TO", "ERR", "INC", ""].indexOf(second) < 0) 
                        {
                            var number = parseFloat(second);
                            if (bestSpecificValue == -1 || bestSpecificValue > number) 
                            {
                                // New best value
                                bestSpecificValue = number;
                                bestSpecificIndex = index;
                            }
                        }
                    }
                }
            });
            // Set new best
            bestIndex.forEach(function(index){
                $(table.cell(rowIdx, index).node()).addClass("bestDefault");
            });
            if (bestSpecificIndex >= 0 && (bestIndex.length = 0 || (!bestIndex.includes(bestSpecificIndex) && bestSpecificValue < bestValue))) {
            $(table.cell(rowIdx, bestSpecificIndex).node()).addClass("bestSpecific");
            }
        });
    }
  </script>

</head>
""")
    indention = 0
    write_line(tablefile, indention, "<body>")
    write_line(tablefile, indention, "<div>")
    indention +=1
    write_line(tablefile, indention, '<table id="table" class="display">')
    indention += 1
    write_line(tablefile, indention, '<thead>')
    indention += 1
    write_line(tablefile, indention, '<tr>')
    indention += 1
    for head in ["Model", "Type", "Original", "Parameters", "Property", "Type"] + toolnames:
        write_line(tablefile, indention, '<th>{}</th>'.format(head))
    indention -= 1
    write_line(tablefile, indention, '</tr>')
    indention -= 1
    write_line(tablefile, indention, '</thead>')
    write_line(tablefile, indention, '<tbody>')
    indention += 1

    for benchmark_id in benchmark_ids:
        b = get_benchmark_from_id(settings, benchmark_id)
        write_line(tablefile, indention, '<tr>')
        indention += 1
        write_line(tablefile, indention, '<td><a href="{}">{}</a></td>'.format(os.path.join(qcomp_root, "benchmarks/index.html#{}".format(b.get_model_short_name())), b.get_model_short_name()))    #for website: "benchmarks/index.html#{}".format
        write_line(tablefile, indention, '<td>{}</td>'.format(b.get_model_type().upper()))
        write_line(tablefile, indention, '<td>{}</td>'.format(b.get_original_format()))
        write_line(tablefile, indention, '<td>{}</td>'.format(b.get_parameter_values_string()))
        write_line(tablefile, indention, '<td>{}</td>'.format(b.get_property_name()))
        write_line(tablefile, indention, '<td>{}</td>'.format(b.get_short_property_type()))
        for toolname in toolnames:
            write_line(tablefile, indention, '<td>{}</td>'.format(get_result_str(toolname, b.get_identifier())))
        indention -= 1
        write_line(tablefile, indention, '</tr>')
    indention -= 1
    write_line(tablefile, indention, '</tbody>')
    indention -= 1
    indention -= 1
    write_line(tablefile, indention, '</table>')
    write_line(tablefile, indention, "<script>")
    indention +=1
    write_line(tablefile, indention, 'var table = $("#table").DataTable( {')
    indention += 1
    write_line(tablefile, indention, '"paging": false,')
    write_line(tablefile, indention, '"autoWidth": false,')
    write_line(tablefile, indention, '"info": false,')
    write_line(tablefile, indention, 'fixedHeader: {')
    indention += 1
    write_line(tablefile, indention, '"header": true,')
    indention -= 1
    write_line(tablefile, indention, '},')
    write_line(tablefile, indention, '"dom": "Bfrtip",')
    write_line(tablefile, indention, 'buttons: [')
    indention += 1
    for columnIndex in range(first_tool_col, num_cols):
        write_line(tablefile, indention, '{')
        indention += 1
        write_line(tablefile, indention, 'extend: "columnsToggle",')
        write_line(tablefile, indention, 'columns: [{}],'.format(columnIndex))
        indention -= 1
        write_line(tablefile, indention, "},")
    tool_columns = [i for i in range(first_tool_col, num_cols)]
    for text, show, hide in zip(["Show all", "Hide all"], [tool_columns, []], [[], tool_columns]):
        write_line(tablefile, indention, '{')
        indention += 1
        write_line(tablefile, indention, 'extend: "colvisGroup",')
        write_line(tablefile, indention, 'text: "{}",'.format(text))
        write_line(tablefile, indention, 'show: {},'.format(show))
        write_line(tablefile, indention, 'hide: {}'.format(hide))
        indention -= 1
        write_line(tablefile, indention, "},")
    indention -= 1
    write_line(tablefile, indention, "],")
    indention -= 1
    write_line(tablefile, indention, "});")
    indention -= 1
    write_line(tablefile, indention, "")
    indention += 1
    write_line(tablefile, indention, 'table.on("column-sizing.dt", function (e, settings) {')
    indention += 1
    write_line(tablefile, indention, "updateBest(table);")
    indention -= 1
    write_line(tablefile, indention, "} );")
    indention -= 1
    write_line(tablefile, indention, "")
    indention += 1
    write_line(tablefile, indention, "updateBest(table);")
    indention -= 1
    write_line(tablefile, indention, "</script>")
    indention -= 1
    write_line(tablefile, indention, "</div>")
    write_line(tablefile, indention, "</body>")
    write_line(tablefile, indention, "</html>")

with open (os.path.join(output_dir, "style.css"), 'w') as stylefile:
    write_line(stylefile, 0, '@import url("{}");'.format(os.path.join(qcomp_root, "fonts/Tajawal/Tajawal.css")))
    stylefile.write(r"""
body {
	margin: 0px auto; padding: 0px;
	font-family: 'Tajawal', sans-serif; font-size: 15px;
	background-color: #FFFFFF; color: #000000;
	hyphens: auto;
	line-height: 1.3;
}

.bestDefault {
    background-color: lightgreen;
}
.bestSpecific {
    background-color: lightblue;
}
.error {
	font-weight: bold;
	background-color: lightcoral;
}
.incorrect {
    background-color: orange;
	font-weight: bold;
}
.timeout {
    background-color: lightgray;
}
""")


if(track_id != "often-epsilon-correct-10-min"):
    # Generate plots
    plot_dir = "competition/2020/results/plots/" + track_id
    ensure_directory(plot_dir)

    # Tool subsets for quantile plots
    subsets = []
    filenames = []
    nums = []

    subsets.append(["ePMC", "mcsta", "Storm", "Storm-static"])
    filenames.append("janitools.csv")
    nums.append(None)

    subsets.append(["ePMC", "mcsta", "Storm", "Storm-static", "PRISM"])
    filenames.append("generalpurpose.csv")
    nums.append(None)

    subsets.append(toolnames)
    filenames.append("all.csv")
    nums.append(0)   

    with open (os.path.join(plot_dir, "plots.tex"), 'w') as plotfile:
        plotfile.write(r"""\documentclass{article}
    \usepackage{pgfplots}
    \usepackage{pgfplotstable}
    \usepackage{tikz}
    \usepackage{xifthen}
    \newcommand{\tool}[1]{\textsc{#1}}

    % Quantile plots
    \newlength{\quantileplotwidth}
    \newlength{\quantileplotheight}
    \setlength{\quantileplotwidth}{\linewidth}
    \setlength{\quantileplotheight}{9cm}
    \newcommand{\quantileplotlegendpos}{south east}
    \tikzset{tool/.code={%
            \ifthenelse{\equal{#1}{mcsta}}{\tikzset{red, mark=x, mark options={thick}}}{}%
            \ifthenelse{\equal{#1}{Storm}}{\tikzset{blue,mark=+, mark options={thick}}}{}%
            \ifthenelse{\equal{#1}{Storm-static}}{\tikzset{cyan,mark=+, mark options={thick}}}{}%
            \ifthenelse{\equal{#1}{ePMC}}{\tikzset{green!70!black, mark=*, mark size=1.5pt}}{}%
            \ifthenelse{\equal{#1}{PRISM}}{\tikzset{orange, mark=asterisk}}{}%
            \ifthenelse{\equal{#1}{PRISM-TUM}}{\tikzset{teal, mark=star}}{}%
            \ifthenelse{\equal{#1}{modes}}{\tikzset{magenta, mark=square*,  mark size=1.5pt}}{}%
            \ifthenelse{\equal{#1}{DFTRES}}{\tikzset{yellow,mark=diamond*}}{}%
            \ifthenelse{\equal{#1}{probFD}}{\tikzset{gray, mark=pentagon*}}{}%
            \ifthenelse{\equal{#1}{ModestFRETpiLRTDP}}{\tikzset{black, mark=triangle*}}{}%
    }}
    \newcommand{\quantileplot}[2]{%
    \begin{tikzpicture}
        \begin{axis}[
            width=\quantileplotwidth,
            height=\quantileplotheight,
            xmin=1,
            ymax=2300,
    %		ymin=0.5,
            ymin=1,
            ymode=log,
            axis x line=bottom,
            axis y line=left,
            ytick= {1, 6, 60, 600, 1200, 1800 },
            yticklabels={$\le$1, 6, 60, 600, 1200, 1800},
            xlabel=solved instances,
            ylabel=time (in s),
            yticklabel style={font=\scriptsize},
            xticklabel style={rotate=290, anchor=west, font=\scriptsize},
            ylabel style={yshift=-0cm},
            legend pos=\quantileplotlegendpos,
            legend style={font=\scriptsize},
        ]
        \foreach \tool in {#2}{%
            \edef\loopbody{
                \noexpand\addplot[tool=\tool] table [x=n,y=\tool shifted, col sep=semicolon] {#1};
            }
            \loopbody
        }
        \draw[densely dotted] (axis cs: 0,1) -- (axis cs: 100,1);
        \legend{#2}
        \end{axis}
    \end{tikzpicture}%
    }

    %Scatter plots
    \newlength{\scatterplotsize}
    \setlength{\scatterplotsize}{8cm}
    \newcommand{\scatterplot}[2]{%
    \begin{tikzpicture}
        \begin{axis}[
                width=\scatterplotsize,
                height=\scatterplotsize,
                axis equal image,
                xmin=0.04,
                ymin=0.04,
                ymax=6000,
                xmax=25000,
                xmode=log,
                ymode=log,
                axis x line=bottom,
                axis y line=left,
                xtick={1,6,60,600,1200,1800},
                xticklabels={1,6,60,600,1200,1800},
                extra x ticks = {4000,8000,16000},
                extra x tick labels = {TO,ERR,INC},
                extra x tick style = {grid = major},
                ytick={1,6,60,600,1200,1800},
                yticklabels={1,6,60,600,1200,1800},
                extra y ticks = {4000},
                extra y tick labels = {n/a},
                extra y tick style = {grid = major},
                xlabel=#2,
                xlabel style={yshift=0cm},
                ylabel=Other tools (best),
                ylabel style={yshift=-0.4cm},
                yticklabel style={font=\scriptsize},
                xticklabel style={rotate=290,anchor=west,font=\scriptsize},
                legend pos=north west,
                legend columns=-1,
                legend style={font=\scriptsize,yshift=0.7cm,xshift=1cm}
            ]
            \addplot[
                scatter,
                only marks,
                scatter/classes={
                    dtmc={mark=square,blue},
                    mdp={mark=triangle,red},
                    ctmc={mark=diamond,orange},
                    ma={mark=pentagon,teal},
                    pta={mark=o,green!70!black}
                },
                scatter src=explicit symbolic
                ]%
                table [col sep=semicolon,x=#2,y=other,meta=Type] {#1};
            \legend{DTMC, MDP, CTMC, MA, PTA}
            \addplot[no marks] coordinates {(0.01,0.01) (3600,3600) };
            \addplot[no marks, densely dotted] coordinates {(0.01,0.1) (360,3600) };
        \end{axis}
    \end{tikzpicture}
    }

    \begin{document}""")
        for subset, filename, n in zip(subsets, filenames, nums):
            # only consider tools of the subsets that are considered
            tool_subset = []
            for tool in subset:
                if tool in tools:
                    tool_subset.append(tool)
                else:
                    print("Tool {} for quantile plot is not selected.".format(tool))
            for default in [True, False]:
                csv, cap = create_quantile_plot_csv(tool_subset, n, default)
                save_csv(csv, os.path.join(plot_dir, ("" if default else "specific") + filename), delim=";")
                subsetlist = ",".join(tool_subset)
                cap += "Default configuration." if default else "Specific configuration."
                plotfile.write(r"""
            \begin{center}
                """ + cap + r"""
                \quantileplot{""" + ("" if default else "specific") + filename + "}{" + subsetlist + r"""}
            \end{center}
                    """)
            plotfile.write("\pagebreak\n")

        for tool in toolnames:
            for default in [True, False]:
                csv = create_scatter_plot_vs_all_csv(tool, default)
                filename = "scatter{}{}.csv".format("" if default else "specific", tool)
                num_fastest = 0
                for row in csv[1:]:
                    if row[2] < row[4]:
                        num_fastest += 1
                save_csv(csv, os.path.join(plot_dir, filename), delim=";")
                cap = "Scatter Plot for {} with {} settings (n={}).".format(tool, "default" if default else "specific", len(csv)-1)
                plotfile.write(r"""
            \begin{center}
                """ + cap + r"""
                \scatterplot{""" + filename + "}{" + tool + r"}{\tool{" + tool + "} " + (" ({}, fastest on {}/{})".format("default" if default else "specific", num_fastest, len(csv) - 1)) + r"""}
            \end{center}
                """)
            plotfile.write("\pagebreak\n")

        plotfile.write("\end{document}\n")
else:
    plot_dir = "competition/2020/results/plots/" + track_id
    ensure_directory(plot_dir)

    with open (os.path.join(plot_dir, "plots.tex"), 'w') as plotfile:
        plotfile.write(r"""\documentclass{article}
    \usepackage{pgfplots}
    \usepackage{pgfplotstable}
    \usepackage{tikz}
    \usepackage{xifthen}
    \newcommand{\tool}[1]{\textsc{#1}}

    %Scatter plots
    \newlength{\scatterplotsize}
    \setlength{\scatterplotsize}{8cm}
    \newcommand{\scatterplot}[2]{%
    \begin{tikzpicture}
        \begin{axis}[
                width=\scatterplotsize,
                height=\scatterplotsize,
                axis equal image,
                xmin=-0.04,
                ymin=-0.04,
                ymax=100000,
                xmax=100000,  %10000000
                xmode=log,
                ymode=log,
                axis x line=bottom,
                axis y line=left,
                xtick={1E-7, 1E-6, 1E-5, 1E-4,10,100,1000,10000},
                xticklabels={1e-7, 1e-6, 1e-5, 1e-4,10,100,1000,10000},
                extra x ticks = {80000}, %800000,8000000}
                extra x tick labels = {n/a},
                extra x tick style = {grid = major},
                ytick={1E-7, 1E-6, 1E-5, 1E-4,10,100,1000,10000},
                yticklabels={1e-7, 1e-6, 1e-5, 1e-4,10,100,1000,10000},
                extra y ticks = {80000},
                extra y tick labels = {n/a},
                extra y tick style = {grid = major},
                xlabel=#2,
                xlabel style={yshift=-0.1cm},
                ylabel=Other tools (best),
                ylabel style={yshift=-0.2cm},
                yticklabel style={font=\scriptsize},
                xticklabel style={rotate=290,anchor=west,font=\scriptsize},
                legend pos=north west,
                legend columns=-1,
                legend style={font=\scriptsize,yshift=0.8cm,xshift=1cm}
            ]
            \addplot[
                scatter,
                only marks,
                scatter/classes={
                    dtmc={mark=square,blue},
                    mdp={mark=triangle,red},
                    ctmc={mark=diamond,orange},
                    ma={mark=pentagon,teal},
                    pta={mark=o,green!70!black}
                },
                scatter src=explicit symbolic
                ]%
                table [col sep=semicolon,x=#2,y=other,meta=Type] {#1};
            \legend{DTMC, MDP, CTMC, MA, PTA}
            \addplot[no marks] coordinates {(1E-20,1E-20) (100000,100000)};
            \addplot[no marks, densely dotted] coordinates {(1E-20,1E-19) (10000,100000)};
        \end{axis}
    \end{tikzpicture}
    }

    \begin{document}""")
        for tool in toolnames:
            for default in [True, False]:
                csv = create_scatter_plot_vs_all_csv_relative_error(tool, default)
                filename = "scatter{}{}.csv".format("" if default else "specific", tool)
                num_fastest = 0
                for row in csv[1:]:
                    if row[2] <= row[4]:
                        num_fastest += 1
                save_csv(csv, os.path.join(plot_dir, filename), delim=";")
                cap = "Scatter Plot for {} with {} settings (n={}).".format(tool, "default" if default else "specific", len(csv)-1)
                plotfile.write(r"""
            \begin{center}
                """ + cap + r"""
                \scatterplot{""" + filename + "}{" + tool + r"}{\tool{" + tool + "} " + (" ({}, most precise on {}/{})".format("default" if default else "specific", num_fastest, len(csv) - 1)) + r"""}
            \end{center}
                """)
            plotfile.write("\pagebreak\n")

        plotfile.write("\end{document}\n")