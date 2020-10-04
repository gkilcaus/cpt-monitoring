### Timestream not supported by Terraform AWS provider. Workaround using cloudformation
#resource "aws_cloudformation_stack" "timestream" {
#  name = "cpt-monitoring-timestream"
#
#  template_body = file("${path.module}/files/timestream.yml")
#}

### Update: Commenting this out because currently Timestream resources stopped working even with CLoudformation