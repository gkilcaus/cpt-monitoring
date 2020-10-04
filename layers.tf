# Powertools
data "archive_file" "powertools" {
  type        = "zip"
  source_dir  = "${path.module}/lambdas/powertools"
  output_path = "${path.module}/temp/powertools.zip"
}

resource "aws_lambda_layer_version" "powertools" {
  filename            = data.archive_file.powertools.output_path
  layer_name          = "powertools"
  compatible_runtimes = ["python3.7", "python3.8"]
  source_code_hash    = data.archive_file.powertools.output_base64sha256
}