terraform {
  backend "s3" {
    bucket       = "anne834-oracle-revenue-tfstate"
    key          = "oracle-revenue-pipeline/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}