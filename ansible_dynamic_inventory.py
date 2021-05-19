#!/usr/bin/python3.6

import boto3, datetime, time, socket, re, os, argparse, json

class ansible_inventory():
    def __init__(self, aws_profile='prod'):
        self.aws_session = boto3.Session(profile_name=aws_profile)
        self.ec2_client = self.aws_session.client('ec2', 'us-east-1')

        tags = self.ec2_client.describe_tags(Filters=[{'Name': 'resource-type', 'Values': ['instance']}])
        taglist = tags.get('Tags')
        self.Tags = {}
        for each in taglist:
            self.Tags[each['Key'] + '_' + each['Value']] = []
    
       
    def publist(self):
        instances = self.ec2_client.describe_instances() 
        ec2_list = instances['Reservations']
        for num, ins in enumerate(ec2_list):
            instancetags = []
            tagslist = ec2_list[num].get('Instances')[0].get('Tags')
            if ec2_list[num].get('Instances')[0].get('PublicIpAddress'):
                publicip = ec2_list[num].get('Instances')[0].get('PublicIpAddress')
                for each in tagslist:
                    instancetags.append(each['Key'] + '_' + each['Value'])
                for each in instancetags:
                    for key, value in self.Tags.items():
                        if key == each:
                            value.append(publicip)
        meta = {"_meta": {"hostvars": {}}}
        json_ansible = {**meta, **self.Tags}
        print(json.dumps(json_ansible, sort_keys=True, indent=2))
        return json.dumps(json_ansible, sort_keys=True, indent=2)

                                              
    def __call__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true', help='List instances (default: True)')
        parser.add_argument('--host', nargs='*', action='store', help='List ec2')
        args = parser.parse_args()
        if args.host:
            return {'_meta': {'hostvars': {}}}
        elif args.list:
            return self.publist()
        return self.publist()


inventory = ansible_inventory()
inventory()
