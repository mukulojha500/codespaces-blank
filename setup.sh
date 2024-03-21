#!/bin/bash

# Setup file for the project:

# Getting the awscli package using curl
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip

# Check if aws is already installed or not
aws --version
exit_code=$?

# If already installed, then update. Else, then install
if [[ $exit_code -eq 0 ]]; then
    sudo ./aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli --update
    echo "AWS CLI is updated"
else
    echo "AWS CLI is not installed, Installing..."
    sudo ./aws/install
fi

# Remove install package
sudo rm -r awscliv2.zip ./aws

# Specify the path to your .env file
ENV_FILE_PATH="Secrets/.env"

# Read AWS credentials from .env file
AWS_ACCESS_KEY_ID=$(grep AWS_ACCESS_KEY_ID $ENV_FILE_PATH | cut -d '=' -f2)
AWS_SECRET_ACCESS_KEY=$(grep AWS_SECRET_ACCESS_KEY $ENV_FILE_PATH | cut -d '=' -f2)

# Configure AWS CLI for access key, secret key and 
aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure set default.region us-east-1 
aws configure set default.output json

cd app

pip3 install -r requirements.txt