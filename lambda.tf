### Monitoring Lambda
data "archive_file" "monitoring_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambdas/monitoring/monitoring.py"
  output_path = "${path.module}/temp/monitoring.zip"
}


resource "aws_lambda_function" "cpt_monitoring_lambda" {
  function_name    = "cpt-monitoring"
  handler          = "monitoring.lambda_handler"
  role             = aws_iam_role.cpt_lambda_monitoring.arn
  runtime          = "python3.8"
  timeout          = "300"
  memory_size      = 512
  source_code_hash = data.archive_file.monitoring_lambda.output_base64sha256
  filename         = data.archive_file.monitoring_lambda.output_path
  publish          = true
  layers           = [aws_lambda_layer_version.powertools.arn]
  environment {
    variables = {
      TS_Database = var.timestream_database
      TS_Table    = var.timestream_table
    }
  }
  tracing_config {
    mode = "Active"
  }
}

resource "aws_lambda_permission" "cpt_monitoring_eventbridge_events" {
  statement_id  = "AllowExecutionFromCloudWatchEvents"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cpt_monitoring_lambda.function_name
  principal     = "events.amazonaws.com"
}


### Configuration Lambda

resource "aws_lambda_event_source_mapping" "configdbstream_to_configlambda" {
  event_source_arn       = aws_dynamodb_table.monitoring_config.stream_arn
  function_name          = aws_lambda_alias.cpt_configuration_lambda_alias.arn
  starting_position      = "LATEST"
  batch_size             = 1
  maximum_retry_attempts = 0
}

data "archive_file" "configuration_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambdas/configuration/configuration.py"
  output_path = "${path.module}/temp/configuration.zip"
}


resource "aws_lambda_function" "cpt_configuration_lambda" {
  function_name    = "cpt-monitoring-configuration"
  handler          = "configuration.lambda_handler"
  role             = aws_iam_role.cpt_lambda_configuration.arn
  runtime          = "python3.8"
  timeout          = "300"
  memory_size      = 512
  source_code_hash = data.archive_file.configuration_lambda.output_base64sha256
  filename         = data.archive_file.configuration_lambda.output_path
  publish          = true
  layers           = [aws_lambda_layer_version.powertools.arn]
  environment {
    variables = {
      MONITORING_LAMBDA_ARN = aws_lambda_function.cpt_monitoring_lambda.arn
    }
  }
  tracing_config {
    mode = "Active"
  }
}

resource "aws_lambda_alias" "cpt_configuration_lambda_alias" {
  name             = "cpt_configuration_latest"
  description      = "Alias to newest version of cpt configuration lambda"
  function_name    = aws_lambda_function.cpt_configuration_lambda.arn
  function_version = aws_lambda_function.cpt_configuration_lambda.version
  routing_config {}
}