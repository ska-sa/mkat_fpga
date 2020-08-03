Description:
-----------
This document describes how to use the CbfSendBuildToCluster.py file to launch a CASPER backend build on a remote nomad cluster.
NOTE: Frontend must still be run on the local machine. This script only launches the backend component of the toolflow

Requirements:
-----------
In order to use this script the the following python packages need to be installed:
1. python-nomad
2. scp
3. paramiko
The packages can be installed by running 'pip install -r requirements.txt' from the mkat_fpga/build_scripts directory

IMPORTANT NOTE: If you are running MATLAB in a virtual environment, activate the virtual environment and then run 'pip install -r requirements.txt'

Directions:
-----------
To submit a single build to the cluster:
1. Run jasper_frontend on the .slx file from Matlab
2. Run the following command in the terminal: "python CbfSendBuildToCluster.py -r <ram> -i <slx_file_location>". <ram> must be replaced with the amount of ram required in MB(for 10GB of ram type 10000). <slx_file_location> must be the location of the slx file - can be absolute or relative. The CbfSendBuildToCluster.py is located in the mkat_fpga/build_scripts directory.
3. You will be required to enter a password to copy data to the ceph storage cluster
4. Once this script has run it should provide a link to a site that allows you to monitor the job.

To access files produced by the job:
1. log into a machine that is part of the nomad cluster: ssh kat@epyc01.sdp.kat.ac.za will do the trick
2. Navigate to /shared-brp/cbf_builds/
2. Seach for a folder with the same name as your submitted job.
3. This folder has the simulink slx file used for the build. It also contains all files produced when running the CASPER toolflow

To submit groups of builds, there are four matlab scripts located in the mkat_fpga/build_scripts directory: BuildAllXengsWide.m, BuildAllXengsNarrow.m, BuildAllFengsWide.m, BuildAllFengsNarrow.m, their names describe exactly what they do. In order to execute one of these scripts, do the following:
1. Open matlab using mlib_devels startsg script
2. Open the script you want to run
3. Run the script
4. Type in the password required to transmit data to the ceph cluster when prompted
5. The script should then do the rest
