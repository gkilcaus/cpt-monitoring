resource "aws_dynamodb_table" "monitoring_config" {
  name             = "WSMonitoringConfig"
  hash_key         = "SiteId"
  billing_mode     = "PAY_PER_REQUEST"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "SiteId"
    type = "S"
  }
}