# Renewable Energy Data Pipeline

A complete data engineering solution for processing renewable energy generation and consumption data using AWS services with automated alerting, CI/CD deployment, and comprehensive error handling.

## Objective

Design and implement a scalable data pipeline using AWS to simulate a real-world data engineering problem. The pipeline ingests, processes, and stores energy data in real-time while providing APIs, visualizations, and automated monitoring capabilities.

## Architecture

```
Data Flow: S3 → Lambda → DynamoDB → APIs/Visualizations
Monitoring: CloudWatch → SNS Alerts → Email/SMS
Deployment: GitHub → Actions → AWS (Automated CI/CD)
```

### Components:
- **S3 Bucket**: Data ingestion and storage with event triggers
- **Lambda Function**: Real-time data processing with error handling
- **DynamoDB**: Processed data storage with optimized queries
- **FastAPI**: Comprehensive REST API endpoints
- **SNS**: Real-time anomaly alerts and notifications
- **CloudWatch**: Logging, monitoring, and dashboards
- **Terraform**: Infrastructure as Code for reproducible deployments
- **GitHub Actions**: Automated CI/CD pipeline

## 📋 Requirements Completed

### 1. Simulated Data Feed
- **Files**: `data_generator.py`, `continuous_uploader.py`
- **Features**:
  - Random energy data generation for 5 sites
  - Realistic time-based patterns (solar generation cycles)
  - Continuous uploads every 5 minutes with safety limits
  - Automatic anomaly injection (2% rate)
  - Graceful shutdown and error recovery

### 2. Data Processing
- **File**: `lambda_function.py` (deployed as AWS Lambda)
- **Features**:
  - Automatic processing on S3 file uploads via event triggers
  - Net energy calculation: `net_energy = generated - consumed`
  - Real-time anomaly detection for negative values
  - Comprehensive error handling and retry logic
  - CloudWatch logging integration

### 3. Data Storage
- **Service**: AWS DynamoDB
- **Schema**:
  - Partition Key: `site_id` (String)
  - Sort Key: `timestamp` (String)
  - Attributes: `energy_generated_kwh`, `energy_consumed_kwh`, `net_energy_kwh`, `anomaly`, `anomaly_reasons`
  - Global Secondary Index on `timestamp` for time-based queries
  - On-demand billing for cost optimization

### 4. Data Visualization
- **File**: `business_visualizer.py`
- **Charts**:
  - Site performance comparison with efficiency metrics
  - Energy efficiency analysis with color-coded zones
  - Anomaly distribution across sites
  - Executive dashboard with key performance indicators
  - Interactive Plotly charts with export capabilities

### 5. APIs for Querying Data
- **File**: `energy_api.py`
- **Comprehensive Endpoints**:
  - `GET /sites/{site_id}` - Site data with optional time filtering
  - `GET /sites/{site_id}/anomalies` - Site-specific anomalies with analysis
  - `GET /sites/{site_id}/range` - Data for specific time range
  - `GET /anomalies` - All anomalies across sites with distribution
  - `GET /summary` - Performance summary with business metrics
  - `GET /health` - System health check with service status
- **Features**: Parameter validation, error handling, comprehensive documentation

## Extra Credit Features

### 1. Automated Alerting for Anomalies
- **File**: `anomaly_alerting.py`
- **Features**:
  - Real-time SNS alerts for energy anomalies
  - Email and SMS notification support
  - Severity-based alerting (LOW, MEDIUM, HIGH, CRITICAL)
  - Daily summary reports with system health
  - Integration with Lambda for automatic anomaly detection
  - Customizable alert thresholds and recipients

### 2. GitHub CI/CD Pipeline
- **File**: `.github/workflows/deploy.yml`
- **Features**:
  - Automated testing on code push/pull requests
  - Security scanning for vulnerabilities and credentials
  - Automated Lambda function deployment
  - Multi-environment support (staging/production)
  - Build artifact management
  - Deployment notifications and rollback capabilities
  - Infrastructure validation

### 3. Comprehensive Error Handling
- **File**: `error_handling.py`
- **Features**:
  - CloudWatch logging integration with structured logs
  - Automatic retry mechanisms with exponential backoff
  - Error categorization and severity classification
  - Real-time error alerts via SNS
  - Graceful degradation for service failures
  - Error statistics and reporting
  - Circuit breaker patterns for external services

## Infrastructure as Code

### Terraform Configuration
- **File**: `terraform/main.tf`
- **Resources Managed**:
  - S3 bucket with versioning, encryption, and public access blocking
  - DynamoDB table with GSI and on-demand billing
  - Lambda function with proper IAM roles and policies
  - SNS topics and subscriptions for alerting
  - CloudWatch log groups and dashboards
  - S3 event notifications and Lambda permissions
  - IAM roles with least-privilege access

### Deployment Strategy
**Initial Setup**: Resources created manually via AWS Console for rapid prototyping
**Production Management**: Terraform state imported from existing resources for ongoing management
**Hybrid Approach**: Combines manual setup speed with Infrastructure as Code benefits

## Setup Instructions

### Prerequisites
- AWS Account with configured credentials
- Python 3.9+
- Terraform >= 1.0 (optional for infrastructure management)
- Git and GitHub account
- Required packages: `boto3`, `fastapi`, `uvicorn`, `plotly`, `matplotlib`, `pandas`, `requests`

### 1. AWS Setup
```bash
# Configure AWS credentials
aws configure

# Set region to us-east-1
# Use your access keys from IAM user with required permissions
```

### 2. Quick Start (Manual Setup)
```bash
# Clone repository
git clone https://github.com/zeeldesai-dev/renewable-energy-data-pipeline.git
cd renewable-energy-data-pipeline

# Install dependencies
pip install boto3 pandas matplotlib plotly fastapi uvicorn requests

# Create AWS resources via Console:
# - S3 Bucket: zeel-energy-data-2025
# - DynamoDB Table: energy-data (site_id, timestamp)
# - Lambda Function: energy-data-processor
# - SNS Topic: energy-anomaly-alerts
```

### 3. Infrastructure as Code 
```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure (creates all AWS resources)
terraform apply

# To import existing resources (if created manually first):
terraform import aws_s3_bucket.energy_data zeel-energy-data-2025
terraform import aws_dynamodb_table.energy_data energy-data
terraform import aws_lambda_function.energy_processor energy-data-processor
```

### 4. Project Setup
```bash
# Project structure automatically created:
renewable-energy-pipeline/
├── .github/workflows/          # CI/CD pipeline
├── src/                       # Python source code
├── terraform/                 # Infrastructure as code
└── README.md                  # Documentation
```

## Usage

### Data Generation
```bash
# Navigate to source directory
cd src

# Single batch upload (testing)
python data_generator.py

# Continuous uploads (production simulation)
python continuous_uploader.py

# Anomaly alerting setup
python anomaly_alerting.py
```

### API Server
```bash
# Start API server
python energy_api.py

# Access endpoints:
# - API: http://localhost:8000
# - Interactive docs: http://localhost:8000/docs
# - Health check: http://localhost:8000/health
```

### Visualizations
```bash
# Important: Make sure the API server is running before executing this script
# (The business_visualizer.py script fetches data from FastAPI endpoints)
# Generate business dashboards (requires API running)
python business_visualizer.py

# Output files:
# - site_performance_comparison.html
# - energy_efficiency_analysis.html
# - anomaly_distribution.html
# - energy_dashboard.html
```

### Error Handling & Monitoring
```bash
# Test error handling system
python error_handling.py

# View logs in AWS CloudWatch:
# - Log group: energy-pipeline-errors
# - Lambda logs: /aws/lambda/energy-data-processor
```

## API Examples

### Get Site Performance Data
```bash
curl "http://localhost:8000/sites/SITE_001"
curl "http://localhost:8000/sites/SITE_001?start_date=2025-06-11&end_date=2025-06-12"
```

### Get Anomaly Information
```bash
curl "http://localhost:8000/sites/SITE_001/anomalies"
curl "http://localhost:8000/anomalies"
```

### Get Time Range Data
```bash
curl "http://localhost:8000/sites/SITE_001/range?start_date=2025-06-11&end_date=2025-06-12"
```

### Get System Summary
```bash
curl "http://localhost:8000/summary"
curl "http://localhost:8000/health"
```

## 📁 Project Structure

```
renewable-energy-pipeline/
├── .github/
│   └── workflows/
│       └── deploy.yml                   # CI/CD pipeline
├── src/
│   ├── data_generator.py                # Single-batch testing
│   ├── continuous_uploader.py           # Automated 5-min uploads
│   ├── lambda_processor.py              # Lambda processor
│   ├── energy_api.py                    # FastAPI endpoints
│   ├── energy_visualizer.py             # Time-series charts
│   ├── business_visualizer.py           # Business dashboards 
│   ├── anomaly_alerting.py              # Real-time alerts
│   ├── error_handling.py                # Error management
│   ├── test_error_handling.py           # Error tests
│   ├── test_github_check.py             # GitHub validation
│   ├── site_performance_comparison.html # Dashboard output
│   ├── energy_efficiency_analysis.html  # Charts output
│   ├── anomaly_distribution.html        # Anomaly charts
│   ├── energy_dashboard.html            # Main dashboard
│   ├── energy_trends.html               # Trend analysis
│   ├── performance_heatmap.html         # Performance heatmap
│   ├── site_comparison.html             # Site comparisons
│   └── lambda_package/                  # Lambda deployment
│       ├── lambda_function.py           # Deployed function
│       └── lambda_function.zip          # Deployment package
├── terraform/
│   ├── main.tf                          # Infrastructure code
│   └── validate_terraform.py            # Validation script
├── Screenshots.pdf                      # UI & output screenshots 
├── DESIGN_DECISIONS.md                  # Solution write-up
└── README.md                            # Setup instructions and usage documentation

```


## Scalability & Future Enhancements

### Current System Limits
- 5 energy sites with configurable expansion
- 15-25 records per 5-minute interval (7,200+ records/day)
- Single AWS region deployment (us-east-1)
- Real-time processing with sub-minute latency

### Scale-Up Roadmap
- **Horizontal Scaling**: Multi-region deployment for global coverage
- **Data Volume**: Increase to thousands of sites with stream processing
- **Real-time Analytics**: Add Kinesis for sub-second processing
- **Machine Learning**: Anomaly detection using AWS SageMaker
- **Dashboard Enhancement**: Real-time updates with WebSocket connections

### Monitoring & Observability
- CloudWatch dashboards for system health
- Custom metrics for business KPIs
- Distributed tracing for performance optimization
- Automated alerting for SLA violations
- Cost monitoring and optimization recommendations

## Development Approach

### Methodology
1. **Rapid Prototyping**: Manual AWS Console setup for quick iteration
2. **Infrastructure Evolution**: Terraform implementation for production management
3. **Test-Driven Development**: Comprehensive testing at each stage
4. **Monitoring-First**: Logging and alerting built from the beginning
5. **Documentation**: Comprehensive documentation for maintenance and scaling


## 👨‍💻 Author

**Zeel Desai**
- **Project**: Renewable Energy Data Pipeline
- **Technology Stack**: Python, AWS (S3, Lambda, DynamoDB, SNS, CloudWatch), FastAPI, Plotly, Terraform, GitHub Actions
- **Architecture**: Serverless, event-driven, microservices with Infrastructure as Code
- **Completion Date**: June 2025
- **Repository**: https://github.com/zeeldesai-dev/renewable-energy-data-pipeline

---



*This implementation showcases advanced data engineering skills including cloud architecture, DevOps practices, monitoring and observability, and business intelligence capabilities suitable for production environments.*