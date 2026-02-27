#!/usr/bin/python3

import socket
import sys
import time
import random
import os
import optparse
import posix
import asyncio
# import dns  # dnspython, pypi, 2.2.1

iplistdir = "/run/netcheck/ips/latest"
pipe_path = "/run/netcheck/pipe"
successcount = 10
healthPercentage = 100
mode = 1  # 1 = TCP on port 80; 2 = DNS check; 3 = ICMP echo
tcpweight = 33
dnsweight = 33
icmpweight = 33
totalweight = tcpweight + dnsweight + icmpweight
highestweight = max(tcpweight, dnsweight, icmpweight)
lowestweight = min(tcpweight, dnsweight, icmpweight)
debug = 2
colors = (
        "\x1b[0m",   # end of color (DEBUG)
        "\x1b[93m",  # bright yellow (WARN)
        "\x1b[91m"   # bright red (ERROR)
)

# write output value to fifo
def out(val):
    assert type(val) == int
    try:
        pipe.write(str(val) + " ")
        pipe.close
        log(0, f"wrote {val} to pipe")
    except OSError as e:
        raise Exception(f"out(): {e}")
        return False

# log messages to stderr, and, if stdout flag is set, to stdout
def log(sev, msg):
    match sev:
        case 0:
            if debug >= 2: print(f"{colors[0]}[DEBUG] {msg}", file=sys.stderr)
        case 1:
            if debug >= 1: print(f"{colors[1]}[WARN] {msg}", file=sys.stderr)
        case 2:
            print(f"{colors[2]}[ERROR] {msg}", file=sys.stderr)

# process arguments
parser=optparse.OptionParser()
parser.add_option("-d", "--debug", dest="debug", metavar="VALUE", help="set logging level: 0 for errors only, 1 for errors and warnings, 2 for debug")
parser.add_option("-m", "--mark", dest="mark", metavar="MARK", help="use so_mark MARK for packets")
parser.add_option("-D", "--dir", dest="iplistdir", metavar="DIR", help="look for ip files in DIR")
parser.add_option("-f", "--file", dest="pipe_path", metavar="FILE", help="use FIFO at FILE")
(opts, args) = parser.parse_args()

log(0, f"opts: {opts}; args: {args}")


# create fifo
try:
    posix.mkfifo(pipe_path)
    log(0, f"FIFO created at {pipe_path}")
except FileExistsError:
    log(0, f"Found FIFO at {pipe_path}")
    pass
except OSError as e:
    log(2, f"FIFO creation failed at {pipe_path}: {e}")
    sys.exit(2)

with open(pipe_path, "w") as pipe:
    while True:
        # moderandomiser = random.randint(1, 100)
        # if moderandomiser <= 33:
        #    mode = 1
        # elif 33 < moderandomiser < 66:
        #    mode = 2
        # elif moderandomiser >= 66:
        #    mode = 3
        try:
            healthPercentage = successcount / 10 * 100
        except ZeroDivisionError:
            healthPercentage = 100
        log(0, f"health %: {str(healthPercentage)} ; success count: {str(successcount)}")
        out(int(healthPercentage))
        if successcount >= 10:
            successcount -= 1
        if mode == 1:  # TCP on port 80
            s = socket.socket()
            s.getsockopt(socket.SOL_SOCKET, socket.SO_MARK, )
            s.settimeout(0.5)
            host = random.choice(os.listdir(iplistdir))
            with open(f"{iplistdir}/{host}") as f:
                domain = f.read()
            port = 80
            log(0, f"connecting to: {host} ({domain.strip()}) on port {str(port)}")
            try:
                s.connect((host, port))
            except OSError:
               pass
            try:
                if s.getpeername():
                    log(0, f"connection to {host} ({domain.strip()}) successful")
                    if successcount < 10:
                        successcount += 1
                        s.close()
                else:
                    log(0, f"connection to {host} ({domain.strip()}) unsuccessful: !getpeername()")
                    if successcount > 0:
                        successcount -= 1
                    s.close()
            except OSError as e:
                log(0, f"connection to {host} ({domain.strip()}) unsuccessful: {e}")
                if successcount > 0:
                    successcount -= 1
                s.close()
        # add other modes
        time.sleep(0.5)

