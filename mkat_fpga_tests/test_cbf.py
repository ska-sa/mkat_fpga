from __future__ import division

import threading
import unittest
import logging
import Queue
import copy
import time
import itertools

import numpy as np

import spead64_48 as spead

from katcp.testutils import start_thread_with_cleanup
from corr2.dsimhost_fpga import FpgaDsimHost

from mkat_fpga_tests import correlator_fixture

LOGGER = logging.getLogger(__name__)

class CorrRx(threading.Thread):
    """Run a spead receiver in a thread; provide a Queue.Queue interface

    Places each received valid data dump (i.e. contains xeng_raw values) as a pyspead
    ItemGroup into the `data_queue` attribute. If the Queue is full, the newer dumps will
    be discarded.

    """
    def __init__(self, port=8888, queue_size=3, log_handler=None,
                 log_level=logging.INFO, spead_log_level=logging.INFO):
        self.logger = LOGGER
        spead.logging.getLogger().setLevel(spead_log_level)
        self.quit_event = threading.Event()
        self.data_queue = Queue.Queue(maxsize=queue_size)
        "Queue for received ItemGroups"
        self.running_event = threading.Event()
        self.data_port = port
        """UDP port to listen at for UDP data. Cannot be changed after start()"""
        threading.Thread.__init__(self)

    def stop(self):
        self.quit_event.set()
        if hasattr(self, 'rx') and self.rx.is_running():
            self.rx.stop()
            self.logger.info("SPEAD receiver stopped")

    def start(self, timeout=None):
        threading.Thread.start(self)
        if timeout is not None:
            self.running_event.wait(timeout)

    def run(self, acc_scale=True):
        logger = self.logger
        logger.info('Data reception on port %i.' % self.data_port)
        self.rx = rx = spead.TransportUDPrx(
            self.data_port, pkt_count=1024, buffer_size=51200000)
        self.running_event.set()

        try:
            ig = spead.ItemGroup()
            idx = -1
            dump_size = 0
            datasets = {}
            datasets_index = {}
            # we need these bits of meta data before being able to assemble and transmit
            # signal display data

            meta_required = ['n_chans', 'bandwidth', 'n_bls', 'n_xengs',
                             'center_freq', 'bls_ordering', 'n_accs']
            meta = {}
            for heap in spead.iterheaps(rx):
                idx += 1
                ig.update(heap)
                logger.debug('PROCESSING HEAP idx(%i) cnt(%i) @ %.4f' % (
                    idx, heap.heap_cnt, time.time()))
                # output item values specified

                try:
                    xeng_raw = ig.get_item('xeng_raw')
                except KeyError:
                    xeng_raw = None
                if xeng_raw is None:
                    logger.info('Skipping heap {} since no xeng_raw was found'.format(idx))
                    continue

                if xeng_raw.has_changed():
                    try:
                        self.data_queue.put_nowait(copy.deepcopy(ig))
                    except Queue.Full:
                        logger.info('Data Queue full, disposing of heap {}.'.format(idx))
                xeng_raw.unset_changed()

                # should we quit?
                if self.quit_event.is_set():
                    logger.info('Got a signal from main(), exiting rx loop...')
                    break

            rx.stop()
            logger.info("SPEAD receiver stopped")
        finally:
            self.quit_event.clear()
            self.running_event.clear()

    def get_clean_dump(self, dump_timeout=None):
        """Discard any queued dumps, discard one more, then return the next dump"""
        # discard any existing queued dumps -- they may be from another test
        try:
            while True:
                self.data_queue.get_nowait()
        except Queue.Empty:
            pass

        # discard next dump too, in case
        LOGGER.info('Discarding first dump:')
        self.data_queue.get(timeout=dump_timeout)
        LOGGER.info('Waiting for a clean dump:')
        return self.data_queue.get(timeout=dump_timeout)



def get_vacc_offset(xeng_raw):
    """Assuming a tone was only put into input 0, figure out if VACC is roated by 1"""
    b0 = np.abs(complexize(xeng_raw[:,0]))
    b1 = np.abs(complexize(xeng_raw[:,1]))
    if np.max(b0) > 0 and np.max(b1) == 0:
        # We expect autocorr in baseline 0 to be nonzero if the vacc is properly aligned,
        # hence no offset
        return 0
    elif np.max(b1) > 0 and np.max(b0) == 0:
        return 1
    else:
        raise ValueError('Could not determine VACC offset')

def complexize(input_data):
    """Convert input data shape (X,2) to complex shape (X)"""
    return input_data[:,0] + input_data[:,1]*1j

class test_CBF(unittest.TestCase):
    def setUp(self):
        self.receiver = CorrRx(port=8888)
        start_thread_with_cleanup(self, self.receiver, start_timeout=1)
        self.correlator = correlator_fixture.correlator
        self.corr_fix = correlator_fixture
        # Make sure the x-engines are not yet dumping
        self.corr_fix.stop_x_data()
        dsim_conf = self.correlator.configd['dsimengine']
        dig_host = dsim_conf['host']
        self.dhost = FpgaDsimHost(dig_host, config=dsim_conf)
        self.dhost.get_system_information()
        # Increase the dump rate so tests can run faster
        self.correlator.xeng_set_acc_time(0.2)

    # TODO 2015-05-27 (NM) Do test using get_vacc_offset(test_dump['xeng_raw']) to see if
    # the VACC is rotated. Run this test first so that we know immediately that other
    # tests will be b0rked.

    def test_channelisation(self):
        cconfig = self.correlator.configd
        n_chans = int(cconfig['fengine']['n_chans'])
        BW = float(cconfig['fengine']['bandwidth'])
        delta_f = BW / n_chans
        f_start = 0. # Center freq of the first bin
        chan_freqs = f_start + np.arange(n_chans)*delta_f

        test_chan = 1500
        expected_fc = f_start + delta_f*test_chan

        self.dhost.sine_sources.sin_0.set(frequency=expected_fc, scale=0.25)
        # The signal source is going to quantise the requested freqency, so see what we
        # actually got
        source_fc = self.dhost.sine_sources.sin_0.frequency
        self.dhost.sine_sources.sin_1.set(frequency=expected_fc, scale=0)
        self.dhost.sine_sources.sin_corr.set(frequency=expected_fc, scale=0)
        self.dhost.noise_sources.noise_0.set(scale=0.0)
        self.dhost.noise_sources.noise_1.set(scale=0)
        self.dhost.noise_sources.noise_corr.register.write(scale=0)
        self.dhost.outputs.out_0.select_output('signal')
        self.dhost.outputs.out_1.select_output('signal')
        self.dhost.outputs.out_0.scale_output(0.5)
        self.dhost.outputs.out_1.scale_output(0.5)

        self.corr_fix.issue_metadata()
        self.addCleanup(self.corr_fix.stop_x_data)
        self.corr_fix.start_x_data()

        full_range = 2**31      # Max range of the integers coming out of VACC
        def get_mag(dump, baseline):
            xrd = dump['xeng_raw']
            b = complexize(xrd[:,baseline,:])
            b_mag = np.abs(b)/full_range
            return b_mag

        def loggerize(data, dynamic_range=70):
            log_data = 10*np.log10(data)
            max_log = np.max(log_data)
            min_log_clip = max_log - dynamic_range
            log_data[log_data < min_log_clip] = min_log_clip
            return log_data

        # Get baseline 0 data, i.e. auto-corr of m000h
        test_baseline = 0
        dump_timeout = 10
        test_dump = self.receiver.get_clean_dump(dump_timeout)
        b_mag = get_mag(test_dump, baseline=test_baseline)
        # find channel with max power
        max_chan = np.argmax(b_mag)
        self.assertEqual(max_chan, test_chan,
                         'Channel with max power is not the test channel')

        # Place frequency samples spaced 0.1 of a channel-width over the central 80% of
        # the channel (assuming nr_freq_samples == 9)
        nr_freq_samples = 9
        # TODO 2015-05-27 (NM) This should be from -0.4 to 0.4, but the current dsim
        # doesn't have enough resolution to place a sample sufficiently close to -0.4
        # without going outside the range
        desired_chan_test_freqs = expected_fc + delta_f*np.linspace(
            -0.35, 0.35, nr_freq_samples)
        # Placeholder of actual frequencies that the signal generator produces
        signal_chan_test_freqs = np.zeros_like(desired_chan_test_freqs)
        # Channel magnitude responses for each frequency
        chan_responses = np.zeros((nr_freq_samples, n_chans))
        for i, freq in enumerate(desired_chan_test_freqs):
            LOGGER.info('Getting channel response for freq {}/{}: {} MHz.'.format(
                i+1, len(desired_chan_test_freqs), freq/1e6))
            if freq == expected_fc:
                # We've already done this one!
                this_source_freq = source_fc
                this_freq_result = b_mag
            else:
                self.dhost.sine_sources.sin_0.set(frequency=freq, scale=0.125)
                this_source_freq = self.dhost.sine_sources.sin_0.frequency
                this_freq_dump = self.receiver.get_clean_dump(dump_timeout)
                this_freq_response = get_mag(this_freq_dump, baseline=test_baseline)
            signal_chan_test_freqs[i] = this_source_freq
            chan_responses[i] = this_freq_response
        self.corr_fix.stop_x_data()
        for i, freq in enumerate(desired_chan_test_freqs):
            max_chan = np.argmax(chan_responses[i])
            self.assertEqual(max_chan, test_chan, 'Source freq {} peak not in channel '
                             '{} as expected but in {}.'
                             .format(signal_chan_test_freqs[i], test_chan, max_chan))
        self.assertLess(np.max(chan_responses[:, test_chan]), 0.99,
                        'VACC output at > 99% of maximum value, indicates that '
                        'something, somewhere, is probably overranging.')
        max_chan_response = np.max(10*np.log10(chan_responses[:, test_chan]))
        min_chan_response = np.min(10*np.log10(chan_responses[:, test_chan]))
        chan_ripple = max_chan_response - min_chan_response
        acceptable_ripple_lt = 0.3
        self.assertLess(chan_ripple, acceptable_ripple_lt,
                        'ripple {} dB within 80% of channel fc >= {} dB'
                        .format(chan_ripple, acceptable_ripple_lt))

        # from matplotlib import pyplot
        # colour_cycle = 'rgbyk'
        # style_cycle = ['-', '--']
        # linestyles = itertools.cycle(itertools.product(style_cycle, colour_cycle))
        # for i, freq in enumerate(desired_chan_test_freqs):
        #     style, colour = linestyles.next()
        #     pyplot.plot(loggerize(chan_responses[i], dynamic_range=60), color=colour, ls=style)
        # pyplot.ion()
        # pyplot.show()
        # import IPython ; IPython.embed()
