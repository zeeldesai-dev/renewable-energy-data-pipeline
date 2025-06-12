import json
import boto3
import datetime
from decimal import Decimal

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('energy-data')

def lambda_handler(event, context):
    """
    AWS Lambda function to process energy data files uploaded to S3
    """
    try:
        # Get bucket and object key from S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Download file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        
        # Parse JSON data
        records = json.loads(file_content)
        print(f"Found {len(records)} records to process")
        
        # Process each record
        processed_count = 0
        anomaly_count = 0
        
        for record in records:
            processed_record = process_energy_record(record)
            
            if processed_record:
                # Store in DynamoDB
                store_in_dynamodb(processed_record)
                processed_count += 1
                
                if processed_record.get('anomaly', False):
                    anomaly_count += 1
        
        print(f"✅ Successfully processed {processed_count} records")
        print(f"⚠️ Found {anomaly_count} anomalies")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {processed_count} records',
                'anomalies_found': anomaly_count,
                'source_file': key
            })
        }
        
    except Exception as e:
        print(f"❌ Error processing file: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'source_file': key if 'key' in locals() else 'unknown'
            })
        }

def process_energy_record(record):
    """
    Process a single energy record: calculate net energy and detect anomalies
    """
    try:
        site_id = record['site_id']
        timestamp = record['timestamp']
        energy_generated = float(record['energy_generated_kwh'])
        energy_consumed = float(record['energy_consumed_kwh'])
        
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
        processed_record = {
            'site_id': site_id,
            'timestamp': timestamp,
            'energy_generated_kwh': Decimal(str(energy_generated)),
            'energy_consumed_kwh': Decimal(str(energy_consumed)),
            'net_energy_kwh': Decimal(str(net_energy)),
            'anomaly': anomaly,
            'anomaly_reasons': anomaly_reasons,
            'processed_at': datetime.datetime.utcnow().isoformat() + 'Z'
        }
        
        return processed_record
        
    except Exception as e:
        print(f"❌ Error processing record: {record}, Error: {str(e)}")
        return None

def store_in_dynamodb(record):
    """
    Store processed record in DynamoDB
    """
    try:
        table.put_item(Item=record)
        print(f"✅ Stored record: {record['site_id']} at {record['timestamp']}")
        
    except Exception as e:
        print(f"❌ Error storing record in DynamoDB: {str(e)}")
        raise

# For local testing
def test_locally():
    """
    Test function locally with sample data
    """
    # Sample S3 event structure
    test_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'zeel-energy-data-2025'},
                'object': {'key': 'energy_data/test_batch_20250608_001529.json'}
            }
        }]
    }
    
    # Test the lambda function
    result = lambda_handler(test_event, None)
    print("Test result:", result)

if __name__ == "__main__":
    # Run local test
    test_locally()