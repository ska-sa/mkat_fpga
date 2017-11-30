function x_map = make_x_interleave(num_x, x_per_board)

x_map = zeros(1, num_x);
idx = 1;
for xeng = 0 : x_per_board - 1
    for board = 0 : (num_x / x_per_board) - 1
        val = (board * x_per_board) + xeng;
        % fprintf('%2i - %2i - %2i - %2i\n', xeng, board, idx, val);
        x_map(idx) = val;
        idx = idx + 1;
    end
end

end

% end
