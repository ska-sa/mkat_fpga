%Author: Gareth Callanan

clear all
warning off
pass = input('Insert password to be used for secure copy to epyc01.sdp.kat.ac.za: ','s');

script_dir = fileparts(mfilename('fullpath'));
cd(strcat(script_dir,'/../source/feng_nb'))
x_eng_dir = pwd();

output_bits=8;
output_len_bits= 8;
n_taps=4; %This will eventually become part of a top level mask but it is necessary for now.
xengbits = 4; %Normaly set to 8, I have no idea if this affects anything

sys_names=[string('s_c_nbe_m32k.slx')];
fft_stages_arr=[16];

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
