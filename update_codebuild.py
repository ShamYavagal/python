import sys
import boto3
import time
import json
from pprint import pprint
from bson import json_util
###################################################################################

if len(sys.argv) != 4:
    pprint('usage <SCRIPT_NAME> <AWS_PROFILE_NAME> <AWS_REGION> <BRANCH_NAME>')
    sys.exit()
    
profile=sys.argv[1]
region=sys.argv[2]
branch_name=sys.argv[3]

session = boto3.Session(profile_name=profile)

client = session.client('codebuild', region_name=region)

projects = json.dumps(client.list_projects(), indent=4, sort_keys=False)
project_list = json.loads(projects).get('projects')


def create_project_list():

    war_list = []
    projects = json.dumps(client.list_projects(), indent=4, sort_keys=False)
    project_list = json.loads(projects).get('projects')
    
    for each in project_list:
        if not (each.endswith("ecr") or each.endswith("build")):
            war_list.append(each)
    
    return war_list

def create_war_mappings():
    
    ss = {}
    for project in create_project_list():
        for each in client.batch_get_projects(names=[project]).get("projects"):
            ssl = (each).get("secondarySources")
            for si in ssl:
                if not si.get("sourceIdentifier") == "ojdbc6":
                    ss.setdefault(project, []).append({'sourceIdentifier': si.get("sourceIdentifier"),'sourceVersion': branch_name})
    
    return ss

def update_cb_project():
    for key,val in create_war_mappings().items():
        resp = client.update_project(name=key, secondarySourceVersions=val)
        pprint((resp))
                
update_cb_project()

###################################################################################