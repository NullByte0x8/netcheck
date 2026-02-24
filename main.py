#!/usr/bin/python3

import socket
import sys
import time
import random
import os
import getopt
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

try:
    posix.mkfifo(pipe_path)
    print("FIFO created")
except FileExistsError:
    print("FIFO exists, continue...")
except OSError as e:
    print(f"FIFO creation failed: {e}")
    sys.exit(2)

def out(val):
    if(type(val) == int):
        pass
    else:
        raise TypeError("out(): val must be int")
        return False
    try:
        with open(pipe_path, "w") as pipe:
            pipe.write(val)
            pipe.close
    except OSError as e:
        raise Exception(f"out(): {e}")
        return False

def quit(val, msg):
    try:
        os.remove(pipe_path)
    except Exception as e:
        print(e)
    print(str(msg))
    sys.exit(int(val))

try:
    opts, args = getopt.getopt(sys.argv, "hm:", ["help", "mark="])
except getopt.GetoptError:
    print("netcheck.py -m:<SO_MARK value> | netcheck.py --mark=<SO_MARK value>")
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-h", "--help"):
        print("netcheck.py -m:<SO_MARK value> | netcheck.py --mark=<SO_MARK value>")
        sys.exit()
    elif opt in ("-m", "--mark"):
        mark = arg

while True:
    # moderandomizer = random.randint(1, 100)
    # if moderandomizer <= 33:
    #    mode = 1
    # elif 33 < moderandomizer < 66:
    #    mode = 2
    # elif moderandomizer >= 66:
    #    mode = 3
    try:
        healthPercentage = successcount / 10 * 100
    except ZeroDivisionError:
        healthPercentage = 100
    print("health %: " + str(healthPercentage) + "; success count:" + str(successcount))
    try:
        out(int(healthPercentage))
    except KeyboardInterrupt:
        quit(0, "\nexiting...")
    except Exception as e:
        quit(2, str(e))
    if successcount >= 10:
        successcount -= 1
    try:
        if mode == 1:  # TCP on port 80
            s = socket.socket()
            s.getsockopt(socket.SOL_SOCKET, socket.SO_MARK, )
            s.settimeout(0.5)
            host = random.choice(os.listdir(iplistdir))
            port = 80
            print("connecting to: " + host + " on port " + str(port))
            try:
                s.connect((host, port))
            except OSError:
                pass
            try:
                if s.getpeername():
                    print("connection successful")
                    if successcount < 10:
                        successcount += 1
                        s.close()
                    else:
                        print("connection unsuccessful")
                        if successcount > 0:
                            successcount -= 1
                        s.close()
            except OSError:
                print("connection unsuccessful")
                if successcount > 0:
                    successcount -= 1
                    s.close()
        # add other modes
    except KeyboardInterrupt:
        quit(0, "\nexiting...")
        sys.exit()
    try:
        time.sleep(0.5)
    except KeyboardInterrupt:
        quit(0, "\nexiting...")
        sys.exit()

