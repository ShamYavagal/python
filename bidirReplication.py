import boto3
import json
import uuid
from s3_event import event

session = boto3.Session(profile_name='dev')
s3_client = session.client('s3', region_name='us-east-1')
sqs_client = session.client('sqs', region_name='us-east-1')

response = s3_client.get_object_tagging(
    Bucket=event.get('Records')[0].get('s3').get('bucket').get('name'),
    Key=event.get('Records')[0].get('s3').get('object').get('key')
)

tags=response.get('TagSet')

s3_bucket = {}

print(tags)

tag_list = []

for each in tags:
    tag_list.append(each.get('Value'))

if 'us-east-1' not in tag_list:

    s3_bucket['Bucket'] = event.get('Records')[0].get('s3').get('bucket').get('name')
    s3_bucket['Key'] = event.get('Records')[0].get('s3').get('object').get('key')

    tags.append({
                    'Key': 'region',
                    'Value': 'us-east-1'
                })

    s3_client.put_object_tagging(
        Bucket=s3_bucket.get('Bucket'),
        Key=s3_bucket.get('Key'),
        Tagging={
            'TagSet': [
                    *tags,
                    ]
            },
        )

    QueueName = 'replication-queue.fifo'
    sqs_queue_url = sqs_client.get_queue_url(QueueName=QueueName).get('QueueUrl')

    response = sqs_client.send_message(QueueUrl=sqs_queue_url,
        MessageBody=json.dumps(s3_bucket),
        MessageGroupId='bidir',
        MessageDeduplicationId=str(uuid.uuid1()))

    print(response.get('MessageId'))