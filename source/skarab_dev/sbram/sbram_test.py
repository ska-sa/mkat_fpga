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

FPG = '/home/paulp/bofs/sbram_test_2017-6-9_1050.fpg'

logging.basicConfig(level=logging.INFO)

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = skarab_fpga.SkarabFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

if f.gbes.forty_gbe.get_port() != 30000:
    f.gbes.forty_gbe.set_port(30000)

LEN = 16384

addr_map_reverse = range(LEN-1, -1, -1)
addr_map_zeros = [0] * LEN
addr_map_forwards = range(LEN)


def write_sbram(vector):
    """
    This is how we'd normally use a Shared BRAM yellow block.
    Write data into it from software, which will be used in the fabric.
    :param vector: 
    :return: 
    """
    # logging.info('Writing the shared BRAM via bulkwrite')
    logging.info('Writing the shared BRAM')
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
    logging.info('Writing RAM via registers')
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
        print 'waddr_raw(%5i)' % data['waddr_raw'][ctr],
        print 'sbram_map(%5i)' % data['waddr_map1'][ctr],
        print 'dpram_map(%5i)' % data['waddr_map2'][ctr],
        print 'spram_map(%5i)' % data['waddr_map3'][ctr],
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

# the the second shared bram
for ctr, vword in enumerate(range(4096)):
    ss = struct.pack('>I', vword)
    f.write('waddr_map2', ss, ctr*4)
# then read a few via the register
logging.info('THESE VALUES SHOULD NOT BE ZERO')
for ctr in range(1, 11):
    f.registers.ram_control.write(addr=ctr)
    print ctr, f.registers.map2_data.read()['data']['reg']
print ''

# the outputs should all be the same
logging.info('WRITING MAP - ALL OUTPUT SHOULD BE THE SAME')
write_sbram(addr_map_forwards)
write_others(addr_map_forwards)
d = read_snap()
print ''

# the three RAM outputs should all be the same
logging.info('WRITING INVERSE MAP - ALL OUTPUT SHOULD BE THE SAME')
write_sbram(addr_map_reverse)
write_others(addr_map_reverse)
d = read_snap()
print ''

# the three RAM outputs should all be zero
logging.info('WRITING ZEROS - ALL OUTPUT SHOULD BE ZEROS')
write_sbram(addr_map_zeros)
write_others(addr_map_zeros)
d = read_snap()
print ''

IPython.embed()

# end
