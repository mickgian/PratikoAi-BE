# PratikoAI MCP Server - AWS Deployment Guide

## 🎯 AWS Startup Strategy: 92% Cost Reduction in Year 1!

This guide shows you how to deploy your PratikoAI MCP server infrastructure on AWS with maximum cost optimization for startups.

### 💰 Cost Comparison

| Phase | Original Setup | AWS First Year | AWS After Year 1 | Savings |
|-------|----------------|----------------|------------------|---------|
| Development | $0 | $0 | $0 | Same |
| Staging | $24/month | $0/month | $29.50/month | $288 saved in year 1 |
| Production | $5/month | $2.30/month | $31.80/month | $32.40 saved in year 1 |
| **TOTAL** | **$29/month** | **$2.30/month** | **$61.30/month** | **$320+ saved in year 1** |

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** (free tier eligible recommended)
   ```bash
   # Sign up at https://aws.amazon.com/
   # New accounts get 12 months of free tier
   ```

2. **AWS CLI** 
   ```bash
   # macOS
   brew install awscli
   
   # Or download from https://aws.amazon.com/cli/
   ```

3. **Configure AWS CLI**
   ```bash
   aws configure
   # Enter your Access Key ID
   # Enter your Secret Access Key  
   # Choose region: us-east-1 (has most free tier services)
   # Output format: json
   ```

4. **Docker Desktop** (for local development)
   ```bash
   # Download from https://www.docker.com/products/docker-desktop
   ```

### One-Command Setup

```bash
./scripts/provision-aws-startup.sh
```

This interactive script will guide you through all three phases.

## 📱 Phase 1: Local Development (FREE)

**Cost: $0/month**

### What You Get
- Local development environment on your Mac
- AWS S3 integration for file storage
- CloudWatch for logging and monitoring
- Perfect for development, testing, and demos

### Setup Steps

1. **Run the provisioning script**:
   ```bash
   ./scripts/provision-aws-startup.sh
   # Choose option 1: Local Development + AWS Free Services
   ```

2. **What it creates**:
   - Docker Compose setup with AWS integration
   - S3 bucket for development files
   - Local containers: MCP server, PostgreSQL, Redis
   - Optional LocalStack for AWS service emulation

3. **Access your services**:
   ```bash
   # MCP Server
   curl http://localhost:8080/health
   
   # Check S3 integration
   aws s3 ls s3://your-dev-bucket-name
   ```

### Development Commands

```bash
# View logs
docker-compose -f docker-compose.local-aws.yml logs -f

# Stop services
docker-compose -f docker-compose.local-aws.yml down

# Clean up (removes data)
docker-compose -f docker-compose.local-aws.yml down -v
```

## 🏗️ Phase 2: AWS Free Tier Staging ($0 first year)

**Cost: $0/month for first 12 months, then ~$29.50/month**

### What You Get
- EC2 t3.micro instance (750 hours/month free)
- RDS PostgreSQL db.t3.micro (750 hours/month free) 
- Application Load Balancer
- S3 storage (5GB free + additional as needed)
- CloudWatch monitoring (free tier)
- Auto Scaling Group (scales 1-2 instances)

### Free Tier Limits
- **EC2**: 750 hours/month t3.micro (enough for 1 instance 24/7)
- **RDS**: 750 hours/month db.t3.micro + 20GB storage
- **S3**: 5GB storage + 20,000 GET + 2,000 PUT requests/month
- **Data Transfer**: 1GB/month free outbound

### Setup Steps

1. **Run the provisioning script**:
   ```bash
   ./scripts/provision-aws-startup.sh
   # Choose option 2: AWS Free Tier Staging
   ```

2. **The script will**:
   - Create CloudFormation templates
   - Deploy VPC with public/private subnets
   - Set up EC2 Auto Scaling Group
   - Create RDS PostgreSQL database
   - Configure Application Load Balancer
   - Set up S3 bucket with proper permissions

3. **Access your staging environment**:
   ```bash
   # Your application will be available at:
   # http://your-load-balancer-dns-name
   
   # Health check
   curl http://your-load-balancer-dns-name/health
   ```

### Monitoring Your Free Tier Usage

```bash
# Check EC2 usage
aws ec2 describe-instances --query 'Reservations[].Instances[?State.Name==`running`].[InstanceId,InstanceType,LaunchTime]' --output table

# Check RDS usage  
aws rds describe-db-instances --query 'DBInstances[?DBInstanceStatus==`available`].[DBInstanceIdentifier,DBInstanceClass,InstanceCreateTime]' --output table

# Check S3 usage
aws s3api list-buckets --output table
aws s3 ls s3://your-bucket-name --recursive --human-readable --summarize
```

### What Happens After 12 Months

When your free tier expires, costs will be:
- **EC2 t3.micro**: ~$8.50/month
- **RDS db.t3.micro**: ~$13/month  
- **Load Balancer**: ~$16/month
- **S3**: ~$1/month (for typical usage)
- **Total**: ~$38.50/month

## 🎯 Phase 3: AWS Serverless Production ($2.30/month)

**Cost: $2.30/month first year, ~$32/month after**

### What You Get
- **AWS Lambda**: 1M requests/month free (more than enough to start)
- **API Gateway**: 1M requests/month free
- **DynamoDB**: 25GB storage + 25 RCU/WCU free
- **S3**: 5GB free + additional as needed ($2.30/month for 100GB)
- **CloudFront CDN**: 1TB transfer/month free
- **CloudWatch**: 10 custom metrics + 5GB logs free

### Serverless Benefits
- **Auto-scaling**: Scales from 0 to thousands automatically
- **No server management**: AWS handles all infrastructure
- **Pay per request**: Only pay for what you use
- **Global distribution**: CloudFront CDN worldwide
- **High availability**: Built-in redundancy

### Setup Steps

1. **Install AWS SAM CLI** (optional but recommended):
   ```bash
   # macOS
   brew install aws-sam-cli
   
   # Or manually: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
   ```

2. **Run the provisioning script**:
   ```bash
   ./scripts/provision-aws-startup.sh
   # Choose option 3: AWS Serverless Production MVP
   ```

3. **Deploy using SAM**:
   ```bash
   cd aws/sam
   sam build
   sam deploy --guided
   ```

4. **Or deploy using CloudFormation directly**:
   ```bash
   aws cloudformation deploy \
     --template-file aws/sam/template.yaml \
     --stack-name pratiko-mcp-prod \
     --capabilities CAPABILITY_IAM \
     --region us-east-1
   ```

### Architecture Overview

```
Internet → CloudFront → API Gateway → Lambda Functions
                                   ↓
                              DynamoDB (data)
                                   ↓
                              S3 (file storage)
```

### Monitoring Serverless Usage

```bash
# Lambda invocations
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/pratiko-mcp"

# DynamoDB usage
aws dynamodb describe-table --table-name pratiko-mcp-prod --query 'Table.BillingModeSummary'

# API Gateway requests
aws apigateway get-usage --usage-plan-id your-usage-plan-id --key-id your-key-id
```

### Free Tier Limits for Serverless

- **Lambda**: 1M requests + 400,000 GB-seconds compute time/month
- **API Gateway**: 1M requests/month
- **DynamoDB**: 25GB storage + 25 RCU + 25 WCU/month
- **CloudFront**: 1TB data transfer + 10M HTTP/HTTPS requests/month
- **S3**: 5GB storage + 20,000 GET + 2,000 PUT requests/month

## 📈 Scaling Strategy

### When to Scale Up

| Metric | MVP Limit | Action |
|--------|-----------|--------|
| Lambda requests | 1M/month | Upgrade to paid tier (~$20/month at 5M requests) |
| DynamoDB RCU/WCU | 25 each | Increase capacity (~$25/month for 100 each) |
| S3 storage | 100GB | Pay per GB (~$2.30/month per 100GB) |
| API Gateway requests | 1M/month | Pay per request (~$3.50 per million) |

### Revenue-Based Scaling

| Monthly Revenue | Infrastructure Cost | % of Revenue |
|----------------|-------------------|--------------|
| $0 - $500 | $2.30 | 0.5% |
| $500 - $2,000 | $30 | 1.5% |
| $2,000 - $10,000 | $150 | 1.5% |
| $10,000+ | $500+ | 5% |

**Rule**: Keep infrastructure costs under 5% of revenue.

## 🔧 Advanced Configuration

### Custom Domain Setup

1. **Register domain** (Route 53 or external):
   ```bash
   # If using Route 53
   aws route53domains register-domain --domain-name yourdomain.com
   ```

2. **Request SSL certificate**:
   ```bash
   aws acm request-certificate \
     --domain-name yourdomain.com \
     --domain-name "*.yourdomain.com" \
     --validation-method DNS
   ```

3. **Update CloudFormation/SAM template** with custom domain configuration.

### Environment Variables Management

Use AWS Systems Manager Parameter Store (free tier: 10,000 parameters):

```bash
# Store configuration
aws ssm put-parameter \
  --name "/pratiko-mcp/prod/jwt-secret" \
  --value "your-jwt-secret" \
  --type "SecureString"

# Retrieve in Lambda
import boto3
ssm = boto3.client('ssm')
jwt_secret = ssm.get_parameter(Name='/pratiko-mcp/prod/jwt-secret', WithDecryption=True)['Parameter']['Value']
```

### Monitoring and Alerting

Set up CloudWatch alarms for key metrics:

```bash
# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "pratiko-mcp-lambda-errors" \
  --alarm-description "Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### Backup Strategy

**Automated Backups (Free/Low Cost)**:

1. **DynamoDB Point-in-Time Recovery**: Free (up to 35 days)
2. **S3 Versioning**: Enabled by default in templates
3. **Lambda function code**: Stored in S3 automatically
4. **CloudFormation templates**: Version controlled in Git

### Security Best Practices

1. **IAM Roles**: Minimal permissions (implemented in templates)
2. **VPC**: Private subnets for databases (staging environment)
3. **Encryption**: At rest and in transit (enabled by default)
4. **Secrets Management**: AWS Secrets Manager for sensitive data
5. **WAF**: AWS WAF for API protection (can be added later)

## 🚨 Cost Monitoring and Alerts

### Set Up Billing Alerts

1. **Enable billing alerts** in AWS Console
2. **Create CloudWatch billing alarm**:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name "pratiko-mcp-billing" \
     --alarm-description "Monthly billing alert" \
     --metric-name EstimatedCharges \
     --namespace AWS/Billing \
     --statistic Maximum \
     --period 86400 \
     --threshold 50 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 1 \
     --dimensions Name=Currency,Value=USD
   ```

### Monthly Cost Review

```bash
# Get current month costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## 🆘 Troubleshooting

### Common Issues

1. **Lambda timeout**: Increase timeout in SAM template
2. **DynamoDB throttling**: Increase RCU/WCU or use on-demand billing
3. **API Gateway 502 errors**: Check Lambda function logs
4. **S3 access denied**: Verify IAM permissions and bucket policies

### Getting Help

- **AWS Free Tier Usage**: AWS Console → Billing → Free Tier
- **AWS Support**: Basic support is free
- **AWS Documentation**: https://docs.aws.amazon.com/
- **Community**: AWS re:Post (https://repost.aws/)

## 📚 Additional Resources

### AWS Cost Optimization
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Cost Optimization Hub](https://aws.amazon.com/aws-cost-management/cost-optimization/)

### Serverless Best Practices
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Serverless Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/)

### Monitoring and Observability
- [AWS X-Ray for distributed tracing](https://aws.amazon.com/xray/)
- [AWS CloudWatch Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)

---

## 🎉 Summary

You now have a complete AWS-based infrastructure that:

✅ **Costs only $2.30/month** in the first year  
✅ **Scales automatically** from 0 to thousands of users  
✅ **Uses AWS free tier** to maximize savings  
✅ **Provides enterprise-grade** reliability and security  
✅ **Includes monitoring** and logging out of the box  
✅ **Can grow with your business** without major rewrites  

**Next Steps**:
1. Run `./scripts/provision-aws-startup.sh`
2. Start with local development (Phase 1)
3. Deploy staging when ready for demos (Phase 2) 
4. Launch production when you have customers (Phase 3)

**Remember**: AWS free tier gives you 12 months to validate your business idea with minimal infrastructure costs!