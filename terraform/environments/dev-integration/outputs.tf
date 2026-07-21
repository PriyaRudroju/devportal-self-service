output "api_gateway_url" {
  value = module.teams_approval.api_gateway_url
}

output "approval_request_url" {
  value       = module.teams_approval.approval_request_url
  description = "Use this URL in port/automations/notify-teams-on-approval-request.json"
}

output "lambda_function_name" {
  value = module.teams_approval.lambda_function_name
}
