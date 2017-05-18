#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""
import sys
import IPython
import os
import logging
import struct

from casperfpga import skarab_fpga

FPG = 'sbram_test_2017-5-17_1628.fpg'
FPG = '/home/paulp/bofs/sbram_wtf_2017-5-17_1628.fpg'

logging.basicConfig(level=logging.INFO)

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = skarab_fpga.SkarabFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

if f.gbes[0].get_port() != 30000:
    f.gbes[0].set_port(30000)

LEN = 16384

addr_map = range(LEN-1, -1, -1)
addr_map_zeros = [0] * LEN
addr_map_same = range(LEN)


def write_sbram(vector):
    """
    This is how we'd normally use a Shared BRAM yellow block.
    Write data into it from software, which will be used in the fabric.
    :param vector: 
    :return: 
    """
    numwords = 0
    for ctr, vword in enumerate(vector):
        ss = struct.pack('>I', vword)
        f.write('waddr_map', ss, ctr*4)
        numwords += 1
    return numwords


def write_others(vector):
    """
    This is an alternate approach, clocking data into Dual-port and Single-
    port RAM blocks using software registers.
    :param vector: 
    :return: 
    """
    numwords = 0
    f.registers.ram_control.write_int(0)
    f.registers.ram_control.write(sel=True)
    for ctr, vword in enumerate(vector):
        f.registers.ram_data.write(reg=vword)
        f.registers.ram_control.write(addr=ctr, en='pulse')
        numwords += 1
    f.registers.ram_control.write_int(0)
    return numwords


def read_snap(plen=-1):
    """
    Read a snapshot of data to see the output of the different RAM blocks.
    Their address lines are all clocked by the same counter.
    Their outputs should all be the same.
    :param plen: 
    :return: 
    """
    def print_snap_line(ctr, data):
        print '%5i' % ctr,
        for k in data.keys():
            print '%s(%i)' % (k, data[k][ctr]),
        print ''

    d = f.snapshots.waddrs_ss.read(man_valid=True, man_trig=True)['data']
    rv = {
        'sbram': [],
        'dpram': [],
        'spram': [],
        'addr': [],
    }
    snaplen = len(d['waddr_raw'])
    for ctr in range(snaplen):
        rv['addr'].append(d['waddr_raw'][ctr])
        rv['sbram'].append(d['waddr_map1'][ctr])
        rv['dpram'].append(d['waddr_map2'][ctr])
        rv['spram'].append(d['waddr_map3'][ctr])
        if (plen != -1) and (ctr < plen):
            print_snap_line(ctr, d)
    if plen == -1:
        for ctr in range(10):
            print_snap_line(ctr, d)
        print '...'
        for ctr in range(snaplen - 10, snaplen):
            print_snap_line(ctr, d)
    return rv


# the outputs should all be the same
write_sbram(addr_map_same)
write_others(addr_map_same)
d = read_snap()
print ''

# the three RAM outputs should all be the same
write_sbram(addr_map)
write_others(addr_map)
d = read_snap()
print ''

# the three RAM outputs should all be zero
write_sbram(addr_map_zeros)
write_others(addr_map_zeros)
d = read_snap()
print ''

IPython.embed()

# end
