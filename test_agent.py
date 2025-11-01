# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import requests
import sys

# Global constant for request timeout
REQUEST_TIMEOUT_SECONDS = 300
import urllib.parse

# Accept agent name as argument, default to oran_agent
agent_name = sys.argv[1] if len(sys.argv) > 1 else "oran_agent"
print(f"Testing agent: {agent_name}")

# Initialize AWS clients
ssm_client = boto3.client('ssm', region_name='us-east-1')
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

# Get agent ARN from SSM parameter
agent_arn = ssm_client.get_parameter(Name=f'/agent/{agent_name}/runtime/agent_arn')["Parameter"]["Value"]
print(f"Using Agent ARN: {agent_arn}")

# Get Cognito credentials from Secrets Manager
cognito_secret = secrets_client.get_secret_value(SecretId=f'/agent/{agent_name}/cognito/credentials')
cognito_creds = json.loads(cognito_secret['SecretString'])

# Get authentication token
auth_response = cognito_client.initiate_auth(
    ClientId=cognito_creds['client_id'],
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': 'testuser',
        'PASSWORD': 'MyPassword123!'
    }
)
token = auth_response['AuthenticationResult']['AccessToken']

# Use requests for OAuth support
url = f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{urllib.parse.quote(agent_arn, safe='')}/invocations"
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}
payload = {"prompt": "Using the O2 interface, do I have any O-Cloud resources supplied by Intel?"}

print(f"USER PROMPT: {payload['prompt']}")
response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
response.raise_for_status()
print(f"Response status: {response.status_code}")

if response.status_code == 200:
    response_data = response.json()
    assistant_text = response_data
    print("\n" + "="*50)
    print("AGENT RESPONSE:")
    print("="*50)
    print(assistant_text)
else:
    print(f"Error response: {response.text}")
