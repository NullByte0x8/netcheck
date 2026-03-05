#!/usr/bin/python3

import sys
import time
import random
import os
import optparse
import posix
import asyncio
import statistics

debug = None
mark = ""
iplistdir = ""
pipe_path = ""
tcp_timeout = 0.2
tcp_port = 80
tcp_amount = 3 # amount of tcp_attempt()s allowed to run concurrently
eval_interval = 0.5 # main() will iterate this often
success_delay = 0.2 # tcp_attempt() will sleep this long after a successful attempt before exiting to control cpu and network usage
colors = (
        "\x1b[0m",   # end of color (DEBUG)
        "\x1b[93m",  # bright yellow (WARN)
        "\x1b[91m"   # bright red (ERROR)
)

tasks = []
results = []

sem = asyncio.Semaphore(tcp_amount)


# write output value to fifo
def out(val: int, pipe):
    try:
        pipe.write(str(val) + "\n")
        pipe.close
        log("dbg", f"wrote {val} to pipe")
    except OSError as e:
        raise Exception(f"out(): {e}")
        return False

# log messages to stderr, and, if stdout flag is set, to stdout
def log(sev: str, msg):
    match sev:
        case "dbg":
            if debug >= 2: print(f"{colors[0]}[DEBUG] {msg}", file=sys.stderr)
        case "wrn":
            if debug >= 1: print(f"{colors[1]}[WARN] {msg}", file=sys.stderr)
        case "err":
            print(f"{colors[2]}[ERROR] {msg}", file=sys.stderr)

# process arguments
def parse_opts():
    parser=optparse.OptionParser()
    parser.add_option(
            "-d", "--debug",
            dest="debug",
            metavar="VALUE",
            type="int",
            default=2,
            help="set logging level: 0 for errors only, 1 for errors and warnings, 2 for debug")
    parser.add_option(
            "-m", "--mark",
            dest="mark",
            metavar="MARK",
            help="use so_mark MARK for packets")
    parser.add_option(
            "-D", "--dir",
            dest="iplistdir",
            metavar="DIR",
            default="/run/netcheck/ips/latest",
            help="look for ip files in DIR")
    parser.add_option(
            "-f", "--file",
            dest="pipe_path",
            metavar="FILE",
            default="/run/netcheck/pipe",
            help="use FIFO at FILE")
    (opts, args) = parser.parse_args()

    global debug, mark, iplistdir, pipe_path
    debug, mark, iplistdir, pipe_path = opts.debug, opts.mark, opts.iplistdir, opts.pipe_path

    log("dbg", f"opts: {opts}; args: {args}")

# create fifo
def create_fifo():
    try:
        posix.mkfifo(pipe_path)
        log("dbg", f"FIFO created at {pipe_path}")
    except FileExistsError:
        log("dbg", f"Found FIFO at {pipe_path}")
    except OSError as e:
        log("err", f"FIFO creation failed at {pipe_path}: {e}")
        sys.exit(2)

# run a single tcp connection attempt
async def tcp_attempt(ip: str):
    # use the semaphore's limit to adjust CPU and network usage
    async with sem:
        # read hostname from file, use only for debugging
        if debug >= 2:
            with open(f"{iplistdir}/{ip}", "r") as f:
                hostname = f.read().strip()
        try:
            # attempt a tcp connection with a 0.2s timeout
            # this timeout should always be shorter than the asyncio.sleep() in main()
            reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, tcp_port), tcp_timeout)
            writer.close()
            await writer.wait_closed()
        except ConnectionRefusedError as e:
            # connection refused is a success
            if debug >= 2:
                log("dbg", f"{ip}, {hostname}: {e}")
            await add_result(True)
            await asyncio.sleep(success_delay)
            return True
        except TimeoutError:
            if debug >= 2:
                log("dbg", f"{ip}, {hostname}: timeout")
            await add_result(False)
            return False
        except Exception as e:
            if debug >= 2:
                log("dbg", f"{ip}, {hostname}: {e}")
            await add_result(False)
            return False
        log("dbg", f"{ip}, {hostname}: success")
        await add_result(True)
        await asyncio.sleep(success_delay)
        return True

# returns the integer percentage of successes in results[]
def evaluate():
    return int(results.count(True) / len(results) * 100)

# add val to results[], trim results[] to 10 items
async def add_result(val: bool):
    while len(results) > 10:
        results.pop(0)
    results.append(val)

async def main():
    parse_opts()
    ip_list = os.listdir(iplistdir)
    create_fifo()
    with open(pipe_path, "w", buffering=1) as pipe:
        while True:
            # avoid zero division
            if len(results):
                out(evaluate(), pipe)
    
            # remove tasks that have finished from tasks[];
            # the pointers seem to get automatically removed afterwards, so there
            # probably isn't a memory leak, but a proper test is needed
            for task in tasks:
                if task.done():
                    tasks.remove(task)
            
            # if we are running out of tasks, make a new task for each ip in the list
            if len(tasks) <= 50:
                log("dbg", "adding tasks")
                for ip in ip_list:
                    tasks.append(asyncio.create_task(tcp_attempt(ip)))
    
            # tasks run here
            await asyncio.sleep(eval_interval)


asyncio.run(main())
