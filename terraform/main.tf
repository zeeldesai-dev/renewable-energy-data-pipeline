# Terraform Configuration for Renewable Energy Data Pipeline
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "renewable-energy-pipeline"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "bucket_name" {
  description = "S3 bucket name for energy data"
  type        = string
  default     = "renewable-energy-data-pipeline"
}

variable "lambda_function_name" {
  description = "Lambda function name"
  type        = string
  default     = "energy-data-processor"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name"
  type        = string
  default     = "energy-data"
}

variable "notification_email" {
  description = "Email for notifications"
  type        = string
  default     = "admin@example.com"
}

# S3 Bucket for Energy Data
resource "aws_s3_bucket" "energy_data" {
  bucket = "${var.bucket_name}-${random_suffix.bucket.result}"
}

resource "random_suffix" "bucket" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket_versioning" "energy_data" {
  bucket = aws_s3_bucket.energy_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "energy_data" {
  bucket = aws_s3_bucket.energy_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "energy_data" {
  bucket = aws_s3_bucket.energy_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB Table for Processed Energy Data
resource "aws_dynamodb_table" "energy_data" {
  name           = var.dynamodb_table_name
  billing_mode   = "ON_DEMAND"
  hash_key       = "site_id"
  range_key      = "timestamp"

  attribute {
    name = "site_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # Global Secondary Index for querying by timestamp
  global_secondary_index {
    name            = "timestamp-index"
    hash_key        = "timestamp"
    projection_type = "ALL"
  }

  # Tags
  tags = {
    Name = "energy-data-table"
  }
}

# IAM Role for Lambda Function
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.lambda_function_name}-execution-role"

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
}

# IAM Policy for Lambda Function
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.lambda_function_name}-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.energy_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.energy_data.arn,
          "${aws_dynamodb_table.energy_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.energy_alerts.arn
      }
    ]
  })
}

# Attach basic execution role to Lambda
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14
}

# SNS Topic for Alerts
resource "aws_sns_topic" "energy_alerts" {
  name = "energy-anomaly-alerts"
  
  tags = {
    Name = "energy-anomaly-alerts"
  }
}

# SNS Topic Subscription
resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.energy_alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# Lambda Function (placeholder - code needs to be uploaded separately)
resource "aws_lambda_function" "energy_processor" {
  filename         = "lambda_function.zip"
  function_name    = var.lambda_function_name
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.energy_data.name
      SNS_TOPIC_ARN      = aws_sns_topic.energy_alerts.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda_logs,
  ]

  # Note: lambda_function.zip needs to be created separately
  lifecycle {
    ignore_changes = [filename]
  }
}

# S3 Bucket Notification to trigger Lambda
resource "aws_s3_bucket_notification" "energy_data_notification" {
  bucket = aws_s3_bucket.energy_data.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.energy_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "energy_data/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# Lambda permission for S3 to invoke function
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.energy_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.energy_data.arn
}

# CloudWatch Log Group for Error Handling
resource "aws_cloudwatch_log_group" "error_logs" {
  name              = "energy-pipeline-errors"
  retention_in_days = 30
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "energy_pipeline" {
  dashboard_name = "energy-pipeline-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Function Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", var.dynamodb_table_name],
            [".", "ConsumedWriteCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "DynamoDB Metrics"
          period  = 300
        }
      }
    ]
  })
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.energy_data.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.energy_data.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.energy_data.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.energy_data.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.energy_processor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.energy_processor.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.energy_alerts.arn
}

output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.energy_pipeline.dashboard_name}"
}