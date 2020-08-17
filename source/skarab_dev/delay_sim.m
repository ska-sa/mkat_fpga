n_bits_fft = 11;

delay_initial = 0.0;
delay_delta = 0.000001; %sample/sample

sampling_rate = 1712000000;
t_acc = sampling_rate/1000; 
n_spectra = floor(t_acc/(2^n_bits_fft))

spec_len = 2^n_bits_fft;

table_size = 2^13; %phase lookups
cos_table = cos(2*pi.*[0:table_size-1]./table_size);
sin_table = sin(2*pi.*[0:table_size-1]./table_size);

%indices for polynomial calculation
x = [-(spec_len/2)/2:1:(spec_len/2)/2-1]/(spec_len/2);

signal = randn(n_spectra*spec_len,1);
fft_signal = fft(reshape(signal, spec_len, n_spectra), spec_len);
padding = randn(floor(delay_initial),1);
padding_signal = [padding; signal];

delay_delta_inc = delay_delta * spec_len;
delays = delay_initial + delay_delta_inc .* [0:n_spectra-1];

signal_cd = zeros(spec_len, n_spectra);
signal_delayed = zeros(spec_len, n_spectra);
phases = zeros(spec_len/2, n_spectra);

for n = 0:n_spectra-1,
	%the delay for this spectrum
	delay = delays(n+1);
	cd = floor(delay);
        %coarse delays
	delay_samples = cd - floor(delay_initial);
	spectrum_cd = padding_signal((n*spec_len)-delay_samples+1:((n+1)*spec_len)-delay_samples, 1);
	signal_cd(:, n+1) = spectrum_cd;
	%fine delays 
	fd = mod(delay, 1);
	slope = -1*fd;
	%reference the delay to the centre of the band	
	offset = mod(cd,4)/2;
	y = x.*slope + offset;
	%convert from fraction to index
	indices = mod(round(y.*table_size/2)+table_size, table_size);
	phases(:, n+1) = complex(cos_table(indices+1), sin_table(indices+1));
end 

spectra_cd = fft(signal_cd, spec_len);
spectra_cd_fd = spectra_cd(1:spec_len/2,:).*phases;

cross_cd = fft_signal(1:spec_len/2,:) .* conj(spectra_cd(1:spec_len/2,:));
cross_cd_fd = fft_signal(1:spec_len/2,:) .* conj(spectra_cd_fd);

%subplot(2,1,1); plot(mod(angle(cross_cd),pi));
%size(cross_cd_fd)
subplot(3,1,1), plot(angle(cross_cd_fd));
subplot(3,1,2), plot(angle(sum(cross_cd_fd,2)));
subplot(3,1,3); plot(20*log10(abs(sum(cross_cd_fd,2))));

