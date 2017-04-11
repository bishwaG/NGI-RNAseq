
#cloud-config
package_upgrade: true
packages:
- nfs-utils
runcmd:
- mkdir -p /mnt/efs
- mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 <EFS_IP_PLACEHOLDER>:/   /mnt/efs
- chown ec2-user:ec2-user /mnt/efs


