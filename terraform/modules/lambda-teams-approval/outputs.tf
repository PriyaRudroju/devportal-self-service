output "api_gateway_url" {
  description = "Base URL for Port action webhooks and Teams approval links"
  value       = "https://${aws_apigatewayv2_api.teams_approval.id}.execute-api.${var.aws_region}.amazonaws.com"
}

output "ec2_request_url" {
  description = "Webhook URL for Port change-ec2-instance self-service action"
  value       = "https://${aws_apigatewayv2_api.teams_approval.id}.execute-api.${var.aws_region}.amazonaws.com/ec2/request"
}

output "approval_decision_url" {
  description = "Base URL for Teams Approve/Reject links (append ?runId=...&decision=approve|reject)"
  value       = "https://${aws_apigatewayv2_api.teams_approval.id}.execute-api.${var.aws_region}.amazonaws.com/approval-decision"
}

output "lambda_function_name" {
  description = "Deployed Lambda function name"
  value       = aws_lambda_function.teams_approval.function_name
}
