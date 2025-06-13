import boto3
import json
import traceback
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from functools import wraps

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ErrorType(Enum):
    """Types of errors in the pipeline"""
    DATA_VALIDATION = "DATA_VALIDATION"
    AWS_SERVICE = "AWS_SERVICE"
    NETWORK = "NETWORK"
    PROCESSING = "PROCESSING"
    AUTHENTICATION = "AUTHENTICATION"
    STORAGE = "STORAGE"
    API = "API"

class PipelineErrorHandler:
    """Comprehensive error handling for the energy data pipeline"""
    
    def __init__(self, log_group_name="energy-pipeline-errors"):
        """
        Initialize error handler
        
        Args:
            log_group_name: CloudWatch log group name
        """
        self.cloudwatch_logs = boto3.client('logs', region_name='us-east-1')
        self.sns_client = boto3.client('sns', region_name='us-east-1')
        self.log_group_name = log_group_name
        self.log_stream_name = f"error-stream-{datetime.utcnow().strftime('%Y-%m-%d-%H')}"
        
        # Setup logging
        self.setup_logging()
        
        # Error counters
        self.error_counts = {
            ErrorSeverity.LOW: 0,
            ErrorSeverity.MEDIUM: 0,
            ErrorSeverity.HIGH: 0,
            ErrorSeverity.CRITICAL: 0
        }
        
        # Retry configuration
        self.retry_config = {
            ErrorType.NETWORK: {"max_retries": 3, "backoff": 2},
            ErrorType.AWS_SERVICE: {"max_retries": 5, "backoff": 1.5},
            ErrorType.STORAGE: {"max_retries": 3, "backoff": 2},
            ErrorType.API: {"max_retries": 2, "backoff": 1}
        }
    
    def setup_logging(self):
        """Setup CloudWatch logging"""
        try:
            # Create log group if it doesn't exist
            try:
                self.cloudwatch_logs.create_log_group(logGroupName=self.log_group_name)
                print(f"Created CloudWatch log group: {self.log_group_name}")
            except self.cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                print(f"CloudWatch log group already exists: {self.log_group_name}")
            
            # Create log stream
            try:
                self.cloudwatch_logs.create_log_stream(
                    logGroupName=self.log_group_name,
                    logStreamName=self.log_stream_name
                )
                print(f"Created log stream: {self.log_stream_name}")
            except self.cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                print(f"Log stream already exists: {self.log_stream_name}")
                
        except Exception as e:
            print(f"Failed to setup CloudWatch logging: {e}")
    
    def log_error(self, 
                  error: Exception, 
                  severity: ErrorSeverity,
                  error_type: ErrorType,
                  context: Dict[str, Any],
                  component: str):
        """
        Log error with full context
        
        Args:
            error: The exception that occurred
            severity: Error severity level
            error_type: Type of error
            context: Additional context information
            component: Component where error occurred
        """
        
        error_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": severity.value,
            "error_type": error_type.value,
            "component": component,
            "error_message": str(error),
            "error_class": error.__class__.__name__,
            "traceback": traceback.format_exc(),
            "context": context
        }
        
        # Log to CloudWatch
        try:
            self.cloudwatch_logs.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=[
                    {
                        'timestamp': int(time.time() * 1000),
                        'message': json.dumps(error_data, indent=2)
                    }
                ]
            )
            print(f"Error logged to CloudWatch")
        except Exception as e:
            print(f"Failed to log to CloudWatch: {e}")
        
        # Update error counters
        self.error_counts[severity] += 1
        
        # Print to console
        print(f"{severity.value} ERROR in {component}: {str(error)}")
        
        # Send alert for high severity errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.send_error_alert(error_data)
        
        return error_data
    
    def send_error_alert(self, error_data: Dict[str, Any]):
        """Send alert for high severity errors"""
        try:
            severity = error_data['severity']
            component = error_data['component']
            error_message = error_data['error_message']
            timestamp = error_data['timestamp']
            
            subject = f" {severity} ERROR - Energy Pipeline"
            
            message = f"""
 HIGH SEVERITY ERROR DETECTED

Component: {component}
Severity: {severity}
Time: {timestamp}

Error: {error_message}

Context: {json.dumps(error_data['context'], indent=2)}

Action Required:
• Check component status immediately
• Review error logs in CloudWatch
• Verify AWS service health
• Contact on-call engineer if critical

Dashboard: http://localhost:8000/health
Logs: CloudWatch > {self.log_group_name}
            """
            
            # Try to send via SNS (if topic exists)
            try:
                topics = self.sns_client.list_topics()
                energy_topic = None
                
                for topic in topics['Topics']:
                    if 'energy' in topic['TopicArn'].lower():
                        energy_topic = topic['TopicArn']
                        break
                
                if energy_topic:
                    self.sns_client.publish(
                        TopicArn=energy_topic,
                        Subject=subject,
                        Message=message
                    )
                    print(f"Error alert sent via SNS")
                else:
                    print(f" No SNS topic found for alerts")
                
            except Exception as e:
                print(f" Failed to send SNS alert: {e}")
                
        except Exception as e:
            print(f" Failed to send error alert: {e}")
    
    def retry_operation(self, 
                       operation_func, 
                       error_type: ErrorType,
                       context: Dict[str, Any],
                       component: str):
        """
        Retry operation with exponential backoff
        
        Args:
            operation_func: Function to retry
            error_type: Type of operation for retry configuration
            context: Context information
            component: Component name
        """
        
        config = self.retry_config.get(error_type, {"max_retries": 1, "backoff": 1})
        max_retries = config["max_retries"]
        backoff_factor = config["backoff"]
        
        for attempt in range(max_retries + 1):
            try:
                result = operation_func()
                
                if attempt > 0:
                    print(f" Operation succeeded on attempt {attempt + 1}")
                    
                return result
                
            except Exception as e:
                if attempt == max_retries:
                    # Final attempt failed
                    self.log_error(
                        error=e,
                        severity=ErrorSeverity.HIGH,
                        error_type=error_type,
                        context={**context, "attempts": attempt + 1, "max_retries": max_retries},
                        component=component
                    )
                    raise
                else:
                    # Retry with backoff
                    wait_time = backoff_factor ** attempt
                    print(f" Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    
                    self.log_error(
                        error=e,
                        severity=ErrorSeverity.MEDIUM,
                        error_type=error_type,
                        context={**context, "attempt": attempt + 1},
                        component=component
                    )
                    
                    time.sleep(wait_time)

def error_handler_decorator(error_type: ErrorType, component: str):
    """Decorator for automatic error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = PipelineErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler.log_error(
                    error=e,
                    severity=ErrorSeverity.MEDIUM,
                    error_type=error_type,
                    context={"args": str(args), "kwargs": str(kwargs)},
                    component=component
                )
                raise
        return wrapper
    return decorator

# Example usage
@error_handler_decorator(ErrorType.DATA_VALIDATION, "data_processing")
def process_data(data):
    """Example function with error handling"""
    if not data:
        raise ValueError("No data provided")
    return {"processed": True, "count": len(data)}

# Enhanced Lambda function with comprehensive error handling
def enhanced_lambda_handler_with_error_handling(event, context):
    """
    Enhanced Lambda function with comprehensive error handling
    """
    handler = PipelineErrorHandler()
    
    try:
        # Initialize components
        s3_client = boto3.client('s3')
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('energy-data')
        
        # Extract S3 event information
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Download file with retry logic
        def download_file():
            response = s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read().decode('utf-8')
        
        file_content = handler.retry_operation(
            operation_func=download_file,
            error_type=ErrorType.AWS_SERVICE,
            context={"bucket": bucket, "key": key},
            component="s3_download"
        )
        
        # Parse JSON with error handling
        try:
            records = json.loads(file_content)
        except json.JSONDecodeError as e:
            handler.log_error(
                error=e,
                severity=ErrorSeverity.HIGH,
                error_type=ErrorType.DATA_VALIDATION,
                context={"bucket": bucket, "key": key, "file_size": len(file_content)},
                component="json_parsing"
            )
            raise
        
        # Process records
        processed_count = 0
        error_count = 0
        
        for i, record in enumerate(records):
            try:
                # Process individual record
                processed_record = process_energy_record_with_validation(record)
                
                if processed_record:
                    # Store in DynamoDB with retry
                    def store_record():
                        table.put_item(Item=processed_record)
                    
                    handler.retry_operation(
                        operation_func=store_record,
                        error_type=ErrorType.STORAGE,
                        context={"record_index": i, "site_id": record.get('site_id', 'unknown')},
                        component="dynamodb_storage"
                    )
                    
                    processed_count += 1
                
            except Exception as e:
                error_count += 1
                handler.log_error(
                    error=e,
                    severity=ErrorSeverity.MEDIUM,
                    error_type=ErrorType.PROCESSING,
                    context={"record_index": i, "record": record},
                    component="record_processing"
                )
                # Continue processing other records
                continue
        
        print(f" Processed {processed_count} records successfully")
        if error_count > 0:
            print(f" {error_count} records failed processing")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processing completed',
                'processed_count': processed_count,
                'error_count': error_count,
                'source_file': key
            })
        }
        
    except Exception as e:
        # Handle catastrophic errors
        handler.log_error(
            error=e,
            severity=ErrorSeverity.CRITICAL,
            error_type=ErrorType.PROCESSING,
            context={"event": event},
            component="lambda_handler"
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Critical processing failure',
                'message': str(e)
            })
        }

def process_energy_record_with_validation(record):
    """Process energy record with comprehensive validation"""
    try:
        # Validate required fields
        required_fields = ['site_id', 'timestamp', 'energy_generated_kwh', 'energy_consumed_kwh']
        for field in required_fields:
            if field not in record:
                raise ValueError(f"Missing required field: {field}")
        
        site_id = record['site_id']
        timestamp = record['timestamp']
        energy_generated = float(record['energy_generated_kwh'])
        energy_consumed = float(record['energy_consumed_kwh'])
        
        # Validate data ranges
        if energy_generated < -1000 or energy_generated > 10000:
            raise ValueError(f"Energy generated out of valid range: {energy_generated}")
        
        if energy_consumed < -1000 or energy_consumed > 10000:
            raise ValueError(f"Energy consumed out of valid range: {energy_consumed}")
        
        # Calculate net energy
        net_energy = energy_generated - energy_consumed
        
        # Detect anomalies
        anomaly = False
        anomaly_reasons = []
        
        if energy_generated < 0:
            anomaly = True
            anomaly_reasons.append("negative_generation")
            
        if energy_consumed < 0:
            anomaly = True
            anomaly_reasons.append("negative_consumption")
        
        # Create processed record
        from decimal import Decimal
        processed_record = {
            'site_id': site_id,
            'timestamp': timestamp,
            'energy_generated_kwh': Decimal(str(energy_generated)),
            'energy_consumed_kwh': Decimal(str(energy_consumed)),
            'net_energy_kwh': Decimal(str(net_energy)),
            'anomaly': anomaly,
            'anomaly_reasons': anomaly_reasons,
            'processed_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        return processed_record
        
    except Exception as e:
        raise ValueError(f"Record validation failed: {str(e)}")

def test_error_handling_system():
    """Test the error handling system"""
    print(" Testing Error Handling System...")
    
    handler = PipelineErrorHandler()
    
    # Test 1: Basic error logging
    try:
        raise ValueError("Test validation error")
    except Exception as e:
        handler.log_error(
            error=e,
            severity=ErrorSeverity.HIGH,
            error_type=ErrorType.DATA_VALIDATION,
            context={"test": "basic_error_logging"},
            component="test_module"
        )
    
    # Test 2: Retry mechanism
    attempt_counter = 0
    def failing_operation():
        nonlocal attempt_counter
        attempt_counter += 1
        if attempt_counter < 3:
            raise ConnectionError("Simulated network failure")
        return "Success after retries"
    
    try:
        result = handler.retry_operation(
            operation_func=failing_operation,
            error_type=ErrorType.NETWORK,
            context={"test": "retry_mechanism"},
            component="test_retry"
        )
        print(f" Retry test successful: {result}")
    except Exception as e:
        print(f" Retry test failed: {e}")
    
    # Test 3: Error statistics
    print(f" Error Statistics: {handler.error_counts}")
    
    return handler

if __name__ == "__main__":
    print(" Starting Error Handling System Test...")
    test_handler = test_error_handling_system()
    print(" Error handling system test completed!")