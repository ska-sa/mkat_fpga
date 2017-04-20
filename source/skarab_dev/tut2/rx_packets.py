#!/usr/bin/env python

"""
Read incoming packets from the Tutorial 2 transmitter and check them for
consistency.
"""

import struct
import socket
import argparse


def unpack_word256(word):
    """
    
    :param word: 
    :return: 
    """
    mark = word[12]
    walkm = (word[13] << 32) | (word[14] << 16) | (word[15] << 0)
    pktcntm = (word[8] << 16) | (word[9] << 0)
    rampm = (word[10] << 16) | (word[11] << 0)
    walkl = (word[4] << 48) | (word[5] << 32) | (word[6] << 16) | \
                (word[7] << 0)
    pktcntl = (word[0] << 16) | (word[1] << 0)
    rampl = (word[2] << 16) | (word[3] << 0)
    return mark, walkm, walkl, pktcntm, pktcntl, rampm, rampl


parser = argparse.ArgumentParser(
    description='SKARAB Tutorial 2 - analyse packets from TX SKARAB',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--port', dest='port', type=int, action='store',
                    default=7779,
                    help='Port to which TX FPGA is sending data.')
parser.add_argument('--num', dest='numpkts', type=int, action='store',
                    default=100,
                    help='How many packets should we process?')
parser.add_argument('-q', '--quiet', dest='quiet', action='store_true',
                    default=False, help='Only print error summary.')
parser.add_argument('--loglevel', dest='log_level', action='store',
                    default='INFO', help='log level to use, default None, '
                                         'options INFO, DEBUG, ERROR')
args = parser.parse_args()

# open a RX socket and bind to the port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(1)
sock.bind(('', args.port))
# receive a bunch of packets and save them in a list
pkts = []
try:
    for ctr in range(args.numpkts):
        pkts.append(sock.recvfrom(10000))
except socket.timeout:
    raise RuntimeError('ERROR: socket timed out waiting for '
                       'packets from TX FPGA.')
finally:
    sock.close()

# analyse the data we have received
last_pkt_count = None
last_ramp = 0
last_walk = None
pkt_ctr = 0
errors = {
    'pkt_count_match': 0,
    'pkt_count_progression': 0,
    'pkt_count_internal': 0,
    'ramp_match': 0,
    'ramp_progression': 0,
    'walk_match': 0,
    'walk_progression': 0,
    'marker': 0,
    'pkt_format': 0,
}
for pkt in pkts:
    d = struct.unpack('>%iH' % (len(pkt[0]) / 2), pkt[0])
    this_pkt_cnt = (d[0] << 16) | (d[1] << 0)
    pktstr = '------------------------- pkt_%03i ' \
             '------------------------- ' % pkt_ctr
    if last_pkt_count is None:
        last_pkt_count = this_pkt_cnt - 1
    if this_pkt_cnt != last_pkt_count + 1:
        pktstr += 'PKTCNT_ERROR\n'
        errors['pkt_count_progression'] += 1
    else:
        pktstr += '\n'
    pkt_count_l = -1
    for ctr in range(0, len(d), 16):
        try:
            marker, walking_m, walking_l, pkt_count_m, pkt_count_l, \
                ramp_m, ramp_l = unpack_word256(d[ctr:ctr+16])
            if last_walk is None:
                last_walk = walking_l / 2
            pktstr += '%4i%25i%10i%10i ' % (marker, walking_l,
                                            pkt_count_l, ramp_l)
            # check for errors
            if marker != 7777:
                pktstr += 'MARKER_ERROR '
                errors['marker'] += 1
            if (walking_l & (2**48-1)) != walking_m:
                errors['walk_match'] += 1
                pktstr += 'WALKING_MATCH_ERROR '
            if pkt_count_m != pkt_count_l:
                errors['pkt_count_match'] += 1
                pktstr += 'PKTCNT_MATCH_ERROR '
            if ramp_m != ramp_l:
                errors['ramp_match'] += 1
                pktstr += 'RAMP_MATCH_ERROR '
            if walking_l != last_walk * 2:
                if not ((walking_l == 2) and (last_walk == 2**63)):
                    errors['walk_progression'] += 1
                    pktstr += 'WALKING_ERROR '
            if ramp_l != last_ramp + 1:
                errors['ramp_progression'] += 1
                pktstr += 'RAMP_ERROR '
            if pkt_count_l != this_pkt_cnt:
                errors['pkt_count_internal'] += 1
                pktstr += 'PKTCNT_ERR2 '
            last_walk = walking_l
            last_ramp = ramp_l
        except IndexError:
            errors['pkt_format'] += 1
        if not args.quiet:
            print(pktstr)
        pktstr = ''
    last_pkt_count = pkt_count_l
    last_ramp = 0
    pkt_ctr += 1

print('-------------------------\nERRORS:')
for key, val in errors.items():
    print('\t%s: %i' % (key, val))

# end
