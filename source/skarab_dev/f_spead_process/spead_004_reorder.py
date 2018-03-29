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
import os
import logging

from casperfpga import CasperFpga

logging.basicConfig(level=logging.INFO)

FPG = '/home/paulp/bofs/spead_test_reorder_2017-5-11_1435.fpg'
FPG = '/home/paulp/bofs/spead_test_reorder_2017-6-15_1453.fpg'
FPG = '/home/paulp/bofs/spead_004_reorder_2017-6-15_1616.fpg'

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = CasperFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

fortygbe = f.gbes[f.gbes.names()[0]]
if fortygbe.get_port() != 7148:
    fortygbe.set_port(7148)


def read_reosnap_read_write():
    f.snapshots.reosnap_write_ss.arm(man_valid=True)
    f.snapshots.reosnap_read_ss.arm(man_valid=True)
    f.registers.reorder_control.write(trig='pulse')
    d = f.snapshots.reosnap_write_ss.read(arm=False)['data']
    dr = f.snapshots.reosnap_read_ss.read(arm=False)['data']
    last_maxcnt = d['maxcnt'][0] - 1
    last_pkt_start = -1
    last_pol = 0 if d['pol0_we'][0] else 1
    last_waddr = -1
    errors = {'relock': 0, 'disc': 0, 'waddr': 0,
              'timestep': 0, 'packetlen': 0, 'packettime': 0}
    for ctr in range(len(d['maxcnt'])):
        if not (d['pol0_we'][ctr] or d['pol1_we'][ctr]):
            continue
        this_waddr = d['waddr'][ctr]
        this_pol = 0 if d['pol0_we'][ctr] else 1
        this_maxcnt = d['maxcnt'][ctr]
        print '%5i' % ctr,
        for k in d.keys():
            print '%s(%i)' % (k, d[k][ctr]),
        if d['relock'][ctr]:
            errors['relock'] += 1
        if d['disc'][ctr]:
            errors['disc'] += 1
        new_packet = (last_pol != this_pol) or (this_maxcnt != last_maxcnt)
        if new_packet:
            pkt_len = this_waddr - last_pkt_start
            if this_pol == 1:
                if pkt_len != 0:
                    print 'PKT_LEN_ERROR(%i)' % pkt_len,
                    errors['packetlen'] += 1
                else:
                    print 'PACKET_LEN(%i)' % pkt_len,
                last_waddr -= 160
            else:
                if (pkt_len != 160) and not \
                        (this_waddr == 0 and last_pkt_start == 2400):
                    print 'PKT_LEN_ERROR(%i)' % pkt_len,
                    errors['packetlen'] += 1
                else:
                    print 'PACKET_LEN(%i)' % pkt_len,
                timestep = this_maxcnt - last_maxcnt
                if timestep != 1:
                    print 'TIMESTEP_ERR(%i)' % timestep,
                    errors['timestep'] += 1
            last_maxcnt = this_maxcnt
            last_pkt_start = this_waddr
        if (this_waddr != last_waddr + 1) and not \
                (this_waddr == 0 and last_waddr == 2559):
            print 'WADDR_ERR(%i,%i)' % (last_waddr, this_waddr),
            errors['waddr'] += 1
        if d['maxcnt'][ctr] != last_maxcnt:
            print 'PKT_TIME_ERR'
            errors['packettime'] += 1
        print ''
        last_waddr = this_waddr
        last_pol = this_pol
    # /data loop
    print errors

    recv_error_times = []
    for ctr in range(len(dr['recv'])):
        this_time = dr['time36'][ctr]
        if dr['dv'][ctr] == 0:
            continue
        print '%5i' % ctr,
        for k in dr.keys():
            print '%s(%i)' % (k, dr[k][ctr]),
        if dr['sync'][ctr]:
            print 'SYNC',
        if dr['recv'][ctr] != 3 and dr['dv'][ctr] == 1:
            if this_time not in recv_error_times:
                recv_error_times.append(this_time)
            print 'RECV_ERR',
        print ''
    # /data loop
    print recv_error_times

    matches = []
    for ctr in range(len(d['maxcnt'])):
        this_maxcnt = d['maxcnt'][ctr]
        if this_maxcnt in recv_error_times:
            if this_maxcnt not in matches:
                matches.append(this_maxcnt)
    print matches


def read_reosnap_time():
    d = f.snapshots.reosnap_time_ss.read(man_trig=True)['data']
    lasttime = d['timestamp'][0] - 1
    step_errors = 0
    for ctr in range(len(d['timestamp'])):
        thistime = d['timestamp'][ctr]
        print '%5i %i' % (ctr, thistime),
        if thistime != lasttime + 1:
            print 'ERR(%i)' % (thistime-lasttime),
            step_errors += 1
        print ''
        lasttime = thistime
    print 'Timestep errors:', step_errors


def read_reosnap_unpack():
    d = f.snapshots.unpacksnap_ss.read(man_trig=True)['data']
    overflows = 0
    ramp_errs = 0
    last_val = ((d['d80_2'][0] << 48) + (d['d80_1'][0] << 16) +
                d['d80_0'][0]) - 1
    vals = []
    for ctr in range(len(d['dv'])):
        print '%5i' % ctr,
        for k in d.keys():
            print '%s(%i)' % (k, d[k][ctr]),
        d80 = (d['d80_2'][ctr] << 48) + (d['d80_1'][ctr] << 16) + \
            d['d80_0'][ctr]
        print 'd80(%i)' % d80,
        if d['overflow'][ctr]:
            print 'OVERFLOW',
            overflows += 1
        if d80 != last_val + 1:
            print 'RAMP_ERR',
            ramp_errs += 1
        if d80 in vals:
            raise RuntimeError
        vals.append(d80)
        print ''
        last_val = d80
    print 'Overflows:', overflows
    print 'Ramp errors:', ramp_errs


def read_reosnap_write():
    d = f.snapshots.reosnap_write_ss.read(man_trig=True)['data']
    lastmaxcnt = d['maxcnt'][0] - 1
    last_pkt_start = -1
    for ctr in range(len(d['maxcnt'])):
        print '%5i' % ctr,
        for k in d.keys():
            print '%s(%i)' % (k, d[k][ctr]),
        if d['maxcnt'][ctr] != lastmaxcnt:
            print 'TIME_STEP(%i)' % (d['maxcnt'][ctr] - lastmaxcnt),
            lastmaxcnt = d['maxcnt'][ctr]
            print 'PACKET_LEN(%i)' % (ctr - last_pkt_start),
            last_pkt_start = ctr
        print ''


def read_reosnap_write_inner(man_valid=True):
    d = f.snapshots.reosnap_innerwrite_ss.read(man_trig=True,
                                               man_valid=man_valid)['data']
    lastmaxcnt = d['mcnt'][0] - 1
    last_pkt_start = -1
    for ctr in range(len(d['mcnt'])):
        print '%5i' % ctr,
        for k in d.keys():
            print '%s(%i)' % (k, d[k][ctr]),
        if d['mcnt'][ctr] != lastmaxcnt:
            print 'TIME_STEP(%i)' % (d['mcnt'][ctr] - lastmaxcnt),
            lastmaxcnt = d['mcnt'][ctr]
            print 'PACKET_LEN(%i)' % (ctr - last_pkt_start),
            last_pkt_start = ctr
        print ''


def reset_counters():
    """
    
    :return: 
    """
    f.registers.control.write(cnt_rst='pulse', dbg_rst='pulse')
    f.registers.unpack_control.write(cnt_rst='pulse')


def print_status_regs():
    """
    
    :return: 
    """
    print 'status_barrel:', f.registers.status_barrel.read()['data']
    print 'status_spead0:', f.registers.status_spead0.read()['data']
    print 'status_spead1:', f.registers.status_spead1.read()['data']
    print 'status_reo0:', f.registers.status_reo0.read()['data']
    print 'status_reo1:', f.registers.status_reo1.read()['data']
    print 'unpack_ramp_err:', f.registers.unpack_ramp_err.read()['data']
    print 'unpack_pol0_err:', f.registers.unpack_pol0_err.read()['data']
    print 'unpack_pol1_err:', f.registers.unpack_pol1_err.read()['data']


def read_reorder_snaps(man_valid=False):
    f.registers.control.write(barrelsnap_arm=0, gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0,
                              speadsnap_arm=0, reosnap_arm=0)
    for ctr in range(5):
        f.snapshots['reosnap%i_ss' % ctr].arm(man_valid=man_valid)
    f.registers.control.write(barrelsnap_arm=0, gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0,
                              speadsnap_arm=0, reosnap_arm=1)
    time.sleep(1)
    d = {}
    for ctr in range(5):
        d.update(f.snapshots['reosnap%i_ss' % ctr].read(arm=False)['data'])
    return d


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


def print_reorder_snaps(verbose=False):
    # check the reorder snapshots
    d = read_reorder_snaps()
    last_time = d['timestamp'][0] - 1
    counters = {'time_errors': 0, 'syncs': 0, 'recv_errors': 0}
    for ctr in range(len(d['timestamp'])):
        if verbose:
            print '%6i sync(%i) dv(%i) recv(%i)' % (
                ctr, d['sync'][ctr], d['dv'][ctr], d['recv'][ctr]),
        for dctr in range(4):
            k = 'p1_d%i' % dctr
            if verbose:
                print '%s(%3i)' % (k, d[k][ctr]),
        if verbose:
            print 'timestamp(%10i)' % d['timestamp'][ctr],
        for dctr in range(4):
            k = 'p0_d%i' % dctr
            if verbose:
                print '%s(%3i)' % (k, d[k][ctr]),
        if d['timestamp'][ctr] != last_time:
            if d['timestamp'][ctr] - last_time != 1:
                if verbose:
                    print 'TIME_ERROR'
                counters['time_errors'] += 1
            last_time = d['timestamp'][ctr]
        if d['sync'][ctr] == 1:
            if verbose:
                print 'SYNC',
            counters['syncs'] += 1
        if d['recv'][ctr] != 3:
            if verbose:
                print 'RECV_ERR',
            counters['recv_errors'] += 1
        if verbose:
            print ''
    print counters
    return counters['time_errors'] + counters['recv_errors']


def snap_to_mat():
    """

    :return: 
    """
    rawdata = read_reorder_snaps(True)
    import scipy.io as sio
    import numpy as np
    d32_0 = {ctr: [] for ctr in range(8)}
    d32_1 = {ctr: [] for ctr in range(8)}
    for ctr in range(len(rawdata['p0_d0'])):
        for ctr2 in range(4):
            idx = ctr2 * 2
            d32_0[idx].append(rawdata['p0_d%i' % ctr2][ctr] & (2 ** 32 - 1))
            d32_0[idx + 1].append(rawdata['p0_d%i' % ctr2][ctr] >> 32)
            d32_1[idx].append(rawdata['p1_d%i' % ctr2][ctr] & (2 ** 32 - 1))
            d32_1[idx + 1].append(rawdata['p1_d%i' % ctr2][ctr] >> 32)
    rawdata['recv'] = ([0] * 100) + rawdata['recv']
    rawdata['dv'] = ([0] * 100) + rawdata['dv']
    rawdata['timestamp'] = ([0] * 100) + rawdata['timestamp']
    rawdata['sync'] = ([0] * 100) + rawdata['sync']
    datadict = {}
    for ctr in range(8):
        d32_0[ctr] = ([0] * 100) + d32_0[ctr]
        d32_1[ctr] = ([0] * 100) + d32_1[ctr]
        datadict['simin_p0_d%i' % ctr] = {
            'time': [], 'signals': {
                'dimensions': 1, 'values': np.array(d32_0[ctr], dtype=np.uint32)
            }
        }
        datadict['simin_p1_d%i' % ctr] = {
            'time': [], 'signals': {
                'dimensions': 1, 'values': np.array(d32_1[ctr], dtype=np.uint32)
            }
        }
        datadict['simin_p0_d%i' % ctr]['signals']['values'].shape = \
            (len(d32_0[ctr]), 1)
        datadict['simin_p1_d%i' % ctr]['signals']['values'].shape = \
            (len(d32_1[ctr]), 1)
    for key in ['recv', 'dv', 'timestamp', 'sync']:
        matvar = 'simin_%s' % key
        datadict[matvar] = {
            'time': [], 'signals': {
                'dimensions': 1,
                'values': np.array(rawdata[key], dtype=np.uint32)
            }
        }
        datadict[matvar]['signals']['values'].shape = (len(rawdata[key]), 1)
    sio.savemat('/tmp/spead.mat', datadict)

# print_reorder_snaps()
IPython.embed()

# end
