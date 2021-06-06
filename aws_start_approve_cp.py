import sys
import boto3
import time
from pprint import pprint

if len(sys.argv) != 3:
    pprint('usage SCRIPT_NAME AWS_PROFILE_NAME AWS_REGION')
    sys.exit()
    
profile=sys.argv[1]
region=sys.argv[2]

session = boto3.Session(profile_name=profile)
client = session.client('codepipeline', region_name=region)

pipeline_list = []

state_mapping = {}

for each in client.list_pipelines().get('pipelines'):

    if not ('frontend' in each.get('name') or 'testing' in each.get('name') or 'consul' in each.get('name')):
        pipeline_list.append(each.get('name'))
        

for each in pipeline_list:
    client.start_pipeline_execution(name=each)

time.sleep(60)

for each in pipeline_list:
    
    state = client.get_pipeline_state(name=each)
              
    for pipeline in state.get('stageStates'):
        try:
            if pipeline.get('actionStates')[0].get('actionName') == 'Manual-Approval' and pipeline.get('actionStates')[0].get('latestExecution').get('status') == 'InProgress':
                
                state_mapping[state.get('pipelineName')] = pipeline.get('actionStates')[0].get('latestExecution').get('token')
                        
        except AttributeError:
                pprint("There is no such attribute")
        
pprint(state_mapping)
        
for key, value in state_mapping.items():
    result = client.put_approval_result(
        pipelineName=key,
        stageName='Approval',
        actionName='Manual-Approval',
        result={
        'summary': 'Bulk Approval',
        'status': 'Approved'
        },
        token=value
        )
    
    #print(dir(result))