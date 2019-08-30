#Author: Gareth Callanan

import paramiko
from scp import SCPClient
import time
import os
import getpass
import nomad
import argparse
import sys

#Command Line Arguments
parser = argparse.ArgumentParser(
    description='Send CASPER toolflow build to cluster for building.\nNote: jasper_frontend needs to have already been run',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '-i', '--input_file', dest='file', action='store', required=True,
    help='Project to build')
parser.add_argument(
    '-r', '--RAM', dest='ram', action='store', required=True,type=int,
    help='Requred RAM(MB)')
parser.add_argument(
    '-u', '--UID', dest='uid', action='store', required=False,type=int,
    help='Telegram chat ID. Speak to Gareth to get this to work. Will Send')
args = parser.parse_args()

#Parse Command Line arguments
file_arg = args.file;
ram = args.ram

if(~os.path.isfile(file_arg) == False):
	print("File does not exist")
	sys.exit()

file_path = os.path.abspath(file_arg);
split_index = str.rindex(file_path,'/');

storage_password = raw_input("Insert password for kat@epyc01.sdp.kat.ac.za:\n")

#Setting up directory paths - a bit messy, should be cleaned up
directory = file_path[:split_index]
build_name = file_path[split_index+1:].replace(".slx","")
username = getpass.getuser();
timestamp = time.strftime("%y-%m-%d_%Hh%M");

nomad_host = 'dametjie.sdp.kat.ac.za';
sub_directory= "{}_{}_{}".format(timestamp,username,build_name)
destination_folder_move = '/shared-brp/cbf_builds/{}/'.format(sub_directory)
destination_folder_build = '/sunstore/cbf_builds/{}/'.format(sub_directory)

#Rename Files that need to be renamed

print('Replacing file paths.')
replace_from = directory
replace_to = destination_folder_build[:-1]

for dname, dirs, files in os.walk("{}/{}".format(directory,build_name)):
    for fname in files:
        fpath = os.path.join(dname, fname)
        with open(fpath) as f:
            s = f.read()
        s = s.replace(replace_from, replace_to)
        with open(fpath, "w") as f:
            f.write(s)

#Open connection and transfer documents
def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

failed = False
try:
	print('Opening SSH Connection to shared storage server.')
	ssh = createSSHClient('epyc01.sdp.kat.ac.za', 22, 'kat', storage_password)
	print('Creating Directories.')
	ssh.exec_command('mkdir {}'.format(destination_folder_move[:-1]))

	print('Transferring Files to shared storage server')
	scp = SCPClient(ssh.get_transport())
	scp.put('{}/{}'.format(directory,build_name),remote_path=destination_folder_move,recursive=True)

	scp.put('{}/{}.slx'.format(directory,build_name),remote_path=destination_folder_move,recursive=False)
except Exception as e:
	print 'Error copying data to sunstore: '+repr(e)
	failed = True

#Rename files back
print('Restoring current directory back to its default state.')
for dname, dirs, files in os.walk("{}/{}".format(directory,build_name)):
    for fname in files:
        fpath = os.path.join(dname, fname)
        with open(fpath) as f:
            s = f.read()
        s = s.replace(replace_to, replace_from)
        with open(fpath, "w") as f:
            f.write(s)

if(failed):
	print("Copy to sunstore failed. Exiting...")
	sys.exit(1)

#Submit Nomad Job

print('Connecting to Nomad cluster')
#'dametjie.sdp.kat.ac.za'
my_nomad = nomad.Nomad(host=nomad_host)
#[{'source':'http://sunstore.sdp.kat.ac.za/cbf_builds/vivado_image'}]
names = build_name
paths = destination_folder_build[:-1]

nomad_job_name_to_display = "{}_{}_{}_build".format(timestamp,username,names)
nomad_job_name="cbf_jobs"

print('Submitting Job')
n = names
p = paths
job = {'Job': {'AllAtOnce': None,
  'Constraints': None,
  'CreateIndex': None,
  'Datacenters': ['brp0'],
  'ID': "{}".format(nomad_job_name),
  'JobModifyIndex': None,
  'Meta': {"submit_date":"{}".format(timestamp),"department":"cbf",'user':username,'resource_location':destination_folder_build},
  'ModifyIndex': None,
  'Name': 'cbf_jobs',
  'Namespace': None,
  'ParameterizedJob': {
    'Payload': 'optional',
    'MetaRequired': [
      'file_path'
     ],
     'MetaOptional': ['uid'],},
  'ParentID': None,
  'Payload': None,
  'Periodic': None,
  'Priority': None,
  'Region': None,
  'Stable': None,
  'Status': None,
  'StatusDescription': None,
  'Stop': None,
  'SubmitTime': None,
  'TaskGroups': [{'Constraints': None,
    'Count': 1,
    'Meta': None,
    'Name': nomad_job_name_to_display,
    'RestartPolicy': {'Attempts': 3,
     'Delay': 25000000000,
     'Interval': 300000000000,
     'Mode': 'delay'},
    'Tasks': [{'Artifacts': None,
      'Config': {'image': 'harbor.sdp.kat.ac.za:443/cbf/vivado:2019p1','network_mode':'host','command':'/bin/bash','volumes':['/shared-brp:/sunstore'],'args': ["-c","/home/jasper/build_script.sh -p ${NOMAD_META_FILE_PATH}.slx -u ${NOMAD_META_UID}"]},
      'Constraints': None,
      'DispatchPayload': None,
      'Driver': 'docker',
      'Env': None,
      'KillTimeout': None,
      'LogConfig': None,
      'Meta': {"CPU_CORES":"${attr.cpu.numcores}","CPU_FREQUENCY":"${attr.cpu.frequency}"},
      'Name': nomad_job_name_to_display,
      'Resources': {'CPU': 20000,
       'IOPS': None,
       'MemoryMB': ram},
      'ShutdownDelay': 0,
      'Templates': None,
      'User': '',
      'Vault': None}],
    'Constraints':[
       {'LTarget':'${node.unique.name}','RTarget':'epyc01','Operand':'=',},
       {'LTarget':'${meta.has_sunstore}','RTarget':'true','Operand':'=',}],
      #{'LTarget':'${attr.cpu.frequency}','RTarget':'2500','Operand':'>=',}],
      #{'LTarget':'${attr.cpu.numcores}','RTarget':'16','Operand':'>=',}],
    'Update': None}],
  'Type': 'batch',
  'VaultToken': None,
  'Version': None}}

print job['Job']['TaskGroups'][0]['Tasks'][0]['Config']['args']

response = my_nomad.job.register_job(nomad_job_name, job)
response = my_nomad.job.dispatch_job(nomad_job_name, meta = {"file_path":"{}/{}".format(p,n),'uid':"756991046"})

print 'Job submitted go to: http://{}:4646/ui/jobs/{} to view progress'.format(nomad_host,response['DispatchedJobID'].replace("/","%2F"))


