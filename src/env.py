
from base64 import b64decode
import logging
import os
import boto3


logging.basicConfig(level=logging.INFO)

logging.info("SETTING UP ENV VARS")

DB_PASS_ENCRYPTED = os.environ['DB_PASSWORD']
# Decrypt code should run once and variables stored outside of the function
# handler so that these are decrypted once per container
DB_PASS = boto3.client('kms').decrypt(
    CiphertextBlob=b64decode(DB_PASS_ENCRYPTED))['Plaintext']

DB_USER = os.environ['DB_USER']
DB_HOST = os.environ['DB_HOST']
DB_NAME = os.environ['DB_NAME']

if (any([required is None for required in [DB_USER, DB_PASS, DB_HOST, DB_NAME]])):
    logging.error("Missing required option, one of DB_USER %s, DB_PASS %s, DB_HOST %s, DB_NAME %s",
                  DB_USER, 'present' if DB_PASS else 'not present', DB_HOST, DB_NAME)
else:
    logging.info("Started up with config values DB_USER %s, DB_PASS <pw>, DB_HOST %s, DB_NAME %s",
                 DB_USER, DB_HOST, DB_NAME)
