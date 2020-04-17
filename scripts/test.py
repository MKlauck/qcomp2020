import subprocess, threading, time, signal, os

interrupt_signal: int
try:
    interrupt_signal = signal.CTRL_C_EVENT #signal.CTRL_BREAK_EVENT
except AttributeError:
    interrupt_signal = signal.SIGINT


class CommandExecution(object):
    """ Represents the execution of a single command line argument. """
    def __init__(self):
        self.timeout = None
        self.return_code = None
        self.output = None
        self.wall_time = None
        self.proc = None

    def stop(self):
        self.timeout = True
        print("send signal")
        self.proc.send_signal(signal.SIGINT)
        time.sleep(10)
        self.proc.kill()


    def run(self):
        print("drin")
        time_limit = 15
        command_line_list = "./toolset_release/toolset/Binaries/Release/linux-x64/modest mcsta eajs.5.jani --epsilon 1e-3 --props ExpUtil -E energy_capacity=250,B=11".split()
        #"C:\\Users\\Michaela\\toolset\\Binaries\\Release\\FretLrtdp.exe C:\\Users\\Michaela\\qcomp2020\\benchmarks\\mdp\\elevators\\elevators.b-11-9.jani --epsilon 1e-3".split() 
        command_line_list[0] = os.path.expanduser(command_line_list[0])
        self.proc = subprocess.Popen(command_line_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, encoding='utf-8')

        start_time = time.time()
        timer = threading.Timer(time_limit, self.stop)
        self.timeout = False
        self.output = ""
        timer.start()
        try:
            stdout, stderr = self.proc.communicate()
        except Exception as e:
            self.output = self.output + "Error when executing the command:\n{}\n".format(e)
        finally:
            timer.cancel()
            self.wall_time = time.time() - start_time
            self.return_code = self.proc.returncode
        self.output = self.output + stdout

        print("unten")
        print(self.output)

ex = CommandExecution()
ex.run()