output "api_gateway_url" {
  description = "Base URL for Port automation webhooks and Teams approval links"
  value       = "https://${aws_apigatewayv2_api.teams_approval.id}.execute-api.${var.aws_region}.amazonaws.com"
}

output "approval_request_url" {
  description = "Webhook URL for Port notify-teams automation"
  value       = "https://${aws_apigatewayv2_api.teams_approval.id}.execute-api.${var.aws_region}.amazonaws.com/teams/approval-request"
}

output "lambda_function_name" {
  description = "Deployed Lambda function name"
  value       = aws_lambda_function.teams_approval.function_name
}
