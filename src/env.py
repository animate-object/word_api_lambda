import boto3
import os

from base64 import b64decode

DB_PASS_ENCRYPTED = os.environ['DB_PASSWORD']
# Decrypt code should run once and variables stored outside of the function
# handler so that these are decrypted once per container
DB_PASS = boto3.client('kms').decrypt(
    CiphertextBlob=b64decode(DB_PASS_ENCRYPTED))['Plaintext']

DB_USER = os.environ['DB_USER']
DB_HOST = os.environ['DB_HOST']
DB_NAME = os.environ['DB_NAME']
