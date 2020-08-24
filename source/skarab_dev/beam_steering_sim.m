% proposal is to implement phase correction by having a base phase
% value for the first frequency, and a phase update to be applied
% for each frequency after that

fft_chans = 2^15; 
fringe_offset = 0.125; %samples
delay = 0.5; %samples
lookup_table_size = 1024; 

signal = randn(1, fft_chans);
signal_fft = fft(signal, fft_chans);

%current solution
indices = [-0.5:1/fft_chans:0.5-1/fft_chans];
lookup_table = exp(j*2*pi*([-(lookup_table_size/2):lookup_table_size/2-1]/lookup_table_size));

phase = ((-1*delay)*indices) + fringe_offset;
table_indices = mod(round(phase*lookup_table_size/2)+lookup_table_size/2, lookup_table_size);
phase_slope = lookup_table(table_indices+1);
%apply delay slope
signal_fft_delayed = signal_fft .* phase_slope;

%proposed solution
initial_phase = delay/2+fringe_offset;
rotator_init = exp(j*pi*initial_phase);
phase_increment = delay/fft_chans;
rotator_inc = exp(-j*pi*phase_increment);
rotators = zeros(1, fft_chans);
rotator = rotator_init;
for n = 1:fft_chans,
    rotator = rotator * rotator_inc;
    rotators(n) = rotator;
end
%apply delay slope
signal_fft_delayed_new = signal_fft.*rotators;    

% Phase error sources;
% * initial phase error on input data
% * initial base rotator value error 
% * initial phase increment value error accumulated
% * rotator value error accumulated 
% * final phase error on output data
% Assuming rounding, maximum error is half an LSB

xengs = 16; %maximum error occurs with maximum channels per xengine

%input data from feng
input_bits = 8;
max_input_error_bits = 1/((2^input_bits)+1);
max_input_error_phase = abs(360/(2*pi)*angle(exp(-j*max_input_error_bits)));

%phase accumulator
phase_acc_init_bits = 16; %input resolution
max_phase_acc_init_error_bits = 1/((2^phase_acc_init_bits)+1);
max_phase_acc_init_error_phase = abs(360/(2*pi)*angle(exp(-j*max_phase_acc_init_error_bits)));
phase_acc_bits = 18; %phase accumulator resolution
max_phase_acc_error_bits = 1/((2^phase_acc_bits)+1);
max_phase_acc_error_phase = abs(360/(2*pi)*angle(exp(-j*max_phase_acc_error_bits)));

%phase increment
phase_inc_bits = 16; %input resolution
max_phase_inc_error_bits = 1/((2^phase_inc_bits)+1);
max_phase_inc_error_phase = abs(360/(2*pi)*angle(exp(-j*max_phase_inc_error_bits)));

%output data
output_bits = 8;
max_output_error_bits = 1/((2^output_bits)+1);
max_output_error_phase = abs(360/(2*pi)*angle(exp(-j*max_output_error_bits)));

chans_per_xeng = fft_chans/xengs;
%integrated phase error due to accumulated initial phase error in phase increment value
max_phase_acc_error_phase_inc = chans_per_xeng * max_phase_inc_error_phase;

%integrated phase error due to accumulated phase error in phase accumulator
max_phase_acc_error_phase_acc = chans_per_xeng * max_phase_acc_error_phase;

%maximum theoretical phase error
max_phase_error_worst = max_input_error_phase + max_phase_acc_init_error_phase + max_phase_acc_error_phase_acc + max_phase_acc_error_phase_inc + max_output_error_phase;

heading = sprintf('Current vs proposed delay correction techniques\n(delay: %2.1f samples, fringe offset: %1.3f samples)', delay, fringe_offset);
plot((180/pi)*angle(signal_fft_delayed.*conj(signal_fft)),'-');
hold on;
plot((180/pi)*angle(signal_fft_delayed_new.*conj(signal_fft)),':');
legend({'current','proposed'});
xlabel('channel');
ylabel('phase (degrees)');
title(heading); 
text(50,20,sprintf('Worst case theoretical error = %2.1f degrees,\n with %d channels and %d xengines', max_phase_error_worst, fft_chans, xengs));

