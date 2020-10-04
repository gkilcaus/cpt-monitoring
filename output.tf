output "dynamodb" {
  value       = aws_dynamodb_table.monitoring_config.name
  description = "DynamoDB Table name used for Configuration"
}