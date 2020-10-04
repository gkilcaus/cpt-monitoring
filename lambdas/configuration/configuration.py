import boto3
import os
from aws_lambda_powertools import Tracer, Logger
from botocore import config
from botocore.client import Config
from botocore.exceptions import ClientError

tracer = Tracer(service="cpt-monitoring-config")
logger = Logger(
    service="cpt-monitoring-config", level=os.environ.get("LOG_LEVEL", "INFO")
)

# this will prevent long timeouts
BOTO3_CONFIG = Config(connect_timeout=5, retries={"max_attempts": 0})

RULE_PREFIX = "CPT_WSMon_RULE_"

MONITORING_LAMBDA_ARN = os.environ['MONITORING_LAMBDA_ARN']

eventBridge_client = boto3.client('events', config=BOTO3_CONFIG)


@tracer.capture_method
def insert_update_rule(ebr_client, newData):
    """
    Processes inserts or updates to Configuration records in DynamoDB
    """
    try:
        rateStr = "1 minute" if newData['rate']['N'] == 1 else f"{newData['rate']['N']} minutes"
        rule_response = ebr_client.put_rule(
            Name=f"{RULE_PREFIX}{newData['SiteId']['S']}",
            State='ENABLED',
            Description=f"CPT Monitorint trigger for {newData['SiteId']['S']}",
            ScheduleExpression='rate(' + rateStr + ')'
        )
        logger.debug(f"Rule Creation/Update Response: {rule_response}")

        target_response = ebr_client.put_targets(
            Rule=f"{RULE_PREFIX}{newData['SiteId']['S']}",
            Targets=[
                {
                    'Id': f"{RULE_PREFIX}{newData['SiteId']['S']}_Lambda_Target",
                    'Arn': MONITORING_LAMBDA_ARN,
                    'Input': '{ "siteId": "' + newData['SiteId']['S'] + '","endpoint":"' + newData['endpoint']['S'] + '","latencyConstraint":"' + newData['latencyConstraint']['N'] + '","testString":"' + newData['testString']['S'] + '"}',
                },
            ]
        )
        logger.debug(
            f"Target Creation/Update Response: {target_response}")
    except Exception as e:
        logger.error(f"Rule/Target creation/update failed: {e}")


@tracer.capture_method
def delete_rule(ebr_client, oldData):
    try:
        ruleName = f"{RULE_PREFIX}{oldData['SiteId']['S']}"
        rule = ebr_client.describe_rule(
            Name=ruleName
        )
        targets_list = ebr_client.list_targets_by_rule(
            Rule=rule['Name']
        )['Targets']
        ebr_client.remove_targets(
            Rule=rule['Name'],
            Ids=[target['Id'] for target in targets_list],
            Force=True
        )
        ebr_client.delete_rule(
            Name=rule['Name'],
            Force=True
        )
    except Exception as e:
        logger.error(
            f"Rule deletion failed: {e}"
        )


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.debug(
        f"Received Event: {event}"
    )

    try:
        ddb_records = event["Records"]
    except:
        logger.error(
            f"Received event does not contain Records."
        )
        raise

    for record in ddb_records:
        if record["eventName"] == "INSERT" or record["eventName"] == "MODIFY":
            insert_update_rule(eventBridge_client,
                               record['dynamodb']['NewImage'])
        elif record["eventName"] == "REMOVE":
            delete_rule(eventBridge_client, record['dynamodb']['OldImage'])

    return
