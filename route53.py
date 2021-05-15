import boto3
import json
import requests
region = 'us-east-1'
import base64
from botocore.exceptions import ClientError


secret_values = {}

def get_secret():

    region_name = "us-east-1"
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    for each in ["slack_url", "zone_id"]:
            
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=each
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'DecryptionFailureException':
                raise e
            elif e.response['Error']['Code'] == 'InternalServiceErrorException':
                raise e
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                raise e
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                raise e
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise e
        else:
            if 'SecretString' in get_secret_value_response:
                secret = get_secret_value_response['SecretString']
                secret_values[each] = secret
            else:
                decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
                secret_values[each] = decoded_binary_secret
    #return secret_values

get_secret()
       
class dns():
    def __init__(self, service, domain, zoneid,):
        self.service = service
        self.domain = domain
        self.zoneid = zoneid
    
        # If you need to assume a role from a different aws account in case of domain being hosted in that account.
        sts_client = boto3.client('sts')
        assumed_role_object=sts_client.assume_role(
            RoleArn="arn:aws:iam::11111111111:role/role_name",
            RoleSessionName="AssumeRoleSession1"
        )
        credentials=assumed_role_object['Credentials']
    
        route53 = boto3.client(
            'route53', aws_access_key_id=credentials['AccessKeyId'], 
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            )
            
        ec2 = boto3.client('ec2', region_name=region)
        servers = ec2.describe_instances(Filters=[
            {
                'Name': 'tag-value',
                'Values': [{self.service}
                ]
            },
        ])

        ec2_servers = []

        for each in servers.get('Reservations'):
            if each.get('Instances')[0].get('PrivateIpAddress'):

                ec2_servers.append(each.get('Instances')[0].get('PrivateIpAddress'))
                  
        response = route53.list_resource_record_sets(HostedZoneId=self.zoneid)
        
        ip_list = []
        
        for each in response.get('ResourceRecordSets'):
            if each.get('Name') == f'{self.service}.{self.domain}.':
                ip_list = each.get('ResourceRecords')
                
        ip_list = [each.get('Value') for each in ip_list]
              
        check_changes = set(ec2_servers) - set(ip_list)
        
        if len(check_changes) > 0:
        
            records = []

            for index, each in enumerate(ec2_servers):
                records.append({'Value':each})
        
            try:
                response = route53.change_resource_record_sets(
	                HostedZoneId=self.zoneid,
                    ChangeBatch = {
                        'Changes': [
                            {
                                'Action': 'UPSERT',
                                'ResourceRecordSet' : {
                                'Name' : f'{self.service}.{self.domain}.',
                                'Type' : 'A',                             
                                'TTL' : 60,
                                'ResourceRecords' : [*records] 
                            }
                                }
                        ]
                    }
                )
            except Exception as E:
                print(E)
                message = f"Failed to Update DNS Records --> Exception: {str(E)}"
                requests.post(get_secret.get('slack_url'), json={"text": message}, headers={'Content-Type': 'application/json'})
                

def lambda_handler(event, context):
    print("RUNNING FUNCTION")
    dns1 = dns('name1', 'example.com', secret_values.get("zone_id"))
    dns2 = dns('name2', 'example.com', secret_values.get("zone_id"))
    dns3 = dns('name3', 'example.com', secret_values.get("zone_id"))