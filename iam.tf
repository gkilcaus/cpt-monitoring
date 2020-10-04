### Assume policy for lambdas
data "aws_iam_policy_document" "lambda_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

### IAM Role for Monitoring Lambda
resource "aws_iam_role" "cpt_lambda_monitoring" {
  name                 = "CPT-Lambda-WebsiteMonitoring"
  description          = "Role for Website Monitoring Lambda"
  max_session_duration = 43200

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "cpt_lambda_basic_execution" {
  role       = aws_iam_role.cpt_lambda_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "cpt_lambda_xray" {
  role       = aws_iam_role.cpt_lambda_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

data "aws_iam_policy_document" "cpt_monitoring_additional" {
  statement {
    sid = "timestreamwrite"

    actions = [
      "timestream:WriteRecords",
      "timestream:DescribeEndpoints"
    ]

    resources = [
      "*"
    ]
  }
}

resource "aws_iam_policy" "cpt_lambda_monitoring_additional" {
  name        = "CPT-Pol-MonitoringAdditional"
  path        = "/"
  description = "Additional permissions for Monitoring Lambda"
  policy      = data.aws_iam_policy_document.cpt_monitoring_additional.json
}

resource "aws_iam_role_policy_attachment" "cpt_lambda_additional" {
  role       = aws_iam_role.cpt_lambda_monitoring.name
  policy_arn = aws_iam_policy.cpt_lambda_monitoring_additional.arn
}

### IAM Role for Configuration Lambda
resource "aws_iam_role" "cpt_lambda_configuration" {
  name                 = "CPT-Lambda-WebsiteMonitoringConfiguration"
  description          = "Role for Website Monitoring Configuration Lambda"
  max_session_duration = 43200

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "cpt_lambdacfg_basic_execution" {
  role       = aws_iam_role.cpt_lambda_configuration.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "cpt_lambdacfg_xray" {
  role       = aws_iam_role.cpt_lambda_configuration.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

data "aws_iam_policy_document" "cpt_configuration_additional" {
  statement {
    sid = "dynamodbread"

    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:DescribeStream",
      "dynamodb:ListStreams",
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator"
    ]

    resources = [
      aws_dynamodb_table.monitoring_config.arn,
      aws_dynamodb_table.monitoring_config.stream_arn
    ]
  }

  statement {
    sid = "eventbridge"

    actions = [
      "events:DeleteRule",
      "events:DescribeRule",
      "events:ListRules",
      "events:PutTargets",
      "events:RemoveTargets",
      "events:PutRule",
      "events:ListTargetsByRule"
    ]

    resources = [
      "*"
    ]
  }
}

resource "aws_iam_policy" "cpt_lambda_configuration_additional" {
  name        = "CPT-Pol-MonitoringCFGAdditional"
  path        = "/"
  description = "Additional permissions for Monitoring Configuration Lambda"
  policy      = data.aws_iam_policy_document.cpt_configuration_additional.json
}

resource "aws_iam_role_policy_attachment" "cpt_lambdacfg_additional" {
  role       = aws_iam_role.cpt_lambda_configuration.name
  policy_arn = aws_iam_policy.cpt_lambda_configuration_additional.arn
}