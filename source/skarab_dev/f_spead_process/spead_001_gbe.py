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

FPG = '/home/paulp/bofs/spead_test_gbe_2017-5-5_1420.fpg'

logging.basicConfig(level=logging.INFO)

if os.environ['CORR2UUT'].strip() == '':
    print 'CORR2UUT environment variables not found.'
    sys.exit(0)

f = skarab_fpga.SkarabFpga(os.environ['CORR2UUT'])
f.get_system_information(FPG)

if f.gbes[0].get_port() != 30000:
    f.gbes[0].set_port(30000)


def read_gbe_snaps():
    f.registers.control.write(gbesnap_arm=0,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0,)
    f.snapshots.rxsnap0_ss.arm()
    f.snapshots.rxsnap1_ss.arm()
    f.snapshots.rxsnap2_ss.arm()
    f.registers.control.write(gbesnap_arm=1,
                              gbesnap_wesel=0, gbesnap_we=0,
                              gbesnap_trigsel=0, gbesnap_trig=0, )
    time.sleep(1)
    d0 = f.snapshots.rxsnap0_ss.read(arm=False)['data']
    d1 = f.snapshots.rxsnap1_ss.read(arm=False)['data']
    d2 = f.snapshots.rxsnap2_ss.read(arm=False)['data']
    for ctr in range(len(d2['eof'])):
        if ((d2['eof'][ctr] == 0) and (d2['rawdv'][ctr] != 15)) or (
                    (d2['eof'][ctr] == 1) and (d2['rawdv'][ctr] != 1)):
            print 'DV_ERROR(%i,%i,%i)' % (ctr, d2['rawdv'][ctr],
                                          d2['eof'][ctr]),
    return d0, d1, d2


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

# read the data straight out of the 40gbe core
d0, d1, d2 = read_gbe_snaps()

ips = []
ports = []
destips = []
destports = []
for ctr in range(len(d2['port'])):
    if d2['port'][ctr] not in ports:
        ports.append(d2['port'][ctr])
    if d2['ip'][ctr] not in ips:
        ips.append(d2['ip'][ctr])
    if d2['destip'][ctr] not in destips:
        destips.append(d2['destip'][ctr])
    if d2['destport'][ctr] not in destports:
        destports.append(d2['destport'][ctr])

print 'IPS:',
for ip in ips:
    print str(tengbe.IpAddress(ip)),
print ''
print 'PORTS:', ports
print 'DEST_IPS:',
for ip in destips:
    print str(tengbe.IpAddress(ip)),
print ''
print 'DEST_PORTS:', destports

# interleave the four 64-bit words
d0.update(d1)
d0.update(d2)
d64 = []
eofs = []
for ctr in range(len(d0['d0'])):
    if d0['eof'][ctr] == 1:
        d64.append(d0['d3'][ctr])
        eofs.append(1)
    else:
        d64.append(d0['d3'][ctr])
        d64.append(d0['d2'][ctr])
        d64.append(d0['d1'][ctr])
        d64.append(d0['d0'][ctr])
        eofs.extend([0, 0, 0, 0])
d = {'data': d64, 'eof': eofs}
del d1, d2, d0

# break it up into packetses and process SPEAD data
gbe_packets = caspersnap.Snap.packetise_snapdata(d, 'eof')
spead_processor = casperspead.SpeadProcessor()
spead_processor.process_data(gbe_packets)

# check the packets for the ramp
if check_ramps(spead_processor.packets) > 0:
    IPython.embed()

sys.exit(0)

# end
