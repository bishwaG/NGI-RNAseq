# This script is used to create a working environment on an amazon machine.
# We strongly recommend to use an already-made ami, as the build time is fairly high.


PATH=$PATH:/usr/local/bin
export PATH

#Install nextflow-related stuff
yum update -y
yum install -y nfs-utils
yum install -y cloud-init
yum install -y java-1.8.0
yum remove -y java-1.7.0-openjdk
yum install -y readline-devel.x86_64
yum install -y gcc 
yum install -y git
yum install -y make
yum install -y zlib-devel.x86_64
yum install -y python27.x86_64
yum install -y openssl-devel.x86_64
yum install -y ncurses-devel.x86_64
yum install -y gcc48-gfortran.x86_64
yum install -y gcc48.x86_64
yum install -y gcc48-c++.x86_64
yum install -y xz-devel.x86_64
yum install -y libcurl-devel.x86_64
yum install -y gsl-devel.x86_64
yum install -y libXt-devel.x86_64
yum install -y libX11-devel.x86_64
yum install -y docker
usermod -a -G docker ec2-user
service docker restart

pip install --upgrade pip

#Install nextflow
cd /opt
curl -fsSL get.nextflow.io | bash
chmod 777 /opt/nextflow
ln -s /opt/nextflow /usr/local/bin/nextflow
chown ec2-user /usr/local/bin/nextflow
echo -e "PATH=$PATH:/usr/local/bin" >> /etc/environment
cd -

#Install Fastqc
wget -O /opt/fastqc_v0.11.5.zip http://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.11.5.zip
unzip /opt/fastqc_v0.11.5.zip -d /opt/
chmod 755 /opt/FastQC/fastqc
ln -s /opt/FastQC/fastqc /usr/local/bin/fastqc
rm /opt/fastqc_v0.11.5.zip

# Install bedops
mkdir /opt/bedops 
wget -q -O /opt/bedops_linux_x86_64-v2.4.20.v2.tar.bz2 https://github.com/bedops/bedops/releases/download/v2.4.20/bedops_linux_x86_64-v2.4.20.v2.tar.bz2
tar xvjf /opt/bedops_linux_x86_64-v2.4.20.v2.tar.bz2 -C /opt/bedops\
ln -s /opt/bedops/bin/* /usr/local/bin/
rm /opt/bedops_linux_x86_64-v2.4.20.v2.tar.bz2

#Install cutadapt
/usr/local/bin/pip install cutadapt


#Install TrimGalore
mkdir /opt/TrimGalore
wget -q -O /opt/TrimGalore/trim_galore_v0.4.2.zip http://www.bioinformatics.babraham.ac.uk/projects/trim_galore/trim_galore_v0.4.2.zip
unzip /opt/TrimGalore/trim_galore_v0.4.2.zip -d /opt/TrimGalore
ln -s /opt/TrimGalore/trim_galore /usr/local/bin/trim_galore
rm /opt/TrimGalore/trim_galore_v0.4.2.zip


#Install STAR
git clone https://github.com/alexdobin/STAR.git /opt/STAR
ln -s /opt/STAR/bin/Linux_x86_64/STAR /usr/local/bin/STAR
ln -s /opt/STAR/bin/Linux_x86_64/STARlong /usr/local/bin/STARlong


#Install RSeQC
/usr/local/bin/pip install RSeQC


#Install SAMTools
wget -q -O /opt/samtools-1.3.1.tar.bz2 https://github.com/samtools/samtools/releases/download/1.3.1/samtools-1.3.1.tar.bz2
tar xvjf /opt/samtools-1.3.1.tar.bz2 -C /opt/
cd /opt/samtools-1.3.1;make;make install
rm /opt/samtools-1.3.1.tar.bz2 


#Install PreSeq
wget -q -O /opt/preseq_linux_v2.0.tar.bz2 http://smithlabresearch.org/downloads/preseq_linux_v2.0.tar.bz2
tar xvjf /opt/preseq_linux_v2.0.tar.bz2 -C /opt/
ln -s /opt/preseq_v2.0/preseq /usr/local/bin/preseq
ln -s /opt/preseq_v2.0/bam2mr /usr/local/bin/bam2mr
rm /opt/preseq_linux_v2.0.tar.bz2


#Install PicardTools
wget -q -O /opt/picard-tools-2.0.1.zip https://github.com/broadinstitute/picard/releases/download/2.0.1/picard-tools-2.0.1.zip
unzip /opt/picard-tools-2.0.1.zip -d /opt/
rm /opt/picard-tools-2.0.1.zip
echo -e "PICARD_HOME=/opt/picard-tools-2.0.1" >> /etc/environment
source /etc/environment


#Install R
wget -q -O /opt/R-3.2.3.tar.gz https://cran.r-project.org/src/base/R-3/R-3.2.3.tar.gz
tar xvzf /opt/R-3.2.3.tar.gz -C /opt/
cd /opt/R-3.2.3;./configure;make;make install
rm /opt/R-3.2.3.tar.gz 


#Install R packages
echo 'source("https://bioconductor.org/biocLite.R")' > /opt/packages.r
echo 'biocLite()' >> /opt/packages.r
echo 'biocLite(c("Rsubread", "dupRadar", "limma", "lattice", "locfit", "edgeR", "chron", "data.table", "gtools", "gdata", "bitops", "caTools", "gplots", "markdown"))' >> /opt/packages.r
Rscript /opt/packages.r
mkdir /usr/local/lib64/R/site-library


#Install featureCounts
wget -q -O /opt/subread-1.5.1-Linux-x86_64.tar.gz http://downloads.sourceforge.net/project/subread/subread-1.5.1/subread-1.5.1-Linux-x86_64.tar.gz
tar xvzf /opt/subread-1.5.1-Linux-x86_64.tar.gz -C /opt/
ln -s /opt/subread-1.5.1-Linux-x86_64/bin/featureCounts /usr/local/bin/featureCounts
rm /opt/subread-1.5.1-Linux-x86_64.tar.gz


#Install StringTie
wget -q -O /opt/stringtie-1.3.3.Linux_x86_64.tar.gz  http://ccb.jhu.edu/software/stringtie/dl/stringtie-1.3.3.Linux_x86_64.tar.gz
tar xvzf /opt/stringtie-1.3.3.Linux_x86_64.tar.gz -C /opt/
ln -s /opt/stringtie-1.3.3.Linux_x86_64/stringtie /usr/local/bin/stringtie
rm /opt/stringtie-1.3.3.Linux_x86_64.tar.gz


#Install MultiQC
/usr/local/bin/pip install git+git://github.com/ewels/MultiQC.git


#Install Hisats
git clone https://github.com/infphilo/hisat2.git /opt/hisat2
cd /opt/hisat2/
make
cp /opt/hisat2/hisat2 /opt/hisat2/hisat2-align-s /opt/hisat2/hisat2-align-l /opt/hisat2/hisat2-build /opt/hisat2/hisat2-build-s /opt/hisat2/hisat2-build-l /opt/hisat2/hisat2-inspect /opt/hisat2/hi    sat2-inspect-s /opt/hisat2/hisat2-inspect-l /usr/local/bin/
cp /opt/hisat2/*.py /usr/local/bin
