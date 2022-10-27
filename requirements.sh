#!/usr/bin/env bash

##--------------------------------------------------------------------
## Copyright (c) 2021 ACDP
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##--------------------------------------------------------------------

##
## Author: Sebastian Kropatschek
##

set -e

os_name=`(grep -o '^NAME=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')`
os_version=`(grep -o '^VERSION_ID=.*' /etc/os-release | cut -f2 -d\" | sed 's/"//g')`
echo "Platform is ${os_name}, Version: ${os_version}"

echo Installing requirements
if [[ ( $os_name == *"Red Hat"* || $os_name == *"CentOS"* ) &&  $os_version == *"7"* ]]; then
	sudo yum install -y wget
	# TODO never tested
	sudo yum install -y p7zip
	wget --content-disposition -c https://sourceforge.net/projects/snap7/files/1.4.2/snap7-full-1.4.2.7z/download
	p7zip -d snap7-full-1.4.2.7z
	cd snap7-full-1.4.2/build/unix
	# TODO if 64bit  
	make -f "$(uname -m)_linux.mk" install	LibInstall=/usr/lib64
	
elif apt --version 2>/dev/null; then
	#sudo apt install -y software-properties-common
	#sudo add-apt-repository -y ppa:gijzelaar/snap7
	#sudo apt update
	#sudo apt-get install -y libsnap7-1 libsnap7-dev
	
	sudo apt install -y wget
	sudo apt install -y p7zip
	wget --content-disposition -c https://sourceforge.net/projects/snap7/files/1.4.2/snap7-full-1.4.2.7z/download
	echo "A" | p7zip -d snap7-full-1.4.2.7z
	cd snap7-full-1.4.2/build/unix
	make -f "$(uname -m)_linux.mk" install	
else
	echo "Requirements cannot be automatically installed, please refer README.rst to install requirements manually"
fi
