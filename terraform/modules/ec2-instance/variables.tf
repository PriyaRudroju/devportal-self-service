variable "instance_name" {
  type        = string
  description = "Name tag for the EC2 instance"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type"
  default     = "t3.micro"
}

variable "tags" {
  type        = map(string)
  description = "Additional resource tags"
  default     = {}
}
