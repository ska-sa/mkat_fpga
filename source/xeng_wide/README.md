# MATLAB variables required for opening and compiling xeng_wide designs:

### n_bits_ants
2^this number of antennas, i.e. 2 for a 4-antenna correlator, 3 for 8-antenna, and so forth.

### n_bits_xengs
In the wideband case, four xengs per antenna, this number is n_bits_ants+2.


### fft_stages 
2^this number of channels. 11 for a 1k, 13 for a 4k, 16 for a 32k.
