% names = {'dv', 'tag', 'sync', 'd0', 'err_wrdata_repeat', 'hmc_dv', ...
%     'wr_en', 'd1', 'hmc_d0_0', 'hmc_tag', 'rd_en', 'wr_rdy', ...
%     'd4', 'hmc_d0_1', 'init_done', 'rd_rdy', 'err_dvblock', 'hmc_d0_2', ...
%     'post_okay', 'rd_tag', 'err_pktlen', 'hmc_d0_3_lsb', 'rd_addr', ...
%     'wr_addr', 'err_wrdata_d4zero', 'hmc_d0_3_msb', 'rd_addr_raw', ...
%     'wr_addr_raw', 'rd_arm'};
names = who;
for names_ctr = 1 : length(names)
    name = names{names_ctr};
    res = strfind(name, 'simin_');
    if isempty(res)
%         fprintf(['not searching: ', name, '\n']);
        continue
    end
    if res(1) ~= 1
%         fprintf(['simin_ isn''t at the beginning: ', name, '\n']);
        continue
    end
%     fprintf([name,'.signals.dimensions = 1;\n']);
    evalin('base', [name,'.signals.dimensions = 1;'])
end
clear names names_ctr res name;
% end
