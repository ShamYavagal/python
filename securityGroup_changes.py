import os
import json
import boto3
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from ses_creds import get_secret
import requests
import base64
from botocore.exceptions import ClientError

def get_secret():

    secret_name = "slack_url"
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
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
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return get_secret_value_response


slack_url = get_secret()

access_key = json.loads(get_secret().get('SecretString')).get('access_key')
secret_key = json.loads(get_secret().get('SecretString')).get('secret_key')

simplejson = {"foo": "bar"} #Place Holder JSON

def lambda_handler(event, context):
    try:
        try:
            event = event["detail"]
        except:
            print("KeyError")
            
        aws_session = boto3.Session()
        ec2_client = aws_session.client('ec2')

        SecurityGroups = ec2_client.describe_security_groups().get('SecurityGroups')
        
        if event["userIdentity"].get("userName"):
            User = (event["userIdentity"].get("userName"))
        elif event["userIdentity"]["principalId"]:
            if len(event["userIdentity"]["principalId"].split(':')) == 2:
                User = event["userIdentity"]["principalId"].split(':')[1]
        else:
            User = "OktaDevAccountAdminUser"
        
        SG = (event["requestParameters"].get("groupId"))

        EventTime = (datetime.datetime.strptime((event["eventTime"]), "%Y-%m-%dT%H:%M:%SZ"))
        
        PerformedAction = (event["eventName"])
        
        SG_GROUPS = {}
        for each in SecurityGroups:
            SG_GROUPS[each.get('GroupId')] = each.get('GroupName')

        
        for each in SecurityGroups:
            if each.get('GroupId') == SG:
                Sg_Name = each.get('GroupName')

        
        RuleList = []
        if event["requestParameters"].get("ipPermissions").get("items"):
            for each in event["requestParameters"].get("ipPermissions").get("items"):
                RuleList.append(each)
        else:
            Rule = {
                "ipProtocol": event["requestParameters"].get("ipProtocol"),
                "fromPort": event["requestParameters"].get("fromPort"),
                "toPort": event["requestParameters"].get("toPort"),
                "cidrIp": event["requestParameters"].get("cidrIp")
            }
            RuleList.append(Rule)
        
        
        Rules = []
        val_Rules = []
        for each in RuleList:    
            if each.get('ipProtocol') == "-1":
                Protocol = 'Protocol: ALL'
            else:                 
                Protocol = 'Protocol: ' + each.get('ipProtocol')

            if each.get('fromPort') and each.get('toPort'):
                PortRange1 = each.get('fromPort')
                PortRange2 = each.get('toPort')
                PortRange = 'Port Range: ' + str(PortRange1) + ' - ' + str(PortRange2)
            else:
                PortRange = 'Port Range: NONE - NONE' 
                PortRange1 = None
                PortRange2 = None
            
            
            if each.get("cidrIp"):
                IpRange = 'IP Range: ' + str(each.get("cidrIp"))
            elif each.get("cidrIpv6"):
                IpRange = 'IP Range: ' + str(each.get("cidrIpv6"))
            

            if each.get("Description"):
                Description = 'Description: ' + str(each.get("Description"))
            else:
                Description = 'Description: NONE'

            if each.get('ipRanges'):
                if each.get('ipRanges').get('items')[0].get('cidrIp'):
                    IpRange = 'IP Range: ' + str(each.get('ipRanges').get('items')[0].get('cidrIp'))

                else:
                    IpRange = 'IP Range: NONE'
                if each.get('ipRanges').get('items')[0].get('description'):
                    Description = 'Description: ' + each.get('ipRanges').get('items')[0].get('description')
                else:
                    Description = 'Description: NONE'

                    
            if each.get('ipv6Ranges'):
                if each.get('ipv6Ranges').get('items')[0].get('cidrIpv6'):
                    IpRange = 'IP Range: ' + str(each.get('ipv6Ranges').get('items')[0].get('cidrIpv6'))

                else:
                    IpRange = 'IP Range: NONE'
                if each.get('ipv6Ranges').get('items')[0].get('description'):
                    Description = 'Description: ' + each.get('ipv6Ranges').get('items')[0].get('description')
                else:
                    Description = 'Description: NONE'
                    
            
            if each.get('groups'):
                SgGroup = 'Security Group Added To This Group: ' +  SG_GROUPS[each.get('groups').get('items')[0].get('groupId')]
            else:
                SgGroup = "Security Group Added To This Group: NONE"
            

            ruleset = Protocol + ' --- ' +  PortRange + ' --- ' + IpRange + ' --- ' + Description  + ' --- ' + SgGroup

            print("#########")
            subnet1 = re.findall("0.0.0.0/0", IpRange)
            subnet2 = re.findall("::/0", IpRange)
            print("#########")

            try:
                if subnet1 and PerformedAction == "AuthorizeSecurityGroupIngress" and Description.split(':')[1].split()[0] != 'Exception':
                    ec2_client.revoke_security_group_ingress(CidrIp='0.0.0.0/0',
                        GroupId=SG, IpProtocol=Protocol.split(':')[1].split()[0].upper(),
                        FromPort=PortRange1, ToPort=PortRange2)
                    val_Rules.append(ruleset)
                elif subnet2 and PerformedAction == "AuthorizeSecurityGroupIngress" and Description.split(':')[1].split()[0] != 'Exception':
                    ec2_client.revoke_security_group_ingress(IpPermissions=[{'IpProtocol': Protocol.split(':')[1].split()[0].upper(), \
                    'FromPort': PortRange1, 'ToPort': PortRange2, 'Ipv6Ranges': [{'CidrIpv6':'::/0'}]}], GroupId=SG)
                    val_Rules.append(ruleset)
                    
                else:
                    Rules.append(ruleset)                  
            except Exception as e:
                print(e)
                print("Failed To Revoke the Vulnerable Rule")
                        
        def AccessOrDeny():
            if PerformedAction == ("AuthorizeSecurityGroupIngress" or "AuthorizeSecurityGroupEgress"):
                Changes = "Additions Made To The Security Group"
            else:
                Changes = "Deletions Made To The Security Group"
            return Changes

        val_rule_sentence = "Rules That Are Not Allowed To Be Added And Will Be Deleted!" 

        def HtmlRules(*args):
            Rules_Html = """<table class="tftable" border="1">
                <tbody>
                <tr>
                <th colspan="4">""" + args[0] + """</th>
                </tr>"""    
            for each in args[1]:
                Rules_Html += """\
                <tr>
                <td colspan="1">""" + each + """</td>
                </tr>
                """
            return Rules_Html
            
        def SlackRules(*args):
            Rules_Slack = "*" + args[0] + "*"
            for each in args[1]:
                Rules_Slack += "\n" + "_" + each + "_" + "\n"
            return Rules_Slack

        def SendEmail(From, receipients, subject, body):
            try:
                mail = smtplib.SMTP('email-smtp.us-east-1.amazonaws.com', 587)
                context = ssl.create_default_context()
                mail.starttls(context=context)
                mail.login(access_key, secret_key)
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = From
                message["To"] = ', '.join(receipients)
                htmlmsg = MIMEText(body, "html")
                message.attach(htmlmsg)
                mail.sendmail(From, receipients, message.as_string())
                print("mail SENT")
            except Exception as e:
                print(e)

        if User == "OktaDevAccountAdminUser":
            SniUser = "test_user" #This is for emailing Purposes Only, syavagal did not make the change here to the SecurityGroup
        else:
            SniUser = User

        subj = "Following Rules Are Not Allowed"
        recp = [SniUser + '@yourdomain.com', 'syavagal@yourdomain.com']
        From = "ops@yourdomain.com"
        
        
        if val_Rules and Rules:
            TEXT1 = User + ": You are not allowed to Add the Following Rule To SecurityGroup " + Sg_Name
            body = """<html><body>""" + "<tr>" + TEXT1 + "<br><br>" + HtmlRules(val_rule_sentence, val_Rules) + "</tr>" + \
                    "<tr>" + "<br>" + HtmlRules(AccessOrDeny(), Rules) + "</tr>" + """</body></html>"""
            SendEmail(From, recp, subj, body)
            requests.post(slack_url, json={"text": "<!here>" + ' ' + TEXT1 + '\n' + SlackRules(val_rule_sentence, val_Rules) + '\n' + SlackRules(AccessOrDeny(), Rules)}, headers={
                                     'Content-Type': 'application/json'})
        elif val_Rules:
            TEXT1 = User + ": You are not allowed to Add the Following Rule To SecurityGroup " + Sg_Name
            body = """<html><body>""" + TEXT1 + "<br><br>" + HtmlRules(val_rule_sentence, val_Rules) + """</body></html>"""
            SendEmail(From, recp, subj, body)
            requests.post(slack_url, json={"text": "<!here>" + ' ' + TEXT1 + '\n' + SlackRules(val_rule_sentence, val_Rules)}, headers={
                                     'Content-Type': 'application/json'})
        else:
            if AccessOrDeny() == "Additions Made To The Security Group":
                TEXT = "The Following Additions Were Made To The Security Group " +  str(Sg_Name) + " by " + str(User) + " at " + str(EventTime) + " \r\n"
            elif AccessOrDeny() == "Deletions Made To The Security Group":
                TEXT = "The Following Deletions Were Made To The Security Group " +  str(Sg_Name) + " by " + str(User) + " at " + str(EventTime) + " \r\n"
            BODY_HTML = """<html>     <body>""" + TEXT + "<br><br>" + HtmlRules(AccessOrDeny(), Rules) + """</body>      </html>"""
            FROM = "sniops@shonoc.com"
            RECIPIENTS = [SniUser + '@yourdomain.com', 'username@yourdomain.com']
            SUBJECT = "Security Group Changes"
            SendEmail(FROM, RECIPIENTS, SUBJECT, BODY_HTML)
            requests.post(slack_url, json={"text":  "<!here>" + ' ' + TEXT + '\n' + SlackRules(AccessOrDeny(), Rules)}, headers={
                                     'Content-Type': 'application/json'})
    except Exception as e:
        print(e)
        message = json.dumps(event, indent=4, sort_keys=True).replace(' ', '&nbsp;').replace('\n', '<br>')
        slack_msg = json.dumps(event, indent=4, sort_keys=True)
        Subject='Security Group Changes'
        jsonbody = "Lambda JSON Filter Failed, There was a SecurityGroup Change, Below is the JSON Format Of The Change: " + "<br><br>"  + message 
        FROM = "sniops@shonoc.com"
        RECIPIENTS = [User + '@yourdomain.com', 'username@yourdomain.com']
        SendEmail(FROM, RECIPIENTS, Subject, jsonbody)
        requests.post(slack_url, json={"text": "*" + "Lambda JSON Filter Failed, There was a SecurityGroup Change, Below is the JSON Format Of The Change" + "*" + "\n" + slack_msg}, headers={
            'Content-Type': 'application/json'})
