function [] = auto_jasper_xengs(fftstages)

% The x-engine reference design and the place that the output should go.
reference_model_file = '/home/james/gitrepos/mkat_fpga/source/xeng_wide/s_b64a4x4f.slx';
output_directory = '/home/james/temp/';
% This will compile 8, 16, 32 and 64 antenna versions of the reference design.
% Edit as needed.
antenna_bits_range = [3:6];

fft_stages = str2num(fftstages);
% So because this is running in a function, and not a script directly, you need to push these variables
% to the base environment for the simulink models to read them upon opening.
assignin('base', 'fft_stages', fft_stages)

    for n_bits_ants = antenna_bits_range
        n_bits_xengs = n_bits_ants + 2;

        assignin('base', 'n_bits_ants', n_bits_ants)
        assignin('base', 'n_bits_xengs', n_bits_xengs)

        sprintf('Processing %s with %d fft stages, %d xengine bits and %d antenna bits.', model_file, fft_stages, n_bits_xengs, n_bits_ants)

        open(reference_model_file)
        % Uses new naming convention to have the full number of channels at the end,
        % not just the number of channels per xengine.
        save_system(gcs,sprintf('%ss_b%ia4x%ikf', output_directory, 2^n_bits_ants, floor(2^(fft_stages-1)/1000)))
        jasper_frontend
        save_system % Matlab moans unless you save the design first, otherwise it won't let you close it.
        close_system
    end
exit;
end

