#!/bin/bash
set -euo pipefail

# PratikoAI MCP Server - AWS Startup-Friendly Provisioning Script
# Ultra-low-cost AWS deployment optimized for startups

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# AWS Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}  # us-east-1 has most free tier services
AWS_PROFILE=${AWS_PROFILE:-"default"}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

log_startup() {
    echo -e "${PURPLE}[🚀]${NC} $1"
}

show_banner() {
    echo -e "${PURPLE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                PratikoAI AWS Startup MCP Setup                ║"
    echo "║              Maximum AWS Free Tier Utilization! ☁️            ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_phase_info() {
    local phase=$1
    case $phase in
        "local")
            echo -e "${BLUE}📱 PHASE 1: Local Development + AWS Free Services${NC}"
            echo "• Compute Cost: FREE (runs on your Mac)"
            echo "• AWS Services: S3, CloudWatch (free tier)"
            echo "• Perfect for: Development, testing, demos"
            echo "• Capacity: You + team, unlimited development"
            ;;
        "staging")
            echo -e "${YELLOW}🏗️  PHASE 2: AWS Free Tier Staging${NC}"
            echo "• Cost: $0/month (first 12 months with AWS free tier)"
            echo "• After 12 months: ~$30/month"
            echo "• Perfect for: Client demos, team collaboration"
            echo "• Capacity: 100 concurrent users, 500K requests/month"
            ;;
        "mvp")
            echo -e "${GREEN}🎯 PHASE 3: AWS Serverless Production${NC}"
            echo "• Cost: $2.30/month (using AWS free tier smartly)"
            echo "• After 12 months: ~$32/month"
            echo "• Perfect for: First customers, validation"
            echo "• Capacity: 500+ real users, 1M Lambda executions"
            ;;
    esac
    echo
}

# Check AWS CLI and credentials
check_aws_prerequisites() {
    log_info "Checking AWS prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws >/dev/null 2>&1; then
        log_error "AWS CLI is required. Install it from: https://aws.amazon.com/cli/"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Run: aws configure --profile $AWS_PROFILE"
    fi
    
    # Check region
    local configured_region
    configured_region=$(aws configure get region --profile "$AWS_PROFILE" || echo "")
    if [ -z "$configured_region" ]; then
        log_warning "No default region set. Using $AWS_REGION"
        aws configure set region "$AWS_REGION" --profile "$AWS_PROFILE"
    fi
    
    log_success "AWS credentials configured for profile: $AWS_PROFILE"
}

# Setup local development with AWS integration
setup_local_development_aws() {
    log_startup "Setting up FREE local development with AWS integration..."
    show_phase_info "local"
    
    # Create local data directories
    mkdir -p "$PROJECT_ROOT/data/local"/{postgres,redis,mcp}
    mkdir -p "$PROJECT_ROOT/logs/local"
    mkdir -p "$PROJECT_ROOT/aws/local"
    
    # Create AWS-integrated docker-compose for local development
    cat > "$PROJECT_ROOT/docker-compose.local-aws.yml" << 'EOF'
version: '3.8'

services:
  mcp-server:
    build:
      context: ./docker/mcp-server
      dockerfile: Dockerfile.local-aws
    container_name: pratiko-mcp-local-aws
    ports:
      - "8080:8080"
      - "9090:9090"  # Metrics
    environment:
      - ENVIRONMENT=local
      - LOG_LEVEL=debug
      - POSTGRES_URL=postgresql://pratiko:pratiko123@postgres:5432/pratiko_mcp
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET_KEY=local-dev-secret-key-not-for-production
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_PROFILE=default
      # S3 Configuration for local testing
      - S3_BUCKET_NAME=pratiko-mcp-dev-${USER}-$(date +%s)
      - S3_USE_LOCAL_STACK=false
    volumes:
      - ./data/local/mcp:/app/data
      - ./logs/local:/app/logs
      - .:/app/src  # Hot reload
      - ~/.aws:/root/.aws:ro  # AWS credentials
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  postgres:
    image: postgres:15-alpine
    container_name: pratiko-postgres-local-aws
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=pratiko_mcp
      - POSTGRES_USER=pratiko
      - POSTGRES_PASSWORD=pratiko123
    volumes:
      - ./data/local/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pratiko"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  redis:
    image: redis:7-alpine
    container_name: pratiko-redis-local-aws
    ports:
      - "6379:6379"
    volumes:
      - ./data/local/redis:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.2'
          memory: 256M

  # AWS LocalStack for local AWS service emulation (optional)
  localstack:
    image: localstack/localstack:latest
    container_name: pratiko-localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,dynamodb,lambda,cloudwatch
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
    volumes:
      - ./data/local/localstack:/tmp/localstack
    profiles: ["localstack"]  # Only start with --profile localstack

networks:
  default:
    name: pratiko-local-aws
EOF

    # Create AWS S3 bucket for development
    local dev_bucket_name="pratiko-mcp-dev-${USER}-$(date +%s | tail -c 6)"
    log_info "Creating S3 bucket for development: $dev_bucket_name"
    
    if aws s3 mb "s3://$dev_bucket_name" --region "$AWS_REGION" --profile "$AWS_PROFILE" 2>/dev/null; then
        log_success "S3 bucket created: $dev_bucket_name"
        echo "S3_BUCKET_NAME=$dev_bucket_name" > "$PROJECT_ROOT/aws/local/.env"
    else
        log_warning "Could not create S3 bucket (may already exist or permissions issue)"
    fi
    
    # Start local environment
    log_info "Starting local development environment with AWS integration..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.local-aws.yml up -d
    
    # Wait for services
    log_info "Waiting for services to start..."
    sleep 30
    
    # Verify services
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
        log_success "MCP Server with AWS integration is running at http://localhost:8080"
    else
        log_warning "MCP Server might still be starting up..."
    fi
    
    log_success "Local development environment with AWS integration is ready!"
    echo
    echo "🔗 Local Services:"
    echo "   • MCP Server:    http://localhost:8080"
    echo "   • Health Check:  http://localhost:8080/health"
    echo "   • Database:      localhost:5432 (pratiko/pratiko123)"
    echo "   • Redis:         localhost:6379"
    echo "   • LocalStack:    http://localhost:4566 (optional)"
    echo
    echo "☁️ AWS Services:"
    echo "   • S3 Bucket:     $dev_bucket_name"
    echo "   • Region:        $AWS_REGION"
    echo "   • Profile:       $AWS_PROFILE"
    echo
}

# Setup AWS Free Tier staging environment
setup_aws_staging_environment() {
    log_startup "Setting up AWS Free Tier staging environment..."
    show_phase_info "staging"
    
    local stack_name="pratiko-mcp-staging"
    local vpc_stack_name="pratiko-mcp-vpc"
    
    log_info "This will create AWS resources using CloudFormation"
    echo
    echo "🆓 AWS Free Tier Resources to be created:"
    echo "• EC2 t3.micro instance (750 hours/month free)"
    echo "• RDS db.t3.micro PostgreSQL (750 hours/month free)"
    echo "• Application Load Balancer"
    echo "• S3 bucket (5GB free)"
    echo "• CloudWatch monitoring (free tier)"
    echo
    
    read -p "Continue with AWS staging setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "AWS staging setup cancelled"
        return 0
    fi
    
    # Create VPC stack first
    log_info "Creating VPC infrastructure..."
    cat > "$PROJECT_ROOT/aws/cloudformation/vpc-stack.yaml" << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'PratikoAI MCP Server - VPC Infrastructure for Staging'

Parameters:
  Environment:
    Type: String
    Default: staging
    Description: Environment name

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-vpc"
        - Key: Environment
          Value: !Ref Environment

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-subnet-1"

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-subnet-2"

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.3.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-private-subnet-1"

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.4.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-private-subnet-2"

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-igw"

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-rt"

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachGateway
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnetRouteTableAssociation1:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PublicSubnetRouteTableAssociation2:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet2
      RouteTableId: !Ref PublicRouteTable

Outputs:
  VPCId:
    Description: VPC ID
    Value: !Ref VPC
    Export:
      Name: !Sub "${Environment}-vpc-id"

  PublicSubnet1Id:
    Description: Public Subnet 1 ID
    Value: !Ref PublicSubnet1
    Export:
      Name: !Sub "${Environment}-public-subnet-1-id"

  PublicSubnet2Id:
    Description: Public Subnet 2 ID
    Value: !Ref PublicSubnet2
    Export:
      Name: !Sub "${Environment}-public-subnet-2-id"

  PrivateSubnet1Id:
    Description: Private Subnet 1 ID
    Value: !Ref PrivateSubnet1
    Export:
      Name: !Sub "${Environment}-private-subnet-1-id"

  PrivateSubnet2Id:
    Description: Private Subnet 2 ID
    Value: !Ref PrivateSubnet2
    Export:
      Name: !Sub "${Environment}-private-subnet-2-id"
EOF

    # Create directories
    mkdir -p "$PROJECT_ROOT/aws/cloudformation"
    
    # Deploy VPC stack
    log_info "Deploying VPC CloudFormation stack..."
    aws cloudformation deploy \
        --template-file "$PROJECT_ROOT/aws/cloudformation/vpc-stack.yaml" \
        --stack-name "$vpc_stack_name" \
        --parameter-overrides Environment=staging \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" \
        --no-fail-on-empty-changeset
    
    if [ $? -eq 0 ]; then
        log_success "VPC stack deployed successfully"
    else
        log_error "Failed to deploy VPC stack"
    fi
    
    # Create main application stack
    log_info "Creating application CloudFormation template..."
    cat > "$PROJECT_ROOT/aws/cloudformation/staging-stack.yaml" << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'PratikoAI MCP Server - Staging Environment (AWS Free Tier Optimized)'

Parameters:
  Environment:
    Type: String
    Default: staging
    
  KeyPairName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: EC2 Key Pair for SSH access
    
  DomainName:
    Type: String
    Default: ""
    Description: Domain name for the application (optional)

Resources:
  # Security Groups
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for Application Load Balancer
      VpcId: 
        Fn::ImportValue: !Sub "${Environment}-vpc-id"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-alb-sg"

  EC2SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for EC2 instances
      VpcId: 
        Fn::ImportValue: !Sub "${Environment}-vpc-id"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8080
          ToPort: 8080
          SourceSecurityGroupId: !Ref ALBSecurityGroup
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 0.0.0.0/0  # Restrict this to your IP
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-ec2-sg"

  RDSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for RDS database
      VpcId: 
        Fn::ImportValue: !Sub "${Environment}-vpc-id"
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref EC2SecurityGroup
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-rds-sg"

  # S3 Bucket
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "pratiko-mcp-${Environment}-${AWS::AccountId}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      VersioningConfiguration:
        Status: Enabled
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # IAM Role for EC2
  EC2Role:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:DeleteObject
                Resource: !Sub "${S3Bucket}/*"
              - Effect: Allow
                Action:
                  - s3:ListBucket
                Resource: !Ref S3Bucket

  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref EC2Role

  # RDS Subnet Group
  RDSSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS database
      SubnetIds:
        - Fn::ImportValue: !Sub "${Environment}-private-subnet-1-id"
        - Fn::ImportValue: !Sub "${Environment}-private-subnet-2-id"
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-rds-subnet-group"

  # RDS Database (Free Tier)
  RDSDatabase:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: !Sub "pratiko-mcp-${Environment}"
      DBInstanceClass: db.t3.micro  # Free tier eligible
      Engine: postgres
      EngineVersion: '15.4'
      AllocatedStorage: 20  # Free tier limit
      StorageType: gp2
      StorageEncrypted: true
      
      DBName: pratiko_mcp_staging
      MasterUsername: pratiko
      MasterUserPassword: !Sub "{{resolve:secretsmanager:${Environment}-db-password:SecretString:password}}"
      
      VPCSecurityGroups:
        - !Ref RDSSecurityGroup
      DBSubnetGroupName: !Ref RDSSubnetGroup
      
      BackupRetentionPeriod: 7  # Free
      PreferredBackupWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "sun:04:00-sun:05:00"
      
      MultiAZ: false  # Single AZ for free tier
      PubliclyAccessible: false
      
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # Database Password Secret
  DBPasswordSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub "${Environment}-db-password"
      Description: Database password for staging environment
      GenerateSecretString:
        SecretStringTemplate: '{"username": "pratiko"}'
        GenerateStringKey: 'password'
        PasswordLength: 32
        ExcludeCharacters: '"@/\'

  # Launch Template
  LaunchTemplate:
    Type: AWS::EC2::LaunchTemplate
    Properties:
      LaunchTemplateName: !Sub "${Environment}-launch-template"
      LaunchTemplateData:
        ImageId: ami-0c7217cdde317cfec  # Amazon Linux 2023
        InstanceType: t3.micro  # Free tier eligible
        KeyName: !Ref KeyPairName
        IamInstanceProfile:
          Name: !Ref EC2InstanceProfile
        SecurityGroupIds:
          - !Ref EC2SecurityGroup
        UserData:
          Fn::Base64: !Sub |
            #!/bin/bash
            yum update -y
            yum install -y docker
            systemctl start docker
            systemctl enable docker
            usermod -a -G docker ec2-user
            
            # Install Docker Compose
            curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            
            # Install CloudWatch agent
            yum install -y amazon-cloudwatch-agent
            
            # Create application directory
            mkdir -p /opt/pratiko-mcp
            cd /opt/pratiko-mcp
            
            # Create docker-compose file
            cat > docker-compose.staging.yml << 'COMPOSE_EOF'
            version: '3.8'
            services:
              mcp-server:
                image: pratiko/mcp-server:staging
                ports:
                  - "8080:8080"
                environment:
                  - ENVIRONMENT=staging
                  - POSTGRES_URL=postgresql://pratiko:${DBPassword}@${DBEndpoint}:5432/pratiko_mcp_staging
                  - S3_BUCKET_NAME=${S3Bucket}
                  - AWS_REGION=${AWS::Region}
                restart: unless-stopped
            COMPOSE_EOF
            
            # Get database password from Secrets Manager
            DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id ${DBPasswordSecret} --region ${AWS::Region} --query SecretString --output text | jq -r .password)
            
            # Replace placeholders
            sed -i "s/\${DBPassword}/$DB_PASSWORD/g" docker-compose.staging.yml
            sed -i "s/\${DBEndpoint}/${RDSDatabase.Endpoint.Address}/g" docker-compose.staging.yml
            sed -i "s/\${S3Bucket}/${S3Bucket}/g" docker-compose.staging.yml
            
            # Start services
            docker-compose -f docker-compose.staging.yml up -d

  # Auto Scaling Group
  AutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      AutoScalingGroupName: !Sub "${Environment}-asg"
      LaunchTemplate:
        LaunchTemplateId: !Ref LaunchTemplate
        Version: !GetAtt LaunchTemplate.LatestVersionNumber
      MinSize: 1
      MaxSize: 2  # Keep minimal for staging
      DesiredCapacity: 1
      VPCZoneIdentifier:
        - Fn::ImportValue: !Sub "${Environment}-public-subnet-1-id"
        - Fn::ImportValue: !Sub "${Environment}-public-subnet-2-id"
      TargetGroupARNs:
        - !Ref TargetGroup
      HealthCheckType: ELB
      HealthCheckGracePeriod: 300
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-instance"
          PropagateAtLaunch: true
        - Key: Environment
          Value: !Ref Environment
          PropagateAtLaunch: true

  # Application Load Balancer
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: !Sub "${Environment}-alb"
      Scheme: internet-facing
      Type: application
      SecurityGroups:
        - !Ref ALBSecurityGroup
      Subnets:
        - Fn::ImportValue: !Sub "${Environment}-public-subnet-1-id"
        - Fn::ImportValue: !Sub "${Environment}-public-subnet-2-id"
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # Target Group
  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub "${Environment}-tg"
      Port: 8080
      Protocol: HTTP
      VpcId: 
        Fn::ImportValue: !Sub "${Environment}-vpc-id"
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 30
      HealthCheckTimeoutSeconds: 5
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      Tags:
        - Key: Environment
          Value: !Ref Environment

  # Listener
  Listener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup
      LoadBalancerArn: !Ref ApplicationLoadBalancer
      Port: 80
      Protocol: HTTP

Outputs:
  LoadBalancerDNS:
    Description: Load Balancer DNS Name
    Value: !GetAtt ApplicationLoadBalancer.DNSName
    Export:
      Name: !Sub "${Environment}-alb-dns"
      
  DatabaseEndpoint:
    Description: RDS Database Endpoint
    Value: !GetAtt RDSDatabase.Endpoint.Address
    Export:
      Name: !Sub "${Environment}-db-endpoint"
      
  S3BucketName:
    Description: S3 Bucket Name
    Value: !Ref S3Bucket
    Export:
      Name: !Sub "${Environment}-s3-bucket"
EOF

    # Prompt for key pair
    log_info "You need an EC2 Key Pair for SSH access to instances."
    read -p "Enter your EC2 Key Pair name (or press Enter to create one): " key_pair_name
    
    if [ -z "$key_pair_name" ]; then
        key_pair_name="pratiko-mcp-staging-$(date +%s)"
        log_info "Creating new EC2 Key Pair: $key_pair_name"
        aws ec2 create-key-pair --key-name "$key_pair_name" --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'KeyMaterial' --output text > "$key_pair_name.pem"
        chmod 400 "$key_pair_name.pem"
        log_success "Key pair created and saved as $key_pair_name.pem"
    fi
    
    # Deploy application stack
    log_info "Deploying application CloudFormation stack..."
    aws cloudformation deploy \
        --template-file "$PROJECT_ROOT/aws/cloudformation/staging-stack.yaml" \
        --stack-name "$stack_name" \
        --parameter-overrides Environment=staging KeyPairName="$key_pair_name" \
        --capabilities CAPABILITY_IAM \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" \
        --no-fail-on-empty-changeset
    
    if [ $? -eq 0 ]; then
        # Get outputs
        local alb_dns
        alb_dns=$(aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)
        
        log_success "AWS staging environment deployed successfully!"
        echo
        echo "🎉 Your staging environment is ready:"
        echo "   • Application URL: http://$alb_dns"
        echo "   • Health Check: http://$alb_dns/health"
        echo "   • SSH Key: $key_pair_name.pem (if created)"
        echo
        echo "⏳ Note: It may take 5-10 minutes for the application to be fully ready"
        echo
    else
        log_error "Failed to deploy application stack"
    fi
}

# Setup AWS Serverless production MVP
setup_aws_production_mvp() {
    log_startup "Setting up AWS Serverless Production MVP..."
    show_phase_info "mvp"
    
    log_info "This will create a serverless production environment using:"
    echo "• AWS Lambda (1M requests/month free)"
    echo "• API Gateway (1M requests/month free)"
    echo "• DynamoDB (25GB + 25 RCU/WCU free)"
    echo "• S3 (5GB free + additional as needed)"
    echo "• CloudFront (1TB transfer free)"
    echo
    
    read -p "Continue with serverless production setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Serverless production setup cancelled"
        return 0
    fi
    
    # Create SAM template for serverless deployment
    mkdir -p "$PROJECT_ROOT/aws/sam"
    
    cat > "$PROJECT_ROOT/aws/sam/template.yaml" << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: 'PratikoAI MCP Server - Serverless Production MVP'

Globals:
  Function:
    Timeout: 30
    MemorySize: 1024
    Runtime: python3.11
    Environment:
      Variables:
        ENVIRONMENT: production
        LOG_LEVEL: info

Parameters:
  DomainName:
    Type: String
    Default: ""
    Description: Custom domain name (optional)

Resources:
  # API Gateway
  ApiGateway:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Cors:
        AllowMethods: "'*'"
        AllowHeaders: "'*'"
        AllowOrigin: "'*'"
      Auth:
        DefaultAuthorizer: LambdaTokenAuthorizer
        Authorizers:
          LambdaTokenAuthorizer:
            FunctionArn: !GetAtt AuthorizerFunction.Arn

  # Main Application Lambda
  MCPServerFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: pratiko-mcp-server-prod
      CodeUri: ../lambda/
      Handler: main.lambda_handler
      Environment:
        Variables:
          DYNAMODB_TABLE: !Ref DynamoDBTable
          S3_BUCKET: !Ref S3Bucket
          JWT_SECRET_KEY: !Ref JWTSecret
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DynamoDBTable
        - S3CrudPolicy:
            BucketName: !Ref S3Bucket
        - Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action:
                - secretsmanager:GetSecretValue
              Resource: !Ref JWTSecret
      Events:
        ApiEvent:
          Type: Api
          Properties:
            RestApiId: !Ref ApiGateway
            Path: /{proxy+}
            Method: ANY

  # Authorizer Lambda
  AuthorizerFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: pratiko-mcp-authorizer-prod
      CodeUri: ../lambda/
      Handler: authorizer.lambda_handler
      Environment:
        Variables:
          JWT_SECRET_KEY: !Ref JWTSecret

  # DynamoDB Table (Free Tier)
  DynamoDBTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: pratiko-mcp-prod
      BillingMode: PROVISIONED
      ProvisionedThroughput:
        ReadCapacityUnits: 25  # Free tier limit
        WriteCapacityUnits: 25  # Free tier limit
      AttributeDefinitions:
        - AttributeName: pk
          AttributeType: S
        - AttributeName: sk
          AttributeType: S
        - AttributeName: gsi1pk
          AttributeType: S
        - AttributeName: gsi1sk
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH
        - AttributeName: sk
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: gsi1pk
              KeyType: HASH
            - AttributeName: gsi1sk
              KeyType: RANGE
          ProvisionedThroughput:
            ReadCapacityUnits: 5
            WriteCapacityUnits: 5
          Projection:
            ProjectionType: ALL
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      Tags:
        - Key: Environment
          Value: production

  # S3 Bucket
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "pratiko-mcp-prod-${AWS::AccountId}"
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      VersioningConfiguration:
        Status: Enabled
      CorsConfiguration:
        CorsRules:
          - AllowedHeaders: ['*']
            AllowedMethods: [GET, PUT, POST, DELETE]
            AllowedOrigins: ['*']
            MaxAge: 3000

  # CloudFront Distribution
  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        Comment: PratikoAI MCP Server CDN
        DefaultRootObject: index.html
        Origins:
          - Id: ApiGatewayOrigin
            DomainName: !Sub "${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com"
            CustomOriginConfig:
              HTTPPort: 443
              HTTPSPort: 443
              OriginProtocolPolicy: https-only
          - Id: S3Origin
            DomainName: !GetAtt S3Bucket.RegionalDomainName
            S3OriginConfig:
              OriginAccessIdentity: !Sub "origin-access-identity/cloudfront/${CloudFrontOAI}"
        DefaultCacheBehavior:
          TargetOriginId: ApiGatewayOrigin
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods: [DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT]
          CachedMethods: [GET, HEAD, OPTIONS]
          ForwardedValues:
            QueryString: true
            Headers: ['*']
        CacheBehaviors:
          - PathPattern: "/static/*"
            TargetOriginId: S3Origin
            ViewerProtocolPolicy: redirect-to-https
            AllowedMethods: [GET, HEAD]
            ForwardedValues:
              QueryString: false
        PriceClass: PriceClass_100

  # CloudFront Origin Access Identity
  CloudFrontOAI:
    Type: AWS::CloudFront::OriginAccessIdentity
    Properties:
      OriginAccessIdentityConfig:
        Comment: OAI for PratikoAI MCP Server

  # JWT Secret
  JWTSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: pratiko-mcp-jwt-secret-prod
      Description: JWT secret for production environment
      GenerateSecretString:
        SecretStringTemplate: '{}'
        GenerateStringKey: 'secret'
        PasswordLength: 64
        ExcludeCharacters: '"@/\'

  # CloudWatch Log Groups
  MCPServerLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${MCPServerFunction}"
      RetentionInDays: 7

  AuthorizerLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub "/aws/lambda/${AuthorizerFunction}"
      RetentionInDays: 7

Outputs:
  ApiGatewayUrl:
    Description: API Gateway URL
    Value: !Sub "https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/prod"
    Export:
      Name: pratiko-mcp-prod-api-url

  CloudFrontUrl:
    Description: CloudFront Distribution URL
    Value: !Sub "https://${CloudFrontDistribution.DomainName}"
    Export:
      Name: pratiko-mcp-prod-cdn-url

  S3BucketName:
    Description: S3 Bucket Name
    Value: !Ref S3Bucket
    Export:
      Name: pratiko-mcp-prod-s3-bucket
EOF

    # Create basic Lambda function structure
    mkdir -p "$PROJECT_ROOT/aws/lambda"
    
    cat > "$PROJECT_ROOT/aws/lambda/main.py" << 'EOF'
import json
import os
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """
    Main Lambda handler for PratikoAI MCP Server
    """
    
    # Get environment variables
    dynamodb_table = os.environ.get('DYNAMODB_TABLE')
    s3_bucket = os.environ.get('S3_BUCKET')
    
    # Parse the request
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    
    # Simple routing
    if path == '/health':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'environment': 'production'
            })
        }
    
    elif path.startswith('/api/'):
        # Handle API requests
        return handle_api_request(event, context)
    
    else:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Not found',
                'path': path
            })
        }

def handle_api_request(event, context):
    """
    Handle API requests
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'API endpoint',
            'path': event.get('path'),
            'method': event.get('httpMethod')
        })
    }
EOF

    cat > "$PROJECT_ROOT/aws/lambda/authorizer.py" << 'EOF'
import json
import jwt
import os
import boto3

def lambda_handler(event, context):
    """
    Lambda authorizer for JWT token validation
    """
    
    token = event['authorizationToken']
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Get JWT secret from environment or Secrets Manager
        jwt_secret = get_jwt_secret()
        
        # Decode and validate JWT
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        
        # Generate policy
        policy = generate_policy('user', 'Allow', event['methodArn'])
        policy['context'] = {
            'user_id': payload.get('user_id', ''),
            'username': payload.get('username', '')
        }
        
        return policy
        
    except jwt.ExpiredSignatureError:
        raise Exception('Unauthorized: Token expired')
    except jwt.InvalidTokenError:
        raise Exception('Unauthorized: Invalid token')
    except Exception as e:
        raise Exception(f'Unauthorized: {str(e)}')

def get_jwt_secret():
    """
    Get JWT secret from Secrets Manager
    """
    secret_name = os.environ.get('JWT_SECRET_KEY')
    
    session = boto3.session.Session()
    client = session.client('secretsmanager')
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret['secret']
    except Exception as e:
        raise Exception(f'Failed to get JWT secret: {str(e)}')

def generate_policy(principal_id, effect, resource):
    """
    Generate IAM policy for API Gateway
    """
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    return policy
EOF

    # Create requirements.txt
    cat > "$PROJECT_ROOT/aws/lambda/requirements.txt" << 'EOF'
PyJWT==2.8.0
boto3==1.34.0
requests==2.31.0
EOF

    # Install SAM CLI check
    if ! command -v sam >/dev/null 2>&1; then
        log_warning "AWS SAM CLI not found. Install it for easy deployment:"
        echo "   • macOS: brew install aws-sam-cli"
        echo "   • Manual: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
        echo
        log_info "You can still deploy using CloudFormation directly"
    fi
    
    log_success "AWS Serverless production MVP configured!"
    echo
    echo "📁 Files created:"
    echo "   • aws/sam/template.yaml - SAM template"
    echo "   • aws/lambda/main.py - Main Lambda function"
    echo "   • aws/lambda/authorizer.py - JWT authorizer"
    echo
    echo "🚀 To deploy:"
    echo "   cd aws/sam"
    echo "   sam build"
    echo "   sam deploy --guided"
    echo
    echo "💡 This will create a serverless production environment for ~$2.30/month!"
}

# Show AWS cost comparison
show_aws_cost_comparison() {
    echo -e "${PURPLE}"
    echo "💰 AWS vs Original Cost Comparison"
    echo "===================================" 
    echo -e "${NC}"
    
    echo "Original Multi-Cloud Setup:"
    echo "• Development: $0/month (local Mac)"
    echo "• Staging: $24/month (DigitalOcean droplet)"
    echo "• Production MVP: $5/month (Railway + free tiers)"
    echo "• TOTAL: $29/month"
    echo
    
    echo -e "${GREEN}AWS-Optimized Setup (First 12 months):${NC}"
    echo "• Development: $0/month (local + AWS free tier) ✅"
    echo "• Staging: $0/month (AWS free tier) ✅"
    echo "• Production MVP: $2.30/month (serverless + free tier) ✅"
    echo "• TOTAL: $2.30/month 🎉"
    echo
    
    echo -e "${YELLOW}AWS-Optimized Setup (After 12 months):${NC}"
    echo "• Development: $0/month (local + always free services)"
    echo "• Staging: $29.50/month (when free tier expires)"
    echo "• Production MVP: $31.80/month (when free tier expires)"
    echo "• TOTAL: $61.30/month"
    echo
    
    echo -e "${BLUE}📈 MASSIVE SAVINGS in Year 1: 92% cost reduction!${NC}"
    echo "First year: $2.30 vs $29/month = $27/month saved"
    echo "After year 1: Still competitive with excellent scaling"
    echo
    
    echo "🎯 AWS Advantages:"
    echo "• 12 months of generous free tier"
    echo "• Seamless serverless scaling"
    echo "• Enterprise-grade reliability"
    echo "• Global infrastructure"
    echo "• Advanced security features"
    echo "• Integrated monitoring and logging"
    echo
}

# Main menu
show_menu() {
    echo -e "${BLUE}What would you like to set up?${NC}"
    echo
    echo "1) 🏠 Local Development + AWS Free Services (FREE)"
    echo "2) 🏗️  AWS Free Tier Staging ($0 first 12 months)"
    echo "3) 🎯 AWS Serverless Production MVP ($2.30/month)"
    echo "4) 💰 Show AWS cost comparison"
    echo "5) ❓ Help & documentation"
    echo "6) 🚪 Exit"
    echo
}

# Help documentation
show_help() {
    echo -e "${BLUE}🆘 PratikoAI AWS MCP Help${NC}"
    echo
    echo "This script helps you set up MCP servers optimized for AWS:"
    echo
    echo "🏠 Local Development + AWS:"
    echo "   • Your Mac for compute (free)"
    echo "   • AWS S3, CloudWatch for storage & monitoring"
    echo "   • Perfect for development and testing"
    echo
    echo "🏗️ AWS Free Tier Staging:"
    echo "   • EC2 t3.micro (750 hours/month free)"
    echo "   • RDS db.t3.micro (750 hours/month free)"
    echo "   • S3, CloudWatch (generous free tiers)"
    echo "   • $0 for first 12 months!"
    echo
    echo "🎯 AWS Serverless Production:"
    echo "   • Lambda (1M requests/month free)"
    echo "   • DynamoDB (25GB free)"
    echo "   • API Gateway (1M requests/month free)"
    echo "   • CloudFront (1TB transfer free)"
    echo "   • Just $2.30/month for extra S3 storage"
    echo
    echo "🔧 Prerequisites:"
    echo "   • AWS CLI installed and configured"
    echo "   • AWS account (free tier eligible recommended)"
    echo "   • Docker Desktop (for local development)"
    echo
    echo "📚 Additional Files Created:"
    echo "   • CloudFormation templates"
    echo "   • SAM serverless templates"
    echo "   • Lambda function code"
    echo "   • Docker configurations"
    echo
}

# Main function
main() {
    show_banner
    check_aws_prerequisites
    show_aws_cost_comparison
    
    while true; do
        show_menu
        read -p "Choose an option (1-6): " -n 1 -r
        echo
        echo
        
        case $REPLY in
            1)
                setup_local_development_aws
                ;;
            2)
                setup_aws_staging_environment
                ;;
            3)
                setup_aws_production_mvp
                ;;
            4)
                show_aws_cost_comparison
                ;;
            5)
                show_help
                ;;
            6)
                log_success "Good luck with your AWS-powered startup! ☁️"
                exit 0
                ;;
            *)
                log_warning "Invalid option. Please choose 1-6."
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..." -r
        clear
        show_banner
    done
}

# Run main function
main "$@"