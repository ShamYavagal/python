import glob 
import boto3 
import os 
import sys
import json
from multiprocessing.pool import ThreadPool 
import threading

session = boto3.Session(profile_name='dev')

sqs_client = session.client('sqs', region_name='us-east-1')

response = sqs_client.receive_message(
    QueueUrl=sqs_client.get_queue_url(QueueName='replication-queue.fifo').get('QueueUrl'),
    AttributeNames=['All'],
    MaxNumberOfMessages=10
)

try:
    messages = response['Messages']
    #print(messages)
except KeyError:
    print('No messages on the queue!')
    messages = []

for receiptHandle in messages:
    sqs_client.delete_message(
        QueueUrl=sqs_client.get_queue_url(QueueName='replication-queue.fifo').get('QueueUrl'),
        ReceiptHandle=receiptHandle.get('ReceiptHandle')
)

messages = [json.loads(message.get("Body")) for message in messages]

dedup_messages = []

for message in messages:
    if not message in dedup_messages:
        dedup_messages.append(message)

print("-----------------------")
#print(messages)
print("-----------------------")
print(dedup_messages)


s3 = session.resource('s3')

def s3_to_s3(bucket, key):
    source = {'Bucket':bucket, 'Key':key}
    dst_bucket = s3.Bucket('ads-dev-dr-' + bucket.split('-')[-1]) #This needs to be fixed based on ADS Environment

    dst_bucket.copy(source, key)

for each in dedup_messages:
    t = threading.Thread(target = s3_to_s3, args=(each.get('Bucket'), each.get('Key'))).start()


