output "bucket_arn" {
  value = module.s3_bucket.bucket_arn
}

output "bucket_name" {
  value = module.s3_bucket.bucket_name
}

output "api_gateway_url" {
  description = "Put this in GitHub Environment API_GATEWAY_URL and port/environments/config.env after apply"
  value       = module.teams_approval.api_gateway_url
}
