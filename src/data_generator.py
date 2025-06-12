import json
import random
import datetime
import boto3

BUCKET_NAME = "zeel-energy-data-2025"

def generate_energy_record(site_id):
    """Generate a single energy record"""
    # Generate realistic energy data
    generation = round(random.uniform(50, 200), 2)  # 50-200 kWh
    consumption = round(random.uniform(30, 150), 2)  # 30-150 kWh
    
    # Occasionally add anomalies (5% chance)
    if random.random() < 0.05:
        if random.random() < 0.5:
            generation = -random.uniform(1, 10)  # Negative generation
        else:
            consumption = -random.uniform(1, 10)  # Negative consumption
    
    return {
        "site_id": site_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "energy_generated_kwh": generation,
        "energy_consumed_kwh": consumption
    }

def generate_test_data():
    """Generate test data for 5 sites"""
    sites = ["SITE_001", "SITE_002", "SITE_003", "SITE_004", "SITE_005"]
    records = []
    
    # Generate 5 records per site (25 total)
    for site in sites:
        for _ in range(5):
            records.append(generate_energy_record(site))
    
    return records

def upload_to_s3(records):
    """Upload records to S3"""
    try:
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Create filename with timestamp
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"energy_data/test_batch_{timestamp}.json"
        
        # Convert to JSON
        json_data = json.dumps(records, indent=2)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=json_data,
            ContentType='application/json'
        )
        
        print(f"✅ SUCCESS! Uploaded {len(records)} records to:")
        print(f"   s3://{BUCKET_NAME}/{filename}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🚀 Energy Data Generator Starting...")
    print("📊 Generating test data...")
    
    # Generate test data
    records = generate_test_data()
    
    print(f"📝 Generated {len(records)} records for 5 sites")
    print("📤 Uploading to S3...")
    
    # Upload to S3
    success = upload_to_s3(records)
    
    if success:
        print("🎉 Test completed successfully!")
        print("🔍 Check your S3 bucket in AWS Console to see the file")
    else:
        print("❌ Test failed - check your AWS credentials")

if __name__ == "__main__":
    main()