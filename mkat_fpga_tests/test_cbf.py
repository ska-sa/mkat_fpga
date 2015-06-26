from __future__ import division

import unittest
import logging

import time
import itertools

import numpy as np

from katcp.testutils import start_thread_with_cleanup
from corr2.dsimhost_fpga import FpgaDsimHost
from corr2.corr_rx import CorrRx

from mkat_fpga_tests import correlator_fixture
from mkat_fpga_tests.utils import normalised_magnitude, loggerise, complexise
from mkat_fpga_tests.utils import init_dsim_sources
from mkat_fpga_tests.utils import nonzero_baselines, zero_baselines, all_nonzero_baselines

LOGGER = logging.getLogger(__name__)

DUMP_TIMEOUT = 10              # How long to wait for a correlator dump to arrive in tests

def get_vacc_offset(xeng_raw):
    """Assuming a tone was only put into input 0, figure out if VACC is roated by 1"""
    b0 = np.abs(complexise(xeng_raw[:,0]))
    b1 = np.abs(complexise(xeng_raw[:,1]))
    if np.max(b0) > 0 and np.max(b1) == 0:
        # We expect autocorr in baseline 0 to be nonzero if the vacc is properly aligned,
        # hence no offset
        return 0
    elif np.max(b1) > 0 and np.max(b0) == 0:
        return 1
    else:
        raise ValueError('Could not determine VACC offset')

class test_CBF(unittest.TestCase):
    def setUp(self):
        self.receiver = CorrRx(port=8888)
        start_thread_with_cleanup(self, self.receiver, start_timeout=1)
        self.correlator = correlator_fixture.correlator
        self.corr_fix = correlator_fixture
        dsim_conf = self.correlator.configd['dsimengine']
        dig_host = dsim_conf['host']
        self.dhost = FpgaDsimHost(dig_host, config=dsim_conf)
        self.dhost.get_system_information()
        # Increase the dump rate so tests can run faster
        self.correlator.xeng_set_acc_time(0.2)
        self.corr_fix.issue_metadata()
        self.addCleanup(self.corr_fix.stop_x_data)
        self.corr_fix.start_x_data()


    # TODO 2015-05-27 (NM) Do test using get_vacc_offset(test_dump['xeng_raw']) to see if
    # the VACC is rotated. Run this test first so that we know immediately that other
    # tests will be b0rked.

    def test_channelisation(self):
        """TP.C.1.19 CBF Channelisation Wideband Coarse L-band"""
        cconfig = self.correlator.configd
        n_chans = int(cconfig['fengine']['n_chans'])
        BW = float(cconfig['fengine']['bandwidth'])
        delta_f = BW / n_chans
        f_start = 0. # Center freq of the first bin
        chan_freqs = f_start + np.arange(n_chans)*delta_f

        test_chan = 1500
        expected_fc = f_start + delta_f*test_chan

        init_dsim_sources(self.dhost)
        self.dhost.sine_sources.sin_0.set(frequency=expected_fc, scale=0.25)
        # The signal source is going to quantise the requested freqency, so see what we
        # actually got
        source_fc = self.dhost.sine_sources.sin_0.frequency

        # Get baseline 0 data, i.e. auto-corr of m000h
        test_baseline = 0
        test_data = self.receiver.get_clean_dump(DUMP_TIMEOUT)['xeng_raw']
        b_mag = normalised_magnitude(test_data[:, test_baseline, :])
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
                this_freq_data = self.receiver.get_clean_dump(DUMP_TIMEOUT)['xeng_raw']
                this_freq_response = normalised_magnitude(
                    this_freq_data[:, test_baseline, :])
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
                        'ripple {} dB within 80% of channel fc is >= {} dB'
                        .format(chan_ripple, acceptable_ripple_lt))

        # from matplotlib import pyplot
        # colour_cycle = 'rgbyk'
        # style_cycle = ['-', '--']
        # linestyles = itertools.cycle(itertools.product(style_cycle, colour_cycle))
        # for i, freq in enumerate(desired_chan_test_freqs):
        #     style, colour = linestyles.next()
        #     pyplot.plot(loggerise(chan_responses[i], dynamic_range=60), color=colour, ls=style)
        # pyplot.ion()
        # pyplot.show()
        # import IPython ; IPython.embed()

    def test_product_baselines(self):
        """CBF Baseline Correlation Products: VR.C.19, TP.C.1.3"""

        init_dsim_sources(self.dhost)
        # Put some correlated noise on both outputs
        self.dhost.noise_sources.noise_corr.set(scale=0.5)
        test_dump = self.receiver.get_clean_dump(DUMP_TIMEOUT)

        # Get list of all the correlator input labels
        input_labels = sorted(tuple(test_dump['input_labelling'][:,0]))
        # Get list of all the baselines present in the correlator output
        present_baselines = sorted(
            set(tuple(bl) for bl in test_dump['bls_ordering']))

        # Make a list of all possible baselines (including redundant baselines) for the
        # given list of inputs
        possible_baselines = set()
        for li in input_labels:
            for lj in input_labels:
                possible_baselines.add((li, lj))

        test_bl = sorted(list(possible_baselines))
        # Test that each baseline (or its reverse-order counterpart) is present in the
        # correlator output
        baseline_is_present = {}

        for test_bl in possible_baselines:
           baseline_is_present[test_bl] = (test_bl in present_baselines or
                                           test_bl[::-1] in present_baselines)
        self.assertTrue(all(baseline_is_present.values()),
                        "Not all baselines are present in correlator output.")

        test_data = test_dump['xeng_raw']
        # Expect all baselines and all channels to be non-zero
        self.assertFalse(zero_baselines(test_data))
        self.assertEqual(nonzero_baselines(test_data),
                         all_nonzero_baselines(test_data))

        # Save initial f-engine equalisations
        initial_equalisations = {input: eq_info['eq'] for input, eq_info
                                in self.correlator.feng_eq_get().items()}
        def restore_initial_equalisations():
            for input, eq in initial_equalisations.items():
                self.correlator.feng_eq_set(source_name=input, new_eq=eq)
        self.addCleanup(restore_initial_equalisations)

        # Set all inputs to zero, and check that output product is all-zero
        for input in input_labels:
            self.correlator.feng_eq_set(source_name=input, new_eq=0)
        test_data = self.receiver.get_clean_dump(DUMP_TIMEOUT)['xeng_raw']
        self.assertFalse(nonzero_baselines(test_data))
        #-----------------------------------
        all_inputs = sorted(set(input_labels))
        zero_inputs = set(input_labels)
        nonzero_inputs = set()

        def calc_zero_and_nonzero_baselines(nonzero_inputs):
            nonzeros = set()
            zeros = set()
            for inp_i in all_inputs:
                for inp_j in all_inputs:
                    if inp_i in nonzero_inputs and inp_j in nonzero_inputs:
                        nonzeros.add((inp_i, inp_j))
                    else:
                        zeros.add((inp_i, inp_j))
            return zeros, nonzeros

        #zero_baseline, nonzero_baseline = calc_zero_and_nonzero_baselines(nonzero_inputs)
        def print_baselines():
            print ('zeros: {}\n\nnonzeros: {}\n\nnonzero-baselines: {}\n\n '
                'zero-baselines: {}\n\n'.format(
                    sorted(zero_inputs), sorted(nonzero_inputs),
                    sorted(nonzero_baseline), sorted(zero_baseline)))
        #print_baselines()
        for inp in input_labels:
            old_eqs = initial_equalisations[inp]
            self.correlator.feng_eq_set(source_name=inp, new_eq=old_eqs)
            zero_inputs.remove(inp)
            nonzero_inputs.add(inp)
            #zero_baseline, nonzero_baseline = calc_zero_and_nonzero_baselines(nonzero_inputs)
            #print_baselines()
        #print self.correlator.feng_eq_get().items()
