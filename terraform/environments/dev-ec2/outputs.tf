output "instance_id" {
  value = module.ec2_instance.instance_id
}

output "private_ip" {
  value = module.ec2_instance.private_ip
}

output "public_ip" {
  value = module.ec2_instance.public_ip
}
