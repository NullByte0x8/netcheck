#!/usr/bin/python3

import socket
import sys
import time
import random
import os
import optparse
import posix
import asyncio
import statistics
# import dns  # dnspython, pypi, 2.2.1

debug = None
mark = ""
iplistdir = ""
pipe_path = ""
tcp_timeout = 1
tcp_port = 80
tcp_amount = 10
healthy_threshold = 90
healthy_sleep = 5
unhealthy_sleep = 0.5
colors = (
        "\x1b[0m",   # end of color (DEBUG)
        "\x1b[93m",  # bright yellow (WARN)
        "\x1b[91m"   # bright red (ERROR)
)

# write output value to fifo
def out(val):
    assert type(val) == int
    try:
        pipe.write(str(val) + "\n")
        pipe.close
        log("dbg", f"wrote {val} to pipe")
    except OSError as e:
        raise Exception(f"out(): {e}")
        return False

# log messages to stderr, and, if stdout flag is set, to stdout
def log(sev, msg):
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
async def try_tcp(host, port, hostname, timeout):
    log("dbg", f"trying tcp for {host}, {hostname}")
    async def inner():
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
        except ConnectionRefusedError:
            log("dbg", f"connection to {host}, {hostname} refused (success)")
        except Exception as e:
            log("dbg", f"connection to {host}, {hostname} failed: {e}")
            return False
        log("dbg", f"connection to {host}, {hostname} successful")
        return True
    try:
        async with asyncio.timeout(timeout):
            ret = await inner()
    except TimeoutError:
        log("dbg", f"connection to {host}, {hostname} failed")
        return False
    return ret

# run try_tcp tcp_amount times concurrently
async def run_tcp_test(timeout):
    ip_list = random.sample(os.listdir(iplistdir), tcp_amount)
    hn_list = []
    success = 0
    for filename in ip_list:
        with open(f"{iplistdir}/{filename}", "r") as f:
            hn = f"{f.read().strip()}"
            hn_list.append(hn)
    log("dbg", f"ip list for tcp test: {ip_list}")
    log("dbg", f"hostname list for tcp test: {hn_list}")
    results = await asyncio.gather(
            *[try_tcp(ip_list[i], tcp_port, hn_list[i], timeout) for i in range(len(ip_list))])
    log("dbg", f"results: {results}")
    for r in results:
        if r:
            success += 1
    log("dbg", f"successes in ip test: {success}")
    return success

async def main():
    parse_opts()
    with open(pipe_path, "w", buffering=1) as pipe:
        create_fifo()
        timeout = tcp_timeout
        while True:
            result = await run_tcp_test(timeout)
            perc = int(result / tcp_amount * 100)
            log("dbg", f"network health: {perc}")
            if perc >= healthy_threshold:
                time.sleep(healthy_sleep)
            else:
                time.sleep(unhealthy_sleep)
            

asyncio.run(main())
