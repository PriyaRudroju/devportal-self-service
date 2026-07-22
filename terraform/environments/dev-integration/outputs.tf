output "api_gateway_url" {
  value = module.teams_approval.api_gateway_url
}

output "ec2_request_url" {
  value       = module.teams_approval.ec2_request_url
  description = "Use this URL in port/actions/change-ec2-instance.json"
}

output "approval_decision_url" {
  value       = module.teams_approval.approval_decision_url
  description = "Use in Teams Workflow Approve/Reject links"
}

output "lambda_function_name" {
  value = module.teams_approval.lambda_function_name
}
