%Author: Gareth Callanan

clear all
warning off
pass = input('Insert password to be used for secure copy to epyc01.sdp.kat.ac.za: ','s');

script_dir = fileparts(mfilename('fullpath'));
cd(strcat(script_dir,'/../source/xeng_wide'))
x_eng_dir = pwd();

xeng_clk = 225;
x_bits_max=8;
n_bits_cd=17;
xengbits=8;
output_bits=8;

% sys_names=[string('s_b4a4x32kf.slx'),string('s_b4a4x4kf.slx'),string('s_b4a4x1kf.slx')];
% x_eng_bits_arr=[4,4,4];
% n_ants_bits_arr=[2,2,2];
% fft_stages_arr=[16,13,11];
% 
% for i = 1:length(sys_names) 
%     n_bits_xengs=x_eng_bits_arr(i);
%     n_bits_ants =n_ants_bits_arr(i);
%     fft_stages=fft_stages_arr(i);
%     name = sys_names(i);
%     open_system(name);
%     save_system(bdroot,name);
%     jasper_frontend;
%     system(['python ',script_dir,'/CbfSendBuildToCluster.py -r 55000 -u 756991046 -i ',x_eng_dir,'/',name{1},' --pass ',pass])
%     close_system(bdroot,0)
% end

sys_names=[string('s_b64a4x32kf.slx'),string('s_b64a4x4kf.slx'),string('s_b64a4x1kf.slx'),string('s_b32a4x32kf.slx'),string('s_b32a4x4kf.slx'),string('s_b32a4x1kf.slx'),string('s_b16a4x32kf.slx'),string('s_b16a4x4kf.slx'),string('s_b16a4x1kf.slx'),string('s_b8a4x32kf.slx'),string('s_b8a4x4kf.slx'),string('s_b8a4x1kf.slx')];
x_eng_bits_arr=[8,8,8,7,7,7,6,6,6,5,5,5];
n_ants_bits_arr=[6,6,6,5,5,5,4,4,4,3,3,3,];
fft_stages_arr=[16,13,11,16,13,11,16,13,11,16,13,11];


for i = 1:length(sys_names)
    n_bits_xengs=x_eng_bits_arr(i);
    n_bits_ants =n_ants_bits_arr(i);
    fft_stages=fft_stages_arr(i);
    name = sys_names(i);
    open_system("s_b64a4x32kf.slx");
    save_system(bdroot,name);
    jasper_frontend
    system(['python ',script_dir,'/CbfSendBuildToCluster.py -r 55000 -u 756991046 -i ',x_eng_dir,'/',name{1},' --pass ',pass])
    close_system(bdroot,0)
end

warning on
