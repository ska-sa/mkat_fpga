function map = make_read_map(num_chans, num_x)

% num_chans = 4096;
parallel_freqs = 8;
num_hmc = 2;
% num_x = 16;
x_per_board = 4;
output_len = 256;
output_len = 16;

% do not edit below this line

x_map = make_x_interleave(num_x, x_per_board)
spectrum_step = num_chans / (parallel_freqs * num_hmc)
chans_per_x = spectrum_step / num_x

map = zeros(1, (num_chans / (parallel_freqs * num_hmc)) * output_len);
idx = 1;
for xchan = 0 : chans_per_x - 1
    for hmc = 1 : num_hmc
        for xeng = 0 : length(x_map) - 1
            xidx = x_map(xeng + 1);
            xfreq = (xidx * chans_per_x) + xchan;
            %fprintf('%i - %i - %i\n', xchan, xidx, xfreq);
            for accum = 0 : output_len - 1
                val = xfreq + (accum * spectrum_step);
                map(idx) = val;
                idx = idx + 1;
            end
        end
    end
end

% simin_addr_mat.signals.values = map.';
% simin_addr_mat.signals.dimensions = 1;
% simin_addr_mat.time = [];
% assignin('base', 'simin_addr_mat', simin_addr_mat);

return
