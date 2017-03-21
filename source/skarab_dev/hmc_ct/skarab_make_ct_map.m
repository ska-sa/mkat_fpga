function map = skarab_make_ct_map(n_chans, output_vector_length, num_x, x_per_host)

parallel_freqs = 8;
map = zeros(1, n_chans * output_vector_length / parallel_freqs);

% % this gives us a straight map
% for fctr = 0 : freq_chans / parallel_freqs - 1
%     read_vec = fctr : freq_chans / parallel_freqs : freq_chans / parallel_freqs * output_vector_length - 1;
%     start_index = fctr * output_vector_length;
%     stop_index = start_index + output_vector_length;
%     map(start_index + 1 : stop_index) = read_vec;
% end

% % interleaved across x-engines
% NOT DONE YET

% interleaved across x-engines and x-hosts
f_per_x = n_chans / num_x;
w_per_x = f_per_x / parallel_freqs;
f_words = n_chans / parallel_freqs;
x_indices = reshape(reshape(0:num_x-1, x_per_host, num_x/x_per_host).', 1, num_x);
% for xeng = 0 : num_x - 1
%     fstart = f_per_x * xeng;
%     fend = fstart + f_per_x - 1;
%     fstart_words = fstart / parallel_freqs;
%     fend_words = fstart_words + w_per_x - 1;
%     fprintf('xeng_%02i: (%i,%i) (%i,%i)\n', xeng, fstart, fend, fstart_words, fend_words);
% end
for wctr = 0 : w_per_x - 1
%     fprintf('wordset %02i:\n', wctr);
    read_vec = (0 : output_vector_length-1) * f_words;
    for xctr = 0 : num_x - 1
        xindex = x_indices(xctr + 1);
        word_start = ((f_per_x * xindex) / parallel_freqs) + wctr;
        read_indices = word_start + read_vec;
        mapindex = output_vector_length * ((wctr * num_x) + xctr);
%         fprintf('\txeng_%02i=>%02i: %s @ %i\n', xctr, xindex, num2str(read_indices), mapindex);
        map(mapindex + 1 : mapindex + output_vector_length) = read_indices;
    end
end

%logstr = sprintf('x%i_%i: %s', xctr, fctr, num2str(addrs));
    
fprintf('\n');

end

