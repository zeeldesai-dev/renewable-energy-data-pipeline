import json
import random
import datetime
import boto3
import time
import signal
import sys
from typing import List, Dict

class ContinuousEnergyUploader:
    def __init__(self, bucket_name: str, interval_minutes: int = 5):
        """
        Initialize continuous uploader
        
        Args:
            bucket_name: S3 bucket name
            interval_minutes: Upload interval in minutes (default 5)
        """
        self.bucket_name = bucket_name
        self.interval_seconds = interval_minutes * 60
        self.s3_client = boto3.client('s3')
        self.sites = [f"SITE_{i:03d}" for i in range(1, 6)]  # 5 sites
        self.running = True
        self.upload_count = 0
        
        # Set up shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n Received shutdown signal. Stopping after {self.upload_count} uploads...")
        self.running = False
        
    def generate_realistic_record(self, site_id: str, base_time: datetime.datetime) -> Dict:
        """Generate realistic energy record with time-based patterns"""
        hour = base_time.hour
        
        # Realistic generation based on time of day 
        if 6 <= hour <= 18:  # Daylight hours
            base_generation = random.uniform(80, 200)
            # Peak around noon
            time_factor = 1 + 0.5 * abs(12 - hour) / 6
            generation = base_generation / time_factor
        else:  # Night hours
            generation = random.uniform(5, 20)  # Minimal generation
            
        # Realistic consumption (higher during day, lower at night)
        if 6 <= hour <= 22:  # Active hours
            consumption = random.uniform(60, 140)
        else:  # Night hours
            consumption = random.uniform(30, 70)
        
        # Add some variability
        generation *= random.uniform(0.8, 1.2)
        consumption *= random.uniform(0.9, 1.1)
        
        # Occasionally inject anomalies 
        if random.random() < 0.02:
            if random.random() < 0.5:
                generation = -random.uniform(1, 10)  # Negative generation
            else:
                consumption = -random.uniform(1, 10)  # Negative consumption
        
        return {
            "site_id": site_id,
            "timestamp": base_time.isoformat() + "Z",
            "energy_generated_kwh": round(generation, 2),
            "energy_consumed_kwh": round(consumption, 2)
        }
    
    def generate_batch(self, batch_time: datetime.datetime) -> List[Dict]:
        """Generate batch of records for all sites at specific time"""
        records = []
        
        
        for site_id in self.sites:
            num_records = random.randint(3, 5)
            for i in range(num_records):
                # Spread records across the 5-minute interval
                record_time = batch_time + datetime.timedelta(
                    seconds=random.randint(0, self.interval_seconds)
                )
                records.append(self.generate_realistic_record(site_id, record_time))
        
        return records
    
    def upload_batch(self, records: List[Dict]) -> bool:
        """Upload batch to S3"""
        try:
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_key = f"energy_data/continuous_batch_{timestamp}.json"
            
            json_data = json.dumps(records, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=json_data,
                ContentType='application/json'
            )
            
            self.upload_count += 1
            print(f"Upload #{self.upload_count}: {len(records)} records → s3://{self.bucket_name}/{file_key}")
            return True
            
        except Exception as e:
            print(f"Upload failed: {e}")
            return False
    
    def run_continuous(self, max_uploads: int = None):
        """
        Run continuous uploads
        
        Args:
            max_uploads: Maximum number of uploads (None for unlimited)
        """
        print(f"Starting continuous energy data uploads...")
        print(f"Uploading every {self.interval_seconds // 60} minutes")
        print(f"Monitoring {len(self.sites)} sites")
        if max_uploads:
            print(f"Maximum uploads: {max_uploads}")
        print(f"Press Ctrl+C to stop gracefully")
        print(f"Started at: {datetime.datetime.utcnow().isoformat()}Z")
        print("=" * 60)
        
        while self.running:
            try:
                # Generate and upload batch
                batch_time = datetime.datetime.utcnow()
                records = self.generate_batch(batch_time)
                
                success = self.upload_batch(records)
                
                if success:
                    print(f" Next upload in {self.interval_seconds // 60} minutes at {(batch_time + datetime.timedelta(seconds=self.interval_seconds)).strftime('%H:%M:%S')}")
                
                # Check if we've reached max uploads
                if max_uploads and self.upload_count >= max_uploads:
                    print(f"Reached maximum uploads ({max_uploads}). Stopping...")
                    break
                
                # Wait for next interval
                if self.running:
                    for remaining in range(self.interval_seconds, 0, -1):
                        if not self.running:
                            break
                        if remaining % 60 == 0:  # Print every minute
                            print(f"   ⏳ {remaining // 60} minutes until next upload...")
                        time.sleep(1)
                        
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"Error in upload loop: {e}")
                time.sleep(10)  # Wait before retrying
        
        print(f"\nContinuous uploader stopped after {self.upload_count} uploads")
        print(f"Stopped at: {datetime.datetime.utcnow().isoformat()}Z")

def main():
    """Main function with configuration"""
    # Configuration
    BUCKET_NAME = "zeel-energy-data-2025"  # Bucket name
    INTERVAL_MINUTES = 5  # Upload every 5 minutes
    MAX_UPLOADS = 12  # Run for 1 hour (12 * 5 minutes) - set to None for unlimited
    
    print("CONTINUOUS ENERGY DATA UPLOADER")
    print("=" * 40)
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Interval: {INTERVAL_MINUTES} minutes")
    print(f"Max uploads: {MAX_UPLOADS if MAX_UPLOADS else 'Unlimited'}")
    print("=" * 40)
    
    # Create uploader
    uploader = ContinuousEnergyUploader(BUCKET_NAME, INTERVAL_MINUTES)
    
    # Start continuous uploads
    uploader.run_continuous(max_uploads=MAX_UPLOADS)

if __name__ == "__main__":
    main()