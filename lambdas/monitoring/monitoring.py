### We need to override boto3 because currently available in Lambda is outdated and doesn't support Timestream
import sys
from pip._internal import main

main(['install', '-I', '-q', 'boto3', '--target', '/tmp/',
      '--no-cache-dir', '--disable-pip-version-check'])
sys.path.insert(0, '/tmp/')

import time
import urllib3
from botocore.exceptions import ClientError
from threading import Thread
from botocore.client import Config
from aws_lambda_powertools import Tracer, Logger
import queue
import os
import boto3
from os import stat


tracer = Tracer(service="cpt-monitoring")
logger = Logger(
    service="cpt-monitoring", level=os.environ.get("LOG_LEVEL", "INFO")
)

logger.info(boto3.__version__)

# this will prevent long timeouts
BOTO3_CONFIG = Config(connect_timeout=5, retries={"max_attempts": 0})

http = urllib3.PoolManager()

DATABASE_NAME = os.environ['TS_Database']
TABLE_NAME = os.environ['TS_Table']

session = boto3.Session()
tsclient = boto3.client('timestream-write', config=Config(read_timeout=20, max_pool_connections=5000,
                                                          retries={'max_attempts': 10}))


@tracer.capture_method
def _current_milli_time():
    return str(int(round(time.time() * 1000)))


@tracer.capture_method
def write_records(siteId: str, endpointUp: bool, latency: dict, error_msg: str, status: int):
    current_time = _current_milli_time()

    dimensions = [
        {'Name': 'siteId', 'Value': siteId},
        {'Name': 'region', 'Value': session.region_name}
    ]

    endpoint_up = {
        'Dimensions': dimensions,
        'MeasureName': 'endpoint_up',
        'MeasureValue': str(endpointUp),
        'MeasureValueType': 'BOOLEAN',
        'Time': current_time
    }
    
    endpoint_latency = {
        'Dimensions': dimensions,
        'MeasureName': 'latency',
        'MeasureValue': str(latency["avg_lat"]),
        'MeasureValueType': 'DOUBLE',
        'Time': current_time
    }

    error_message = {
        'Dimensions': dimensions,
        'MeasureName': 'error_message',
        'MeasureValue': "" if error_msg == None else str(error_msg),
        'MeasureValueType': 'VARCHAR',
        'Time': current_time
    }

    status_code = {
        'Dimensions': dimensions,
        'MeasureName': 'status_code',
        'MeasureValue': str(status),
        'MeasureValueType': 'BIGINT',
        'Time': current_time
    }

    records = [endpoint_up, endpoint_latency, error_message, status_code]
    ### We will not put record(s) if value is None or ""
    records_filtered = [rec for rec in records if not (rec['MeasureValue'] == "None" or rec['MeasureValue'] == None or rec['MeasureValue'] == "")]
    

    try:
        result = tsclient.write_records(DatabaseName=DATABASE_NAME, TableName=TABLE_NAME,
                                        Records=records_filtered, CommonAttributes={})
        logger.info("WriteRecords Status: [%s]" %
                    result['ResponseMetadata']['HTTPStatusCode'])
    except Exception as err:
        logger.error("Error:", err)


@tracer.capture_method
def measure_latency(endpoint: str, latQ: queue):
    """
    urllib3 doesn't have standard method to measure latency, workaround using time
    """
    start = time.time()
    try:
        http.request('GET', endpoint, retries=urllib3.util.Retry(
            connect=0, read=0, status=1, redirect=10), timeout=urllib3.util.Timeout(connect=5, read=60))
    except:
        logger.error("Timeouts occured while trying to measure latency")
    end = time.time()
    delta = end - start
    elapsed_seconds = round(delta, 6)
    latQ.put(elapsed_seconds)


@tracer.capture_method
def latency(endpoint: str, latencyConstraint: float) -> dict:
    latencyQ = queue.Queue()
    threads = [
        Thread(
            target=measure_latency,
            args=(endpoint, latencyQ)
        ) for x in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lat_list = []
    while not latencyQ.empty():
        lat_list.append(latencyQ.get())

    return {"latency": float(sum(lat_list) / len(lat_list)), "status": "ok" if float(sum(lat_list) / len(lat_list)) <= latencyConstraint else "ko"}


@tracer.capture_method
def connectivity_and_test(endpoint: str, testString: str) -> dict:
    retries = urllib3.util.Retry(connect=1, read=1, redirect=10)
    timeout = urllib3.util.Timeout(connect=5, read=30)
    try:
        r = http.request('GET', endpoint, timeout=timeout, retries=retries)
    except Exception as e:
        logger.error(f"Connectivity issue to {endpoint}: {e}")
        return {"is_up": False, "message": e, "statusCode": 500}
    else:
        is_up = True if r.status == 200 else False
        try:
            message = None if testString in r.data.decode(
                r.headers['Content-Type'].split("; ")[1].split("=")[1]) else "Test string not found in response."
        except:
            message = "Test string not found in response. Failed decoding response."
        return {"is_up": is_up, "message": message, "statusCode": r.status}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.debug(
        f"Received Event: {event}"
    )
    try:
        siteId = event["siteId"]
        url = event["endpoint"]
        testString = event["testString"]
        latencyConstraint = float(event["latencyConstraint"])

    except:
        logger.error(
            f"Missing Parameters!"
        )
        raise RuntimeError(
            "Missing parameters!"
        )

    connectivity = connectivity_and_test(url, testString)

    if connectivity["is_up"]:
        endpoint_latency = latency(url, latencyConstraint)
        write_records(siteId, connectivity["is_up"], {"avg_lat": endpoint_latency["latency"],
                                                      "status": endpoint_latency["status"]}, connectivity["message"], connectivity["statusCode"])
    else:
        write_records(siteId, connectivity["is_up"], {
                      "avg_lat": None, "status": None}, connectivity["message"], connectivity["statusCode"])

    return
