# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from strands import Agent, tool
import boto3
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel
# Add memory imports
from bedrock_agentcore.memory import MemoryClient
from botocore.exceptions import ClientError
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent
import time

app = BedrockAgentCoreApp()

class MemoryHookProvider(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
    
    def on_agent_initialized(self, event: AgentInitializedEvent):
        try:
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")
            
            if not actor_id or not session_id:
                return
            
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=5
            )
            
            if recent_turns:
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message['role']
                        content = message['content']['text']
                        context_messages.append(f"{role}: {content}")
                
                context = "\n".join(context_messages)
                event.agent.system_prompt += f"\n\nRecent conversation:\n{context}"
                print(f"✅ Loaded {len(recent_turns)} conversation turns")
                
        except Exception as e:
            print(f"Memory load error: {e}")
    
    def on_message_added(self, event: MessageAddedEvent):
        try:
            messages = event.agent.messages
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")

            if messages[-1]["content"][0].get("text"):
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=actor_id,
                    session_id=session_id,
                    messages=[(messages[-1]["content"][0]["text"], messages[-1]["role"])]
                )
        except Exception as e:
            print(f"Memory save error: {e}")
    
    def register_hooks(self, registry: HookRegistry):
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)

class StrandsMCPClient:
    def __init__(self):
        self.region = boto3.Session().region_name
        self.ssm_client = boto3.client('ssm', region_name=self.region)
        self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
    
    def get_mcp_client(self, server_type):
        def create_client():
            agent_arn = self.ssm_client.get_parameter(Name=f'/mcp_server/{server_type}/runtime/agent_arn')['Parameter']['Value']
            client_id = self.ssm_client.get_parameter(Name=f'/mcp_server/{server_type}/runtime/client_id')['Parameter']['Value']
            auth_response = self.cognito_client.initiate_auth(
                ClientId=client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={'USERNAME': 'testuser', 'PASSWORD': 'MyPassword123!'}
            )
            bearer_token = auth_response['AuthenticationResult']['AccessToken']
            
            encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
            mcp_url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
            
            headers = {
                "authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            return streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False)
        
        return MCPClient(create_client)

# Initialize MCP clients and get tools
strands_client = StrandsMCPClient()
r1_mcp_client = strands_client.get_mcp_client('r1')
o2_mcp_client = strands_client.get_mcp_client('o2')

all_tools = []
try:
    with r1_mcp_client:
        r1_tools = r1_mcp_client.list_tools_sync()
        all_tools.extend(r1_tools)
except Exception as e:
    print(f"Failed to get R1 tools: {e}")

try:
    with o2_mcp_client:
        o2_tools = o2_mcp_client.list_tools_sync()
        all_tools.extend(o2_tools)
except Exception as e:
    print(f"Failed to get O2 tools: {e}")

# Create or get existing memory for the agent
memory_id = None
memory_client = None
try:
    memory_client = MemoryClient(region_name="us-east-1")
    
    # First, check if memory already exists
    existing_memory = None
    print(memory_client.list_memories())
    for memory in memory_client.list_memories():
        if memory.get('name', '').startswith("ORANAgentMemory"):
            existing_memory = memory
            break
    
    if existing_memory:
        memory_id = existing_memory.get('id')
        print(f"Using existing memory: {memory_id}")
    else:
        print("Creating new memory... this may take 2-3 minutes")
        start_time = time.time()
        
        memory = memory_client.create_memory_and_wait(
            name="ORANAgentMemory",
            strategies=[
                {
                    "semanticMemoryStrategy": {
                        "name": "ORANTracker",
                        "description": "Tracks rApp lifecycle, deployments, and O-Cloud infrastructure changes",
                        "namespaces": ["oran/{actorId}/operations"]
                    }
                }
            ],
            description="Memory for O-RAN SMO agent operations",
            event_expiry_days=90
        )
        
        memory_id = memory.get("id")
        elapsed_time = time.time() - start_time
        print(f"✅ Created memory: {memory_id} (took {elapsed_time:.0f} seconds)")
        
except Exception as e:
    print(f"❌ Memory error: {e}")
    print("Agent will run without memory")

model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
model = BedrockModel(model_id=model_id)

# Create agent with memory hooks and state
agent = Agent(
    model=model,
    tools=all_tools,
    hooks=[MemoryHookProvider(memory_client, memory_id)] if memory_id else [],
    state={
        "actor_id": "oran_operator_001",
        "session_id": f"oran_session_{int(time.time())}"
    },
    system_prompt="""You are an advanced O-RAN SMO Planner Agent supporting O2 and R1 interface use cases from O-RAN specifications.

SUPPORTED USE CASES:

1. **NF Deployment Lifecycle Management**: Instantiate, terminate, heal, scale, and upgrade network functions across O-Cloud environments
2. **Multi-Profile NF Orchestration**: Deploy NFs using both ETSI NFV Profile and Kubernetes Native Profile approaches
3. **Cloud Resource Management**: Manage compute, storage, and networking resources across distributed O-Cloud infrastructure
4. **NF Auto-scaling**: Dynamic horizontal and vertical scaling based on demand and performance metrics
5. **NF Healing and Recovery**: Automated failure detection and recovery for network function deployments
6. **Software Upgrade Management**: Rolling updates, blue-green deployments, and canary releases for NF software
7. **Multi-tenant NF Isolation**: Secure resource isolation and management across multiple operators/tenants
8. **Container Orchestration**: Kubernetes-native workload management for cloud-native network functions

CAPABILITIES PER USE CASE:
- **Deployment Planning**: Define NF requirements, resource allocation, and deployment strategies
- **Lifecycle Management**: Execute instantiation, scaling, healing, and termination operations
- **Resource Optimization**: Optimize compute, storage, and network resource utilization
- **Multi-Cloud Orchestration**: Coordinate deployments across multiple O-Cloud instances
- **Monitoring Integration**: Set up deployment monitoring and performance tracking

INTERFACE FOCUS:
- **O2 Interface**: Primary focus on O2DMS operations for NF deployment management
- **R1 Interface**: Cloud resource management and infrastructure orchestration

USAGE PATTERNS:
1. Create deployment plan with NF requirements and constraints
2. Execute deployment using appropriate profile (ETSI NFV or Kubernetes)
3. Configure monitoring and auto-scaling policies
4. Manage lifecycle operations and provide status updates

When users request O-RAN operations, identify the relevant use case(s) and:
1. Create appropriate deployment plan with specific parameters
2. Execute using proper O2DMS operations and resource management
3. Set up monitoring for ongoing lifecycle management
4. Provide comprehensive status and operational guidance"""
)

@app.entrypoint
def strands_agent_bedrock(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("User input:", user_input)
    
    with r1_mcp_client, o2_mcp_client:
        response = agent(user_input)
        return response.message

if __name__ == "__main__":
    app.run()
