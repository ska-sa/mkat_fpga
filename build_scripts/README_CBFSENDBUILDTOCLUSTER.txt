Descritpion:
-----------
This document describes how to use the CbfSendBuildToCluster.py file to launch a CASPER backend build on a remote nomad cluster.
NOTE: Frontend must still be run on the local machine. This script only launches the backend component of the toolflow

Requirements:
-----------
In order to use this script the the following python packages need to be installed:
	1. python-nomad
	2. scp
	3. paramiko

Directions:
-----------
To submit a job to the cluster:
	1. Run jasper_frontend on the .slx file from Matlab
	2. Run the following command in the terminal: "python CbfSendBuildToCluster.py -r <ram> -i <slx_file_location>". <ram> must be replaced with the amount of ram required in MB(for 10GB of ram type 10000). <slx_file_location> must be the location of the slx file - can be absolute or relative
	3. Once this script has run it should provide a link to a site that allows you to monitor the job. This allows you to skip step 1 and 2 of the "To monitor a job instructions below"

To monitor a job:
	1. Navigate to "dametjie.sdp.kat.ac.za:4646" in a browser
	2. In the search for job section, type either your username or the slx file name. A job with both of these details and a timestamp should be found.
	3. Click on this job
	4. Somewhere in the page that displays is a way to access the log files and the resource use. Explore at your own convenience

To access files produced by the job:
	1. Navigate to "http://sunstore.sdp.kat.ac.za/cbf_builds/" in your browser
	2. Seach for a folder with the same name as your submitted job.
	3. This folder has the simulink slx file used for the build. It also contains all files produced when running the CASPER toolflow
