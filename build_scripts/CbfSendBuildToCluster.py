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
args = parser.parse_args()

#Parse Command Line arguments
file_arg = args.file;
ram = args.ram

if(~os.path.isfile(file_arg) == False):
	print("File does not exist")
	sys.exit()

file_path = os.path.abspath(file_arg);
split_index = str.rindex(file_path,'/');

#Setting up directory paths - a bit messy, should be cleaned up
directory = file_path[:split_index]
build_name = file_path[split_index+1:].replace(".slx","")
username = getpass.getuser();

nomad_host = 'dametjie.sdp.kat.ac.za';
sub_directory= "{}_{}_{}".format(time.strftime("%y-%m-%d_%Hh%M"),username,build_name)
destination_folder_move = '/data/cbf_builds/{}/'.format(sub_directory)
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

#Open and transfer documents
def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

print('Opening SSH Connection to shared storage server.')
ssh = createSSHClient('sunstore.sdp.kat.ac.za', 22, 'kat', 'kat')
print('Creating Directories.')
ssh.exec_command('mkdir {}'.format(destination_folder_move[:-1]))

print('Transferring Files to shared storage server')
scp = SCPClient(ssh.get_transport())
scp.put('{}/{}'.format(directory,build_name),remote_path=destination_folder_move,recursive=True)

scp.put('{}/{}.slx'.format(directory,build_name),remote_path=destination_folder_move,recursive=False)

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

#Submit Nomad Job

print('Connecting to Nomad cluster')
#'dametjie.sdp.kat.ac.za'
my_nomad = nomad.Nomad(host=nomad_host)
#[{'source':'http://sunstore.sdp.kat.ac.za/cbf_builds/vivado_image'}]
names = build_name
paths = destination_folder_build[:-1]

nomad_job_name = "{}_{}_build".format(username,names)

print('Submitting Job')
n = names
p = paths
job = {'Job': {'AllAtOnce': None,
  'Constraints': None,
  'CreateIndex': None,
  'Datacenters': [,'capetown'],
  'ID': nomad_job_name,
  'JobModifyIndex': None,
  'Meta': None,
  'ModifyIndex': None,
  'Name': nomad_job_name,
  'Namespace': None,
  'ParameterizedJob': None,
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
    'Name': 'cache',
    'RestartPolicy': {'Attempts': 3,
     'Delay': 25000000000,
     'Interval': 300000000000,
     'Mode': 'delay'},
    'Tasks': [{'Artifacts': [{'GetterSource':'http://sunstore.sdp.kat.ac.za/cbf_builds/vivado_2018p2_image.tar'}],
      'Config': {'load':'vivado_2018p2_image.tar','image': 'vivado:2018p2','mac_address':'18:66:da:56:e1:e5','command':'/bin/bash','volumes':['/sunstore:/sunstore'],'args': ["-c","/home/jasper/build_script.sh -p {}/{}.slx".format(p,n)],'hostname':'jasper'},
      'Constraints': None,
      'DispatchPayload': None,
      'Driver': 'docker',
      'Env': None,
      'KillTimeout': None,
      'LogConfig': None,
      'Meta': None,
      'Name': 'build_fpg',
      'Resources': {'CPU': 25000,
       'DiskMB': 5000,
       'IOPS': None,
       'MemoryMB': ram},
      'ShutdownDelay': 0,
      'Templates': None,
      'User': '',
      'Vault': None}],
    'Constraints':[
      {'LTarget':'${meta.has_sunstore}','RTarget':'true','Operand':'=',}],
    'Update': None}],
  'Type': 'batch',
  'VaultToken': None,
  'Version': None}}

print job['Job']['TaskGroups'][0]['Tasks'][0]['Config']['args']

response = my_nomad.job.register_job(nomad_job_name, job)

print 'Job submitted go to: {}:4646/ui/jobs/{} to view progress'.format(nomad_host,nomad_job_name)
