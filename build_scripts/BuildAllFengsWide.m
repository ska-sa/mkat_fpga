%Author: Gareth Callanan

clear all
warning off
pass = input('Insert password to be used for secure copy to epyc01.sdp.kat.ac.za: ','s');

script_dir = fileparts(mfilename('fullpath'));
cd(strcat(script_dir,'/../source/feng_wide'))
x_eng_dir = pwd();

xeng_clk = 225;
x_bits_max=8;
n_bits_cd=17;
xengbits=8;
output_bits=8;

sys_names=[string('s_c856m32k.slx'),string('s_c856m4k.slx'),string('s_c856m1k.slx')];
fft_stages_arr=[16,13,11];

for i = 1:length(sys_names) 
    fft_stages=fft_stages_arr(i);
    name = sys_names(i);
    open_system(name);
    save_system(bdroot,name);
    jasper_frontend;
    system(['python ',script_dir,'/CbfSendBuildToCluster.py -r 55000 -u 756991046 -i ',x_eng_dir,'/',name{1},' --pass ',pass])
    close_system(bdroot,0)
end

warning on