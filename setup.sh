#!/bin/bash

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
sudo rm -r awscliv2.zip ./aws

pip3 install virtualenv

virtualenv --python=/home/gitpod/.pyenv/shims/python app/pyenv

echo "source Secrets/.env" >> ~/.bashrc

echo "source Secrets/.env" >> ~/.bash_profile

exec "$SHELL"

source app/pyenv/bin/activate

cd app/

pip3 install -r requirements.txt

# To know the current environment of python, use the command: which python