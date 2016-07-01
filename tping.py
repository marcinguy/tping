#!/usr/bin/python

""" Ping scanner with threads  """

__author__ = "Marcin Kozlowski <marcinguy@gmail.com>"


import os
import platform
from threading import Thread as Task
import threading
from Queue import Queue
import pprint
import argparse
import random
from random import randint

import os, sys, socket, struct, select, time

import time, random, sys, collections
 
# From /usr/include/linux/icmp.h; your milage may vary.
ICMP_ECHO_REQUEST = 8 # Seems to be the same on Solaris.
 
 
def checksum(source_string):
    """
    I'm not too confident that this is right but testing seems
    to suggest that it gives the same answers as in_cksum in ping.c
    """
    sum = 0
    countTo = (len(source_string)/2)*2
    count = 0
    while count<countTo:
        thisVal = ord(source_string[count + 1])*256 + ord(source_string[count])
        sum = sum + thisVal
        sum = sum & 0xffffffff # Necessary?
        count = count + 2
 
    if countTo<len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff # Necessary?
 
    sum = (sum >> 16)  +  (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
 
    # Swap bytes. Bugger me if I know why.
    answer = answer >> 8 | (answer << 8 & 0xff00)
 
    return answer
 
 
def receive_one_ping(my_socket, ID, timeout):
    """
    receive the ping from the socket.
    """
    timeLeft = timeout
    while True:
        startedSelect = time.time()
        whatReady = select.select([my_socket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return
 
        timeReceived = time.time()
        recPacket, addr = my_socket.recvfrom(1024)
        icmpHeader = recPacket[20:28]
        type, code, checksum, packetID, sequence = struct.unpack(
            "bbHHh", icmpHeader
        )
        if packetID == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            return timeReceived - timeSent
 
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return
 
 
def send_one_ping(my_socket, dest_addr, ID):
    """
    Send one ping to the given >dest_addr<.
    """
    dest_addr  =  socket.gethostbyname(dest_addr)
 
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    my_checksum = 0
 
    # Make a dummy heder with a 0 checksum.
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    bytesInDouble = struct.calcsize("d")
    data = (192 - bytesInDouble) * "Q"
    data = struct.pack("d", time.time()) + data
 
    # Calculate the checksum on the data and the dummy header.
    my_checksum = checksum(header + data)
 
    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.
    header = struct.pack(
        "bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1
    )
    packet = header + data
    my_socket.sendto(packet, (dest_addr, 1)) # Don't know about the 1
 
 
def do_one(dest_addr, timeout):
    """
    Returns either the delay (in seconds) or none on timeout.
    """
    icmp = socket.getprotobyname("icmp")
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    except socket.error, (errno, msg):
        if errno == 1:
            # Operation not permitted
            msg = msg + (
                " - Note that ICMP messages can only be sent from processes"
                " running as root."
            )
            raise socket.error(msg)
        raise # raise the original error
 
    my_ID = int(random.randint(0,10000)) & 0xFFFF
 
    send_one_ping(my_socket, dest_addr, my_ID)
    delay = receive_one_ping(my_socket, my_ID, timeout)
 
    my_socket.close()
    return delay
 
 
def verbose_ping(dest_addr, timeout = 2, count = 4):
    """
    Send >count< ping to >dest_addr< with the given >timeout< and display
    the result.
    """
    for i in xrange(count):
        print "ping %s..." % dest_addr,
        try:
            delay  =  do_one(dest_addr, timeout)
        except socket.gaierror, e:
            print "failed. (socket error: '%s')" % e[1]
            break
 
        if delay  ==  None:
            print "failed. (timeout within %ssec.)" % timeout
        else:
            delay  =  delay * 1000
            print "get ping in %0.4fms" % delay
    print






def isUp(status,host):
   

    r = do_one(host,3)
    print r
    if r is not None:
      status.put([host, 1])
      resfile.write(host+" up\n")
    else:
      status.put([host, 0])
      resfile.write(host+" down\n")

def print_progress(progress):
    sys.stdout.write('\033[2J\033[H') #clear screen
    for host, percent in progress.items():
        bar = ('=' * int(percent * 20)).ljust(20)
        percent = int(percent * 100)
        sys.stdout.write("%s [%s] %s%%\n" % (host, bar, percent))
    sys.stdout.flush()


if __name__ == '__main__':

    if os.geteuid() != 0:
      exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")

    parser = argparse.ArgumentParser(description='Ping Scanner v0.99')
    parser.add_argument('-i','--input', help='Input list of IPs', required=True)
    parser.add_argument('-o','--output', help='Output', required=True)
    parser.add_argument('-s','--shuffle', help='Shuffle', required=True)
    args = parser.parse_args()
    input = args.input
    output = args.output
    shuffle = args.shuffle
    
    if(shuffle == "yes"):
      with open(input,'rU') as f:
        lines = f.read().splitlines()
      random.shuffle(lines)
      data = lines
    else:
      with open(input,'rU') as f:
        lines = f.read().splitlines()
      data = lines

    resfile = open(output,'w')


    status = Queue()
    progress = collections.OrderedDict()
    workers = []
    for host in data:
        temp=host.rstrip()
        host=temp.split(',')[0]
        child = Task(target=isUp, args=(status,  host))
        child.start()
        workers.append(child)
        progress[host] = 0.0
    while any(i.is_alive() for i in workers):
        time.sleep(0.1)
        while not status.empty():
            host, percent = status.get()
            progress[host] = percent
            print_progress(progress)
    print 'all pings complete'


