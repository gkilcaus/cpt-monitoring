# Website monitoring

## Requirements
- AWS CLI v2 (make sure it's latest version)
- AWS Credentials configured (cli / terraform assumes you're using default profile)
- terraform (latest version available, i.e. 0.13.4)
- git
- python 3.8 (optional)

## How to
1. Clone this repository
2. Create Amazon Timestream database (currently neither Terraform not Cloudformation supports it)
```
aws timestream-write create-database --database-name CPTMonitoring
aws timestream-write create-table --database-name CPTMonitoring --table-name WebsiteMonitoringData
```
3. cd into cloned repository and run:
```
terraform init
terraform apply
```
Note: Update variable defaults if you've changed database and table names when creating Timestream objects above. 
4. add few entries into configuration database:
```
aws dynamodb batch-write-item --request-items file://dynamo_entries.json
```
5. After some time check Amazon Timestream console for records

## How it works
Configuration DynamoDB table is configured to stream all changes to Configuration lambda which modifies EventBridge rules to trigger monitoring lambda (with individual input body). Then rule is triggered at rate defined in configuration (minimum 1 minute). Triggered monitoring lambda check connectivity, latency (average of 5 requests), status code, error messages and then stores that information into Amazon Timestream database. Current implementation is missing UI for displaying results, but this can be easily extended with quicksight, grafana, which works out of the box with Amazon Timestream.
On top of standard libraries coming with python lambda environment, lambda powertools & xray-sdk (for logging and tracing) were built into lambda layer.


## What's next
- UI for showing results
  - QuickSight/Grafana could be used for limited number internal users
  - dedicated serverless website (i.e. SPA hosted on S3/Cloudfront + backend API via APIGAteway/Lambda) for wider audience. Authentication/Authorization could be achieved using Cognito (either managed within cognito or external idp)
- urllib3 library used for connectivity checks is pretty basic and could be replaced with more sophisticated one (i.e. requests). urllib3 was selected because it comes out of the box with Lambda and doesn't need to be packaged
  - improvements to checks' logic, better error handling
- For better scaling, writing to Timestream table should be made as separate Lambda and detached from actual monitoring lambda
- AWS Limits should be increased for Lambda concurrency.
  - Reserved concurrency configured for selected lambdas to minimize impact of cold starts.
- Optimizations to lambda resources based on analysis of tracing data
- To extend checks to different regions, monitoring lambda should be deployed to those regions and configuration database/lambda extended to include new regions.
- To overcome minimum 1min rate, EventBridge rules should be replaced -- for example adding Steps Functions could help to achieve this
- UI for configuration management. DynamoDB could be made Global to have better latency for users managing records.
  - Latency for configuring triggers for global checks is not that relevant
- Security:
  - Minimal permissions for IAM Roles used
  - separate Timestream databases/tables for individual customers
  - Segregation of access at frontend application layer
  - retention policy per customer
  - encryption of data using Customer Managed Keys
- deployments utilizing Infrastructure as a Code (i.e. Terraform) with CI/CD utilizing either tool like Jenkins or CodePipeline