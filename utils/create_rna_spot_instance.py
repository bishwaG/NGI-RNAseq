#! /usr/bin/env python

import argparse
import base64
import getpass
import json
import logging
import os
import pip
import socket
import time

SCILIFELAB_IMAGE_NAME = "Current scilifelab/ngi-rnaseq"
SSH_GROUP_NAME = "NGI-RNA SSH"
EFS_NAME = "NGI-RNA EFS"

USAGE ="""
USAGE:
python create_rna_spot_instance.py -p <SPOT_PRICE> -c <CONFIGURATION> -u <USER_CONFIGURATION> -i <INSTANCE_TYPE> -l <LOGFILE> -k <KEYNAME>

-p, --price : SPOT_PRICE : required. The price in dollars of your highest bid for the spot instance. With everthing default, a good price is around 1$
-c, --launch-specification :CONFIGURATION : file containing the launch specification of the spot instance (https://boto3.readthedocs.io/en/latest/reference/services/ec2.html#EC2.Client.request_spot_instances)
-u, --user-data : USER_CONFIGURATION : file containing the user_data specification to start your instance with. Default is "mount_rna_efs.sh", it takes care of mounting the EFS file system.
-i, --instance-type : INSTANCE-TYPE : the code for the type of instance requested. By default, m4.2xlarge.
-l, --log : LOGFILE : file to send logs to. By default, logs are sent to stderr. Will make the script quiet, other than the warning. 
-k, --key-pair : KEYPAIR: ec2 keypair name to use.


-c overrides defaults, other options override -c.
"""

class NGI_RNA_Setup():

    def __init__(self, args):
        import boto3
        self.args = args
        self.log = self.log_setup()
        self.conf = {}
        self.efs_ip = None
        self.client = boto3.client('ec2')
        self.ec2 = boto3.resource('ec2')
        self.efs_client = boto3.client('efs')
        self.session = boto3.session.Session()
        self.region = self.session.region_name
        self.subnet_id = self.get_subnet_id()

    def log_setup(self):
        log = logging.getLogger('rna_logger')
        log.setLevel(level=logging.INFO)
        if not self.args.log:
            mfh = logging.StreamHandler()
        else:
            mfh = logging.FileHandler(args.log)
        info_template = '%(asctime)s : %(message)s'
        mft = logging.Formatter(info_template)
        mfh.setFormatter(mft)
        log.addHandler(mfh)
        return log

    def make_keypair(self):
        self.log.info("Going to use key '{}'.".format(self.keyname))
        try:
            response = self.client.describe_key_pairs(KeyNames=[self.keyname])
        except :
            self.log.info("Key not found, creating it.")
            response = self.client.create_key_pair(KeyName=self.keyname)
            with open("{}.pem".format(self.keyname), "w") as kf:
                kf.write(response["KeyMaterial"])
            os.chmod("{}.pem".format(self.keyname),0600)


    def generate_defaults(self):
        if "InstanceType" not in self.conf:
            if self.args.instance_type:
                self.conf["InstanceType"] = self.args.instance_type
            else:
                self.conf["InstanceType"] = 'm4.2xlarge'

        if "KeyName" not in self.conf:
            if self.args.key_pair:
                self.conf['KeyName'] = self.args.key_pair
                self.keyname = self.args.key_pair
            else:
                user = getpass.getuser()
                hostname = socket.gethostname()
                keyname = "NGI-RNA_{}@{}".format(user, hostname)
                self.keyname = keyname
                self.conf["KeyName"] = self.keyname
                self.make_keypair()

        if "ImageId" not in self.conf:
            image_id = self.find_scilifelab_image_id()
            self.conf["ImageId"] = image_id

        if "UserData" not in self.conf or self.args.user_data:
            if self.args.user_data:
                user_data = self.generate_user_data(self.args.user_data)
                self.conf["UserData"] = user_data
            else:
                user_data = self.generate_user_data('mount_rna_efs.sh')
                self.conf["UserData"] = user_data

        if "SubnetId" not in self.conf:
            self.conf["SubnetId"] = self.subnet_id

        if "SecurityGroupIds" not in self.conf:
            security_groups = self.get_security_groups()
            self.conf["SecurityGroupIds"] = security_groups

        if "InstanceType" not in self.conf:
            self.conf["InstanceType"] = self.args.instance_type

    def get_subnet_id(self):
        self.log.info("Getting subnet id for region '{}'...".format(self.region))
        response = self.client.describe_subnets()
        return response['Subnets'][0]["SubnetId"]

    def find_scilifelab_image_id(self):
        self.log.info("Getting '{}' ami id...".format(SCILIFELAB_IMAGE_NAME))
        my_filter = {'Name': 'name', 'Values' : [SCILIFELAB_IMAGE_NAME]}
        response = self.client.describe_images(Filters=[my_filter])
        self.log.info("Found '{}'".format(response['Images'][0]['ImageId']))
        return response['Images'][0]['ImageId']

    def generate_user_data(self, datafile):
        self.log.info("Preparing user data '{}'".format(datafile))
        with open(datafile, "r") as ud:
            data = ud.read()
            if self.efs_ip and "<EFS_IP_PLACEHOLDER>" in data:
                data = data.replace("<EFS_IP_PLACEHOLDER>", self.efs_ip)
            user_data = base64.b64encode(data)
        return user_data

    def load_configuration(self):
        self.log.info("Opening configuration '{}'".format(self.args.conf))
        with open(self.args.conf, "r") as cf:
            json_conf = json.load(cf)
        return json_conf

    def get_security_groups(self):
        security_groups = []
        response = self.client.describe_security_groups()
        for sec_gr in response["SecurityGroups"]:
            if sec_gr['GroupName'] in ["default", SSH_GROUP_NAME]:
                self.log.info("Adding security group '{}'".format(sec_gr['GroupName']))
                security_groups.append(sec_gr["GroupId"])

        if len(security_groups) == 1:
            self.log.info("Creating security group '{}'".format(SSH_GROUP_NAME))
            response = self.client.create_security_group(GroupName=SSH_GROUP_NAME, Description="SSH rules for the NGI_RNA pipeline")
            security_groups.append(response["GroupId"])
            response = self.client.authorize_security_group_ingress(GroupId=response["GroupId"], IpProtocol='tcp', FromPort=22, ToPort=22, CidrIp="0.0.0.0/0")

        return security_groups

    def find_efs_ip(self):
        efs_id = None
        self.log.info("Looking for EFS '{}'".format(EFS_NAME))
        response = self.efs_client.describe_file_systems()
        for efs in response["FileSystems"]:
            if efs["Name"] == EFS_NAME:
                efs_id = efs['FileSystemId'] 
                response = self.efs_client.describe_mount_targets(FileSystemId=efs_id)
                for target in response['MountTargets']:
                    if target['SubnetId'] == self.subnet_id:
                        return target['IpAddress']

                efs_ip = self.create_efs_mount_target(efs_id)
                return efs_ip

        if not efs_id:
            self.log.info("EFS '{}' not found, creating it.".format(EFS_NAME))
            response = self.efs_client.create_file_system(CreationToken="{} creation token".format(EFS_NAME))
            efs_id = response['FileSystemId']
            tags = [{"Key":"Name","Value": EFS_NAME}]
            self.efs_client.create_tags(FileSystemId=efs_id, Tags=tags)
            response = self.efs_client.describe_file_systems(FileSystemId=efs_id)
            while response["FileSystems"][0]['LifeCycleState'] == 'creating':
                time.sleep(5)
                response = self.efs_client.describe_file_systems(FileSystemId=efs_id)

            efs_ip = self.create_efs_mount_target(efs_id)
            return efs_ip

    def create_efs_mount_target(self, efs_id):
            self.log.info("EFS '{}' created. Creating Mount Target. (Long)".format(EFS_NAME))
            self.efs_client.create_mount_target(FileSystemId=efs_id, SubnetId=self.subnet_id, SecurityGroups=self.get_security_groups())
            response = self.efs_client.describe_mount_targets(FileSystemId=efs_id)
            while response["MountTargets"][0]['LifeCycleState'] == 'creating':
                time.sleep(5)
                response = self.efs_client.describe_mount_targets(FileSystemId=efs_id)
            self.log.info("Mount Target for '{}' created.".format(EFS_NAME))
            return response["MountTargets"][0]['IpAddress']

    def main(self):
        if self.args.conf:
            self.conf = self.load_configuration()

        self.efs_ip = self.find_efs_ip()
        self.generate_defaults()
        self.log.info("Sending request...")
        response = self.client.request_spot_instances(SpotPrice=args.price, InstanceCount=1, LaunchSpecification=self.conf)
        req_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']

        request_granted = False
        self.log.info("Waiting for an answer...")
        while not request_granted:
            response = self.client.describe_spot_instance_requests(SpotInstanceRequestIds=[req_id])
            if response['SpotInstanceRequests'][0]['Status']['Code'] == 'fulfilled':
                request_granted = True
                instance_id = response['SpotInstanceRequests'][0]['InstanceId']
                self.log.info("Spot request fulfilled")
            else:
                time.sleep(5)

        response = self.client.describe_instances(InstanceIds=[instance_id])
        dns_name = response['Reservations'][0]['Instances'][0]['PublicDnsName']
        instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']

        self.log.info("Instance is created, waiting for it to run...")
        instance = self.ec2.Instance(instance_id)
        instance.wait_until_running()
        self.log.info("Instance is running, waiting on initialization... (Very long)")
        status = "not ok"
        while not status == "ok":
            response = self.client.describe_instance_status(InstanceIds=[instance_id])
            status = response['InstanceStatuses'][0]['SystemStatus']['Status']
            time.sleep(5)


        self.log.info("Machine ready")
        self.log.info("ssh -i \"{}.pem\" ec2-user@{}".format(self.keyname, dns_name))

def first_setup():
    pip.main(['install', 'boto3'])
    print "\n\n###################################################################"
    print "This is the setup for creating an Amazon EC2 instance to run Scilifelab's NGI-RNAseq pipeline (https://github.com/SciLifeLab/NGI-RNAseq)."
    print "Note that Scilifelab does not take ownership of the machines created by this script. By using this script, YOU will be charged by Amazon according to the parameters provided."
    print "###################################################################"
    region = raw_input( "Please enter the region you wish to use (Currently, only 'eu-west-1' is supported.) :  ")
    if not os.path.exists(os.path.expanduser("~/.aws")):
        os.mkdir(os.path.expanduser("~/.aws"))
    with open(os.path.expanduser("~/.aws/config"), "w") as cf:
        cf.write("[default]\n")
        cf.write("output = text\n")
        cf.write("region = {}\n".format(region))

    print "Next, we'll need your amazon credentials. Navigate to your IAM console (https://console.aws.amazon.com/iam/home?region={}), create an individual IAM user.".format(region)
    print "Tick  'programmatic access', then 'Permissions'"
    print"There, select 'AmazonEC2FullAccess' and 'AmazonElasticFileSystemFullAccess'."
    i = raw_input("Press 'Review' and 'Create User'. Copy the 'Access key ID' and the 'Secret access key'. Press Enter when this is done.")
    access_key = raw_input("Please enter your AWS access key ID:  ")
    secret_key = raw_input("Please enter your AWS secret key :  ")
    with open(os.path.expanduser("~/.aws/credentials"), "w") as cf:
        cf.write("[default]\n")
        cf.write("aws_access_key_id = {}\n".format(access_key))
        cf.write("aws_secret_access_key = {}\n".format(secret_key))

    print "###################################################################"
    print "The configuration files have been created in '<HOME>/.aws'."
    print "###################################################################\n\n"
    import boto3
    from botocore.exceptions import ClientError
    client = boto3.client('ec2')
    try:
        client.describe_instances(DryRun=True)
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print "It looks like the EC2 permissions have not been set."
            print "Please log in IAM (https://console.aws.amazon.com/iam/home?region={}), click your user, then 'Add permissions', 'Attach exising policies directly', and tick 'AmazonEC2FullAccess' and 'AmazonElasticFileSystemFullAccess'. Then click 'Review', and finally, 'Add permissions'.".format(region)
            i = raw_input("Press enter when this is done")

    client = boto3.client('efs')
    try:
        client.describe_file_systems()
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDeniedException':
            print "It looks like the EFS permissions have not been set."
            print "Please log in IAM (https://console.aws.amazon.com/iam/home?region={}), click your user, then 'Add permissions', 'Attach exising policies directly', and tick 'AmazonEC2FullAccess' and 'AmazonElasticFileSystemFullAccess'. Then click 'Review', and finally, 'Add permissions'.".format(region)
            i = raw_input("Press enter when this is done")




    print "All is set, here is how to use this script : "
    print USAGE


if __name__ == "__main__":
    if not (os.path.exists(os.path.expanduser("~/.aws/config")) and os.path.exists(os.path.expanduser("~/.aws/credentials"))):
        first_setup()
    else:
        ap = argparse.ArgumentParser(usage=USAGE)
        ap.add_argument("-p", "--spot-price", dest="price", required=True)
        ap.add_argument("-c", "--launch-specification", dest="conf")
        ap.add_argument("-u", "--user-data", dest="user_data")
        ap.add_argument("-l", "--log", dest="log")
        ap.add_argument("-i", "--instance-type", dest="instance_type")
        ap.add_argument("-k", "--key-pair", dest="key_pair")
        args = ap.parse_args()

        instance = NGI_RNA_Setup(args)
        instance.main()
