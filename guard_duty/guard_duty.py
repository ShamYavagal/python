import json
import boto3
import requests
from datetime import datetime

class Gduty_Class():

    def __init__(self):
        ec2 = boto3.resource('ec2')
        self.instance = ec2.Instance(self.Instance_Id)
        self.ip = self.Public_Ip

    def slack_post(self):

        if eventparams.get('type').split(":")[1].split("/")[0] == "EC2":
            message = f"GuardDuty Violation: {eventparams.get('type')} --- Victim-Instance-Name: {self.instance_info()} --- Victim-Instance-Id: {self.Instance_Id} --- Remote IP: {self.ip} --- Country: {eventparams.get('country')} --- City: {eventparams.get('city')} --- Last Seen At: {eventparams.get('time')}"
        else:
            message = f"GuardDuty Violation: {eventparams.get('type')} Last Seen At {eventparams.get('time')}"

        if int(eventparams.get("severity")) >= 3:
            post_msg = requests.post(slack_url, json={"text": message}, headers={
                                     'Content-Type': 'application/json'})
            print(post_msg.status_code)

    def instance_info(self):
        for each in self.instance.tags:
            if each.get('Key') == 'Name':
                return each.get('Value')

    @classmethod
    def handler(cls, event_json):

        event_type = event_json.get('detail').get('type') #Removing 'input'
        eventparams["type"] = event_type

        cls.Public_Ip = event_json.get('detail').get('service').get('action').get('portProbeAction').get('portProbeDetails')[0].get('remoteIpDetails').get('ipAddressV4')
        cls.Instance_Id = event_json.get('detail').get("resource").get(
            "instanceDetails").get("instanceId")

        eventparams["severity"] = event_json.get('detail').get("severity")
        eventparams['time'] = str(datetime.strptime(event_json.get('detail').get(
            "service").get("eventLastSeen"), "%Y-%m-%dT%H:%M:%SZ"))
        eventparams['country'] = event_json.get('detail').get('service').get('action').get('portProbeAction').get('portProbeDetails')[0].get('remoteIpDetails').get('country').get('countryName')
        eventparams['city'] = event_json.get('detail').get('service').get('action').get('portProbeAction').get('portProbeDetails')[0].get('remoteIpDetails').get('city').get('cityName')

        if event_type.split(":")[0] == "UnauthorizedAccess":
            return "UnauthorizedAccess"
        elif event_type.split(":")[0] == "Stealth":
            return "Stealth"
        elif event_type.split(":")[0] == "Trogan":
            return "Trogan"
        return None


def gduty_event(event, context):
    event_result = Gduty_Class.handler(event)
    Slack_Post = Gduty_Class().slack_post()
    return event_result
