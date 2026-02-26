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
debug = True
stdout = False

pipe = open(pipe_path, "w")

# write output value to fifo
def out(val):
    assert type(val) == int
    try:
        pipe.write(str(val))
        pipe.close
    except OSError as e:
        raise Exception(f"out(): {e}")
        return False

# log messages to stderr, and, if stdout flag is set, to stdout
def log(msg):
    print(f"{round(time.time(), 1)} netcheck: {msg}", file=sys.stderr)
    if stdout: print(f"{time.time()} netcheck: {msg}")

# process arguments
parser=optparse.OptionParser()
parser.add_option("-d", "--debug", action="store_true", dest="debug", help="increase logging")
parser.add_option("-s", "--stdout", action="store_true", dest="stdout", help="log to stdout as well as stderr")
parser.add_option("-m", "--mark", dest="mark", metavar="MARK", help="use so_mark MARK for packets")
parser.add_option("-D", "--dir", dest="iplistdir", metavar="DIR", help="look for ip files in DIR")
parser.add_option("-f", "--file", dest="pipe_path", metavar="FILE", help="use FIFO at FILE")
(opts, args) = parser.parse_args()

if debug: log(f"opts: {opts}; args: {args}")

# create fifo
try:
    posix.mkfifo(pipe_path)
    if debug: log("FIFO created")
except FileExistsError:
    if debug: log("FIFO exists, continue...")
    pass
except OSError as e:
    if debug: log(f"FIFO creation failed: {e}")
    sys.exit(2)

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
    if debug: log(f"health %: {str(healthPercentage)} ; success count: {str(successcount)}")
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
        log(f"connecting to: {host} ({domain.strip()}) on port {str(port)}")
        try:
            s.connect((host, port))
        except OSError:
            pass
        try:
            if s.getpeername():
                log("connection successful")
                if successcount < 10:
                    successcount += 1
                    s.close()
                else:
                    log("connection unsuccessful")
                    if successcount > 0:
                        successcount -= 1
                    s.close()
        except OSError:
            log("connection unsuccessful")
            if successcount > 0:
                successcount -= 1
                s.close()
    # add other modes
    time.sleep(0.5)

