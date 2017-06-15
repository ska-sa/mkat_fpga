#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Used in conjunction with the spead_test.slx model to test incoming data on 
the frontend of a SKARAB-based f-engine.

The data is expected to be coming from a DSIM sending normal-sized packets, 
but containing a ramp from 0:639, not actual noise data.

@author: paulp
"""
import sys
import IPython
import time
import argparse
import os
import logging

from casperfpga import utils as fpgautils, tengbe
from casperfpga import spead as casperspead, snap as caspersnap
from casperfpga import skarab_fpga
from corr2 import utils

logging.basicConfig(level=logging.INFO)

FPG = '/home/paulp/bofs/spead_test_spead_2017-5-5_1651.fpg'

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = skarab_fpga.SkarabFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

if f.gbes[0].get_port() != 30000:
    f.gbes[0].set_port(30000)


def read_spead_snaps(man_valid=False):
    extended = ('speadsnap3_ss' in f.snapshots.names()) and man_valid
    if extended:
        f.registers.snapwaittime.write(waittime=64500)
    f.registers.control.write(barrelsnap_arm=0, gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0,
                              speadsnap_arm=0,)
    for ctr in (range(0, 6) if extended else range(3)):
        f.snapshots['speadsnap%i_ss' % ctr].arm(man_valid=man_valid)
    f.registers.control.write(barrelsnap_arm=0, gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0,
                              speadsnap_arm=1,)
    time.sleep(1)
    d = {}
    for ctr in range(3):
        d.update(f.snapshots['speadsnap%i_ss' % ctr].read(arm=False)['data'])
    if extended:
        d1 = {}
        for ctr in range(3, 6):
            d1.update(
                f.snapshots['speadsnap%i_ss' % ctr].read(arm=False)['data'])
        # stitch together the data
        last_dtime = d['timestamp'][-1]
        ctr = len(d['timestamp']) - 1
        try:
            while d['timestamp'][ctr] == last_dtime:
                ctr -= 1
            while d['polid'][ctr] != 1:
                ctr -= 1
        except IndexError:
            print 'Trouble calculating stiching d_stop'
            IPython.embed()
        d_stop = ctr
        ctr = 0
        try:
            while d1['timestamp'][ctr] != last_dtime:
                ctr += 1
        except IndexError:
            print 'Trouble calculating stiching d1_start'
            IPython.embed()
        ctr2 = ctr
        while d1['dv'][ctr2] != 1:
            ctr2 += 1
        if d1['polid'][ctr2] != 0:
            print 'd1 should start at pol 0!'
            IPython.embed()
        d1_start = ctr
        for k in d.keys():
            d[k] = d[k][0:d_stop]
            d[k].extend(d1[k][d1_start:])

        # DEBUG
        print 'd_stop:', d_stop
        print 'd1_start:', d1_start
        for ctr in range(d_stop-20, d_stop):
            print ctr,
            for k in d.keys():
                print '%s(%i)' % (k, d[k][ctr]),
            pkt_idx = (d['timestamp'][ctr] >> 12) & 15
            print 'pkt_idx(%2i)' % pkt_idx,
            print ''
        for ctr in range(d1_start, d1_start + 20):
            print ctr,
            for k in d1.keys():
                print '%s(%i)' % (k, d1[k][ctr]),
            pkt_idx = (d1['timestamp'][ctr] >> 12) & 15
            print 'pkt_idx(%2i)' % pkt_idx,
            print ''
        # if d['polid'][d_stop] == d1['polid'][d1_start]:
        #     print 'ERROR - packet duplication!!'
        #     IPython.embed()
        last_eof = 0
        diffs = {}
        for ctr in range(len(d['eof'])):
            if d['eof'][ctr] == 1:
                diff = ctr - last_eof
                if diff not in diffs:
                    diffs[diff] = 0
                diffs[diff] += 1
                last_eof = ctr
        print diffs
        a = diffs.keys()
        a.pop(0)
        print min(a), max(diffs.keys())
        # /DEBUG
        # IPython.embed()
    return d


def speadsnap_to_mat():
    """
    
    :return: 
    """
    rawdata = read_spead_snaps(True)
    import scipy.io as sio
    import numpy as np
    d32 = {ctr: [] for ctr in range(8)}
    for ctr in range(len(rawdata['d0'])):
        d32[0].append(rawdata['d3'][ctr] & (2 ** 32 - 1))
        d32[1].append(rawdata['d3'][ctr] >> 32)
        d32[2].append(rawdata['d2'][ctr] & (2 ** 32 - 1))
        d32[3].append(rawdata['d2'][ctr] >> 32)
        d32[4].append(rawdata['d1'][ctr] & (2 ** 32 - 1))
        d32[5].append(rawdata['d1'][ctr] >> 32)
        d32[6].append(rawdata['d0'][ctr] & (2 ** 32 - 1))
        d32[7].append(rawdata['d0'][ctr] >> 32)
    for ctr in range(8):
        d32[ctr] = ([0] * 100) + d32[ctr]
    rawdata['eof'] = ([0] * 100) + rawdata['eof']
    rawdata['dv'] = ([0] * 100) + rawdata['dv']
    rawdata['timestamp'] = ([0] * 100) + rawdata['timestamp']
    rawdata['heapid'] = ([0] * 100) + rawdata['heapid']
    rawdata['polid'] = ([0] * 100) + rawdata['polid']
    datadict = {
        'simin_d%i' % ctr: {
            'time': [], 'signals': {
                'dimensions': 1, 'values': np.array(d32[ctr], dtype=np.uint32)
            }
        } for ctr in range(8)
    }
    for ctr in range(8):
        datadict['simin_d%i' % ctr]['signals']['values'].shape = \
            (len(d32[ctr]), 1)
    datadict['simin_dv'] = {
        'time': [], 'signals': {
            'dimensions': 1, 'values': np.array(rawdata['dv'], dtype=np.uint32)
        }
    }
    for key in ['eof', 'dv', 'timestamp', 'heapid', 'polid']:
        matvar = 'simin_%s' % key
        datadict[matvar] = {
            'time': [], 'signals': {
                'dimensions': 1,
                'values': np.array(rawdata[key], dtype=np.uint32)
            }
        }
        datadict[matvar]['signals']['values'].shape = (len(rawdata[key]), 1)
    sio.savemat('/tmp/spead.mat', datadict)


def check_ramps(spead_packets):
    last_hdr_time = 0
    errors = False
    for ctr, packet in enumerate(spead_packets):
        print ctr, packet.headers[0x1600], \
            packet.headers[0x1600] - last_hdr_time,
        last_hdr_time = packet.headers[0x1600]
        if packet.headers[0x1600] != packet.headers[0x1]:
            print 'ID_ERROR',
            errors = True
        if packet.data != range(640):
            print 'DATA_ERROR',
            errors = True
        print ''
    return errors


def check_snap_data(print_detail=True):
    rawdata = read_spead_snaps()
    gbe_packets = caspersnap.Snap.packetise_snapdata(rawdata, 'eof')
    lasttime = rawdata['timestamp'][0]
    lastheapid = rawdata['heapid'][0]
    if lastheapid != lasttime:
        print 'HEAP_ID DOES NOT MATCH TIMESTAMP?!'
        IPython.embed()
    spead_errors = 0
    packet_jumps = []
    for ctr, packet in enumerate(gbe_packets[1:]):
        errstr = ''
        d = [0] * 640
        d[0:640:4] = packet['d0']
        d[1:640:4] = packet['d1']
        d[2:640:4] = packet['d2']
        d[3:640:4] = packet['d3']
        if d != range(640):
            spead_errors += 1
            errstr += 'PACKET_DATA_ERROR '
        packettime = packet['timestamp'][0]
        packetheapid = packet['heapid'][0]
        packetidx = (packettime >> 12) & 15
        if packettime != packetheapid:
            spead_errors += 1
            errstr += 'HEAP_ID!=TIMESTAMP '
        if len(packet['timestamp']) != 160:
            spead_errors += 1
            errstr += 'PACKET_LEN!=160(%i)' % len(packet['timestamp'])
        for pktctr in range(len(packet['timestamp'])):
            if print_detail:
                print '(%3i,%3i)' % (ctr, pktctr), \
                    packet['timestamp'][pktctr], packet['heapid'][pktctr], \
                    packet['polid'][pktctr], packet['dv'][pktctr], \
                    packet['eof'][pktctr], '%4i' % packet['d3'][pktctr], \
                    '%4i' % packet['d2'][pktctr], '%4i' % packet['d1'][pktctr],\
                    '%4i' % packet['d0'][pktctr],
                print 'pkt_idx(%2i)' % packetidx,
            if packet['timestamp'][pktctr] != packettime:
                spead_errors += 1
                if print_detail:
                    print 'TIME_ERROR',
            if packet['heapid'][pktctr] != packetheapid:
                spead_errors += 1
                if print_detail:
                    print 'HEAP_ERROR',
            if packet['eof'][pktctr] == 1:
                timediff = packettime - lasttime
                if timediff not in packet_jumps:
                    packet_jumps.append(timediff)
                    if print_detail:
                        print 'EOF(%i)' % timediff,
                lasttime = packettime
            if print_detail:
                print ''
        if print_detail:
            print errstr
    print 'spead_errors:', spead_errors
    print 'spead packet jumps:', packet_jumps


check_snap_data()

#speadsnap_to_mat()
IPython.embed()

# end
