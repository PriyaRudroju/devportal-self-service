data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = var.lambda_source_path
  output_path = "${path.module}/teams-approval.zip"
}

resource "aws_iam_role" "lambda" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
  tags              = var.tags
}

resource "aws_lambda_function" "teams_approval" {
  function_name = var.function_name
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      TEAMS_WEBHOOK_URL    = var.teams_webhook_url
      PORT_CLIENT_ID       = var.port_client_id
      PORT_CLIENT_SECRET   = var.port_client_secret
      PORT_API_URL         = var.port_api_url
      API_GATEWAY_BASE_URL = "https://${aws_apigatewayv2_api.teams_approval.id}.execute-api.${var.aws_region}.amazonaws.com"
      GITHUB_TOKEN         = var.github_token
      GITHUB_ORG           = var.github_org
      GITHUB_REPO          = var.github_repo
      GIT_REF_DEFAULT      = var.git_ref_default

      SERVICENOW_INSTANCE_URL        = var.servicenow_instance_url
      SERVICENOW_USERNAME            = var.servicenow_username
      SERVICENOW_PASSWORD            = var.servicenow_password
      SERVICENOW_CATALOG_ITEM_SYS_ID = var.servicenow_catalog_item_sys_id
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = var.tags
}

resource "aws_apigatewayv2_api" "teams_approval" {
  name          = "${var.function_name}-api"
  protocol_type = "HTTP"
  tags          = var.tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.teams_approval.id
  name        = "$default"
  auto_deploy = true
  tags        = var.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.teams_approval.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.teams_approval.invoke_arn
  payload_format_version = "2.0"
  integration_method     = "POST"
}

resource "aws_apigatewayv2_route" "teams_notify" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "POST /teams/notify"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "s3_validate_git_ref" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "POST /s3/validate-git-ref"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "s3_mark_ready" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "POST /s3/mark-ready"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "servicenow_create_request" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "POST /servicenow/create-request"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "ec2_request" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "POST /ec2/request"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "approval_decision_get" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "GET /approval-decision"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "approval_decision_post" {
  api_id    = aws_apigatewayv2_api.teams_approval.id
  route_key = "POST /approval-decision"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.teams_approval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.teams_approval.execution_arn}/*/*"
}
