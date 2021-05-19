import json
import boto3

def dependency_mapping(access_key, secret_key, session_token):
    
    client = boto3.client('codebuild', aws_access_key_id=access_key, 
         aws_secret_access_key=secret_key, aws_session_token=session_token
        )

    war_list = []
    ss = {}

    projects = json.dumps(client.list_projects(), indent=4, sort_keys=False)
    project_list = json.loads(projects).get('projects')


    for each in project_list:
        if not (each.endswith("ecr") or each.endswith("build")):
            war_list.append(each)
        

    for project in war_list:
        for each in client.batch_get_projects(names=[project]).get("projects"):
            ssl = (each).get("secondarySources")
            for si in ssl:
                if not si.get("sourceIdentifier") == "ojdbc6":
                    ss.setdefault(project, []).append(si.get("sourceIdentifier"))


    client_list = []

    for key, values in ss.items():
        for each in values:
            if not each in client_list:
                client_list.append(each)


    client_map = {}

    for client in client_list:
        for key,value in ss.items():
            if client in value:
                client_map.setdefault('pipeline-'+ key.split('build')[0][:-1], []).append(client)

    return client_map


def lambda_handler(event, context):
    
    name = event.get('requestContext').get('requestId') + '.json'

    s3 = boto3.resource('s3')
    with open(f'/tmp/{name}', 'w') as outfile:
        
        json_body = json.loads(event.get('body'))
        outfile.write(json.dumps(json_body, indent=4, sort_keys=True))
        s3.meta.client.upload_file(f'/tmp/{name}', 'ads-shared-artifacts', name)
        
    repo_name = json_body.get("repository").get("name")
    print(repo_name)
    branch_name = json_body.get("ref").split('/')[-1]
    
    account_number = "12345678911"
    
    if branch_name == 'master':
        branch_name = 'dev'
    
    if branch_name == 'dev':
        account_number = "12345678911"
    elif branch_name == 'prod':
        account_number = "12345678922"
    elif branch_name == 'stage':
        account_number = "12345678933"
    elif branch_name == 'uat':
        account_number = "12345678944"     
    
    sts_client = boto3.client('sts')
    assumed_role_object=sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_number}:role/assume_role",
        RoleSessionName="AssumeRoleSession1"
    )
    
    credentials=assumed_role_object['Credentials']
    aws_access_key_id=credentials['AccessKeyId']
    aws_secret_access_key=credentials['SecretAccessKey']
    aws_session_token=credentials['SessionToken']
    
    ClientMap = dependency_mapping(aws_access_key_id, aws_secret_access_key, aws_session_token)
    
    
    cp_client = boto3.client('codepipeline', aws_access_key_id=aws_access_key_id, 
         aws_secret_access_key=aws_secret_access_key, aws_session_token=aws_session_token
        )
    
    for pipeline, client_repos in ClientMap.items():
        for each in client_repos:
            if each.replace('_','-') == repo_name:
                cp_client.start_pipeline_execution(name=pipeline)
        
    return {
        'statusCode': 200,
        'headers': {'Content-Type':'application/json'},
        'body':json.dumps({'200':'valid response'})
    }