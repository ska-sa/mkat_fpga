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

FPG = '/home/paulp/bofs/spead_test_barrel_2017-5-5_1425.fpg'

logging.basicConfig(level=logging.INFO)

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = skarab_fpga.SkarabFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

if f.gbes[0].get_port() != 30000:
    f.gbes[0].set_port(30000)


def read_barrel_snaps(man_valid=False):
    f.registers.control.write(barrelsnap_arm=0, gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0,)
    f.snapshots.barrelsnap0_ss.arm(man_valid=man_valid)
    f.snapshots.barrelsnap1_ss.arm(man_valid=man_valid)
    f.snapshots.barrelsnap2_ss.arm(man_valid=man_valid)
    f.registers.control.write(barrelsnap_arm=1, gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0, )
    time.sleep(1)
    d0 = f.snapshots.barrelsnap0_ss.read(arm=False)['data']
    d1 = f.snapshots.barrelsnap1_ss.read(arm=False)['data']
    d2 = f.snapshots.barrelsnap2_ss.read(arm=False)['data']
    d0.update(d1)
    d0.update(d2)
    return d0


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

# # # save the output of the barrelsnaps to matlab .mat files
# # rawdata = read_barrel_snaps(True)
# # import scipy.io as sio
# # import numpy as np
# # d32 = {ctr: [] for ctr in range(8)}
# # for ctr in range(len(rawdata['d0'])):
# #     d32[0].append(rawdata['d3'][ctr] & (2 ** 32 - 1))
# #     d32[1].append(rawdata['d3'][ctr] >> 32)
# #     d32[2].append(rawdata['d2'][ctr] & (2 ** 32 - 1))
# #     d32[3].append(rawdata['d2'][ctr] >> 32)
# #     d32[4].append(rawdata['d1'][ctr] & (2 ** 32 - 1))
# #     d32[5].append(rawdata['d1'][ctr] >> 32)
# #     d32[6].append(rawdata['d0'][ctr] & (2 ** 32 - 1))
# #     d32[7].append(rawdata['d0'][ctr] >> 32)
# # for ctr in range(8):
# #     d32[ctr] = ([0] * 100) + d32[ctr]
# # rawdata['eof'] = ([0] * 100) + rawdata['eof']
# # rawdata['we'] = ([0] * 100) + rawdata['we']
# # datadict = {
# #     'simin_d%i' % ctr: {
# #         'time': [], 'signals': {
# #             'dimensions': 1, 'values': np.array(d32[ctr], dtype=np.uint32)
# #         }
# #     } for ctr in range(8)
# # }
# # for ctr in range(8):
# #     datadict['simin_d%i' % ctr]['signals']['values'].shape = \
# #         (len(rawdata['d0']) + 100, 1)
# # datadict['simin_dv'] = {
# #     'time': [], 'signals': {
# #         'dimensions': 1, 'values': np.array(rawdata['we'], dtype=np.uint32)
# #     }
# # }
# # datadict['simin_dv']['signals']['values'].shape = (len(rawdata['d0']) + 100, 1)
# # datadict['simin_eof'] = {
# #     'time': [], 'signals': {
# #         'dimensions': 1, 'values': np.array(rawdata['eof'], dtype=np.uint32)
# #     }
# # }
# # datadict['simin_eof']['signals']['values'].shape = (len(rawdata['d0']) + 100, 1)
# # sio.savemat('/tmp/mat.mat', datadict)
# # sys.exit(0)

# now check the barrel snaps
rawdata = read_barrel_snaps()
d64 = []
eofs = []
for ctr in range(len(rawdata['d0'])):
    d64.append(rawdata['d3'][ctr])
    d64.append(rawdata['d2'][ctr])
    d64.append(rawdata['d1'][ctr])
    d64.append(rawdata['d0'][ctr])
    if rawdata['eof'][ctr] == 1:
        eofs.extend([0, 0, 0, 1])
    else:
        eofs.extend([0, 0, 0, 0])
d = {'data': d64, 'eof': eofs}

# break it up into packetses and process SPEAD data
try:
    gbe_packets = caspersnap.Snap.packetise_snapdata(d, 'eof')
    spead_processor = casperspead.SpeadProcessor()
    spead_processor.process_data(gbe_packets)
    if check_ramps(spead_processor.packets):
        IPython.embed()
except Exception as exc:
    print exc.message
    IPython.embed()

IPython.embed()

# end
