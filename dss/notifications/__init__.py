import json
import random
import typing

from dss import Config
from dss.util.aws import ARN
from dss.util.aws.clients import sqs  # type: ignore


class DSSNotificationFailed(Exception):
    pass


def aquire_queue_url() -> str:
    name = Config.get_notification_queue_name()

    try:
        url = sqs.get_queue_url(QueueName=name)
    except sqs.exceptions.ClientError as e:
        if 'NonExistentQueue' == e.response['Error']['Code']:
            resp = sqs.create_queue(QueueName=name)
            url = resp['QueueUrl']
        else:
            raise

    return url


def notify(callback_url: str, data: typing.Dict[typing.Any, typing.Any]):
    payload = json.dumps(data)

    try:
        _send(callback_url, payload)
    except DSSNotificationFailed:
        _enqueue(callback_url, payload)


def _enqueue(callback_url: str, payload: str):
    message_attributes = {
        'callback_url': {
            'StringValue': callback_url,
            'DataType': 'String',
        }
    }

    url = aquire_queue_url()

    sqs.send_message(
        QueueUrl=url,
        MessageBody=json.dumps(payload),
        MessageAttribute=message_attributes
    )


def process_queue():
    url = aquire_queue_url()

    resp = sqs.receive_message(
        QueueUrl=url,
        MaxNumberOfMessages=10,
        VisibilityTimeout=300,
        WaitTimeSeconds=60,
    )

    for message in resp['Messages']:
        try:
            callback_url = message['MessageAttributes']['callback_url']['StringValue']
            payload = message['Body']
            _send(callback_url, message['Body'])
            sqs.delete_message(QueueUrl=url, ReceiptHandle=message['ReceiptHandle'])
        except DSSNotificationFailed:
            pass

    return len(resp['Messages'])


def _send(callback_url: str, payload: str):
    a = random.randint(0, 1)
    if a > 0:
        raise DSSNotificationFailed('so sad too bad')
