import boto3
from botocore.exceptions import ClientError
import json
import requests
import typing
from decimal import Decimal
import logging

class CreateNewTable:
    def __init__(self) -> None:
        self.dynamodb = boto3.resource('dynamodb')
    
    def createPriceHistoryTable(self, tableName: str) -> int:
        try:
            response = self.dynamodb.create_table(
                TableName=tableName,
                KeySchema=[
                    {
                        'AttributeName': 'date',
                        'KeyType': 'HASH'  # Hash Key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'date',
                        'AttributeType': 'S'  # string data type
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            logging.info("[createPriceHistoryTable]: New table created")
            return 200
        except ClientError  as err:
            logging.warning(f"[createPriceHistoryTable]: {err.response['message']} : Status: {err.response['ResponseMetadata']['HTTPStatusCode']}")
            # pass
            return err.response['ResponseMetadata']['HTTPStatusCode']

            
    def createItemOrderTable(self, tableName: str) -> int:
        response = None
        try:
            response = self.dynamodb.create_table(
                TableName=tableName,
                KeySchema=[
                    {
                        'AttributeName': 'issued', # It is called issued in the esi pull
                        'KeyType': 'HASH'  # Hash Key
                    },
                    {
                        'AttributeName': 'order_id', 
                        'KeyType': 'RANGE'  # Sort Key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'issued',
                        'AttributeType': 'S'  # string data type
                    },
                    {
                        'AttributeName': 'order_id',
                        'AttributeType': 'N'  # number data type
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            logging.info(f'[createItemOrderTable]: New table {tableName}_ORDERS created')
            return 200
        except ClientError  as err:
            logging.warning(f"[createItemOrderTable]: {err.response['message']} : Status: {err.response['ResponseMetadata']['HTTPStatusCode']}")
            pass
            return err.response['ResponseMetadata']['HTTPStatusCode']