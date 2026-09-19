# ── Provider Configuration ─────────────────────────────────────────────
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

# ── S3 Bucket ──────────────────────────────────────────────────────────
resource "aws_s3_bucket" "oracle_pipeline" {
  bucket = "oracle-revenue-pipeline-tf"

  tags = {
    Name        = "Oracle Revenue Pipeline"
    Environment = "Dev"
    Project     = "Revenue Leakage Detection"
  }
}

# ── IAM Role for Lambda ────────────────────────────────────────────────
resource "aws_iam_role" "lambda_role" {
  name = "oracle-lambda-role-tf"

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

# ── Attach S3 Full Access to Lambda Role ───────────────────────────────
resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# ── Attach Basic Lambda Execution Role ────────────────────────────────
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ── Lambda Function 1: Data Generator ─────────────────────────────────
resource "aws_lambda_function" "data_generator" {
  filename      = "generator.zip"
  function_name = "oracle-revenue-pipeline-tf"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30

  tags = {
    Project = "Revenue Leakage Detection"
  }
}

# ── Lambda Function 2: Data Processor ─────────────────────────────────
resource "aws_lambda_function" "data_processor" {
  filename      = "processor.zip"
  function_name = "oracle-pipeline-processor-tf"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30

  tags = {
    Project = "Revenue Leakage Detection"
  }
}

# ── IAM Role for Step Functions ────────────────────────────────────────
resource "aws_iam_role" "step_functions_role" {
  name = "oracle-stepfunctions-role-tf"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# ── Attach Lambda Invoke Permission to Step Functions ──────────────────
resource "aws_iam_role_policy_attachment" "step_functions_lambda" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
}

# ── Step Functions State Machine ───────────────────────────────────────
resource "aws_sfn_state_machine" "pipeline" {
  name     = "oracle-revenue-pipeline-orchestrator-tf"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = jsonencode({
    Comment = "Oracle Revenue Leakage Detection Pipeline"
    StartAt = "GenerateData"
    States = {
      GenerateData = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.data_generator.function_name
          Payload = {
            source = "step-functions"
          }
        }
        ResultPath = "$.generateResult"
        Next       = "ProcessData"
      }
      ProcessData = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.data_processor.function_name
          Payload = {
            date = "2026-09-19"
          }
        }
        ResultPath = "$.processResult"
        End        = true
      }
    }
  })

  tags = {
    Project = "Revenue Leakage Detection"
  }
}

# ── EventBridge Schedule ───────────────────────────────────────────────
resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "oracle-daily-pipeline-trigger-tf"
  description         = "Triggers Oracle revenue pipeline daily at midnight"
  schedule_expression = "cron(0 0 * * ? *)"
}

resource "aws_cloudwatch_event_target" "trigger_step_functions" {
  rule      = aws_cloudwatch_event_rule.daily_trigger.name
  target_id = "OraclePipelineTarget"
  arn       = aws_sfn_state_machine.pipeline.arn
  role_arn  = aws_iam_role.step_functions_role.arn
}