# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
"""Deploy Strands Agent to AgentCore Runtime using starter toolkit"""

import logging
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import time, sys, os, boto3, json, argparse
from cognito_utils import create_agentcore_role, setup_cognito_user_pool

def main():
    parser = argparse.ArgumentParser(description='Deploy Strands Agent to AgentCore Runtime')
    parser.add_argument('--agent-file', default='agent.py', help='Agent file to deploy (default: agent.py)')
    parser.add_argument('--auto-update-on-conflict', action='store_true', help='Auto-update on conflict')
    args = parser.parse_args()
    
    agent_file = args.agent_file
    boto_session = Session()
    region = boto_session.region_name
    
    required_files = [agent_file, 'requirements.txt']
    for file in required_files:
        if not os.path.exists(file):
            raise FileNotFoundError(f"Required file {file} not found")
    
    # Determine tool name based on agent file
    if 'memory' in agent_file:
        tool_name = "oran_agent_memory"
    else:
        tool_name = "oran_agent"
    agentcore_iam_role = create_agentcore_role(agent_name=tool_name)
    cognito_config = setup_cognito_user_pool()
    
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config['client_id']],
            "discoveryUrl": cognito_config['discovery_url'],
        }
    }

    agentcore_runtime = Runtime()
    agentcore_runtime.configure(
        entrypoint=agent_file,
        execution_role=agentcore_iam_role['Role']['Arn'],
        auto_create_ecr=True,
        requirements_file="requirements.txt",
        region=region,
        authorizer_configuration=auth_config,
        agent_name=tool_name
    )
    
    launch_result = agentcore_runtime.launch()

    ssm_client = boto3.client('ssm', region_name=region)
    secrets_client = boto3.client('secretsmanager', region_name=region)
    try:
        secrets_client.create_secret(
            Name=f'/agent/{tool_name}/cognito/credentials',
            Description='Cognito credentials for MCP server',
            SecretString=json.dumps(cognito_config)
        )
    except secrets_client.exceptions.ResourceExistsException:
        secrets_client.update_secret(
            SecretId=f'/agent/{tool_name}/cognito/credentials',
            SecretString=json.dumps(cognito_config)
        )
    
    ssm_client.put_parameter(
        Name=f'/agent/{tool_name}/runtime/agent_arn',
        Value=launch_result.agent_arn,
        Type='String',
        Description='Agent ARN for MCP server',
        Overwrite=True
    )
    
    ssm_client.put_parameter(
        Name=f'/agent/{tool_name}/runtime/client_id',
        Value=cognito_config["client_id"],
        Type='String',
        Description='Client ID for auth',
        Overwrite=True
    )

if __name__ == "__main__":
    main()
