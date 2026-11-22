variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Name prefix for resources"
  type        = string
  default     = "final-webapp"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability Zones used by the subnets"
  type        = list(string)
  default     = ["eu-central-1a", "eu-central-1b"]
}

variable "public_subnet_cidrs" {
  description = "Public subnets (ALB, NAT Gateway)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "app_subnet_cidrs" {
  description = "Private application subnets (ECS Fargate)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "db_subnet_cidrs" {
  description = "Private database subnets (RDS)"
  type        = list(string)
  default     = ["10.0.21.0/24", "10.0.22.0/24"]
}

variable "container_port" {
  description = "Port the application listens on"
  type        = number
  default     = 8000
}

variable "image_tag" {
  description = "Docker image tag to deploy from ECR"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate task memory (MiB)"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Initial number of ECS tasks"
  type        = number
  default     = 1
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "webapp"
}

variable "db_username" {
  description = "Master username of the database"
  type        = string
  default     = "webapp_admin"
}

variable "db_backup_retention_days" {
  description = "RDS automated backup retention (days)"
  type        = number
  default     = 7
}

variable "alert_email" {
  description = "Email for CloudWatch alarms and budget notifications"
  type        = string
  default     = "vizarsky@gmail.com"
}

variable "budget_limit_usd" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 15
}
