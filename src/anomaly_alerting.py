import boto3
import json
from datetime import datetime
from decimal import Decimal

class AnomalyAlertingSystem:
    def __init__(self, sns_topic_arn=None):
        """
        Initialize anomaly alerting system
        
        Args:
            sns_topic_arn: SNS topic ARN for sending alerts
        """
        self.sns_client = boto3.client('sns', region_name='us-east-1')
        self.sns_topic_arn = sns_topic_arn
        
        # If no topic ARN provided, create one
        if not self.sns_topic_arn:
            self.sns_topic_arn = self.create_sns_topic()
    
    def create_sns_topic(self):
        """Create SNS topic for anomaly alerts"""
        try:
            response = self.sns_client.create_topic(
                Name='energy-anomaly-alerts',
                Attributes={
                    'DisplayName': 'Energy Anomaly Alerts',
                    
                }
            )
            topic_arn = response['TopicArn']
            print(f"✅ Created SNS topic: {topic_arn}")
            return topic_arn
        except Exception as e:
            print(f"❌ Error creating SNS topic: {e}")
            return None
    
    def subscribe_email(self, email_address):
        """Subscribe email to anomaly alerts"""
        try:
            response = self.sns_client.subscribe(
                TopicArn=self.sns_topic_arn,
                Protocol='email',
                Endpoint=email_address
            )
            subscription_arn = response['SubscriptionArn']
            print(f"✅ Email subscription created: {email_address}")
            print(f"📧 Check your email to confirm subscription!")
            return subscription_arn
        except Exception as e:
            print(f"❌ Error subscribing email: {e}")
            return None
    
    def send_anomaly_alert(self, anomaly_record):
        """Send real-time anomaly alert"""
        try:
            site_id = anomaly_record.get('site_id', 'Unknown')
            timestamp = anomaly_record.get('timestamp', 'Unknown')
            energy_generated = anomaly_record.get('energy_generated_kwh', 0)
            energy_consumed = anomaly_record.get('energy_consumed_kwh', 0)
            anomaly_reasons = anomaly_record.get('anomaly_reasons', [])
            
            # Determine anomaly type
            anomaly_type = "Unknown"
            if 'negative_generation' in anomaly_reasons:
                anomaly_type = "Negative Energy Generation"
            elif 'negative_consumption' in anomaly_reasons:
                anomaly_type = "Negative Energy Consumption"
            
            # Create alert message
            subject = f"🚨 ENERGY ANOMALY DETECTED - {site_id}"
            
            message = f"""
🚨 ENERGY ANOMALY ALERT 🚨

Site: {site_id}
Time: {timestamp}
Anomaly Type: {anomaly_type}

📊 Energy Data:
• Generation: {energy_generated} kWh
• Consumption: {energy_consumed} kWh
• Net Energy: {float(energy_generated) - float(energy_consumed)} kWh

⚠️ Issue Details:
{', '.join(anomaly_reasons) if anomaly_reasons else 'Anomaly detected'}

🔧 Recommended Actions:
• Check site equipment status
• Verify sensor readings
• Investigate potential equipment failure
• Review maintenance logs

📈 Dashboard: http://localhost:8000/sites/{site_id}/anomalies

This is an automated alert from the Renewable Energy Monitoring System.
Alert generated at: {datetime.utcnow().isoformat()}Z
            """
            
            # Send SMS and email alert
            response = self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=message
            )
            
            message_id = response['MessageId']
            print(f"🚨 Anomaly alert sent! Message ID: {message_id}")
            print(f"   Site: {site_id} | Type: {anomaly_type}")
            
            return message_id
            
        except Exception as e:
            print(f"❌ Error sending anomaly alert: {e}")
            return None
    
    def send_daily_summary_alert(self, summary_data):
        """Send daily summary with anomaly statistics"""
        try:
            total_anomalies = summary_data.get('total_anomalies', 0)
            total_records = summary_data.get('total_records', 0)
            anomaly_rate = (total_anomalies / total_records * 100) if total_records > 0 else 0
            
            subject = f"📊 Daily Energy System Summary - {datetime.utcnow().strftime('%Y-%m-%d')}"
            
            message = f"""
📊 DAILY ENERGY SYSTEM SUMMARY

Date: {datetime.utcnow().strftime('%Y-%m-%d')}

🔢 System Statistics:
• Total Records Processed: {total_records:,}
• Total Anomalies Detected: {total_anomalies}
• Anomaly Rate: {anomaly_rate:.2f}%
• System Health: {'🟢 Excellent' if anomaly_rate < 1 else '🟡 Attention Needed' if anomaly_rate < 5 else '🔴 Critical'}

🏭 Site Performance:
"""
            
            # Add site-specific data if available
            if 'site_summaries' in summary_data:
                for site_id, site_data in summary_data['site_summaries'].items():
                    site_anomalies = site_data.get('anomaly_count', 0)
                    site_records = site_data.get('record_count', 0)
                    site_rate = (site_anomalies / site_records * 100) if site_records > 0 else 0
                    
                    message += f"""
• {site_id}: {site_records} records, {site_anomalies} anomalies ({site_rate:.1f}%)
  - Avg Generation: {site_data.get('avg_generation_kwh', 0):.1f} kWh
  - Avg Net Energy: {site_data.get('avg_net_energy_kwh', 0):.1f} kWh"""
            
            message += f"""

📈 Dashboard: http://localhost:8000/summary
📊 Visualizations: Open energy_dashboard.html

Generated by Renewable Energy Monitoring System
{datetime.utcnow().isoformat()}Z
            """
            
            response = self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=message
            )
            
            print(f"📊 Daily summary alert sent! Message ID: {response['MessageId']}")
            return response['MessageId']
            
        except Exception as e:
            print(f"❌ Error sending daily summary: {e}")
            return None

# Enhanced Lambda function with alerting
def enhanced_lambda_handler(event, context):
    """
    Enhanced Lambda function with anomaly alerting
    """
    # Initialize alerting system
    alerting = AnomalyAlertingSystem()
    
    try:
        # Original processing logic (same as before)
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Download and process file
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        records = json.loads(file_content)
        
        # Process records and detect anomalies
        processed_count = 0
        anomaly_count = 0
        anomalies_detected = []
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('energy-data')
        
        for record in records:
            processed_record = process_energy_record(record)
            
            if processed_record:
                # Store in DynamoDB
                table.put_item(Item=processed_record)
                processed_count += 1
                
                # Check for anomalies and send alerts
                if processed_record.get('anomaly', False):
                    anomaly_count += 1
                    anomalies_detected.append(processed_record)
                    
                    # Send real-time anomaly alert
                    alerting.send_anomaly_alert(processed_record)
        
        print(f"✅ Processed {processed_count} records")
        print(f"🚨 Found {anomaly_count} anomalies - alerts sent!")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {processed_count} records',
                'anomalies_found': anomaly_count,
                'alerts_sent': len(anomalies_detected),
                'source_file': key
            })
        }
        
    except Exception as e:
        # Send error alert
        error_message = f"""
🔴 SYSTEM ERROR ALERT

Error processing file: {key if 'key' in locals() else 'Unknown'}
Error: {str(e)}
Time: {datetime.utcnow().isoformat()}Z

Please check CloudWatch logs for details.
        """
        
        try:
            alerting.sns_client.publish(
                TopicArn=alerting.sns_topic_arn,
                Subject="🔴 Energy System Error",
                Message=error_message
            )
        except:
            pass  # Don't fail if alert fails
        
        print(f"❌ Error processing file: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'source_file': key if 'key' in locals() else 'unknown'
            })
        }

def process_energy_record(record):
    """Process individual energy record (same as before)"""
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
            'processed_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        return processed_record
        
    except Exception as e:
        print(f"❌ Error processing record: {record}, Error: {str(e)}")
        return None

# Test alerting system
def test_alerting_system():
    """Test the anomaly alerting system"""
    print("🧪 Testing Anomaly Alerting System...")
    
    # Initialize alerting
    alerting = AnomalyAlertingSystem()
    
    # Test anomaly record
    test_anomaly = {
        'site_id': 'SITE_001',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'energy_generated_kwh': -15.5,  # Negative generation (anomaly)
        'energy_consumed_kwh': 45.2,
        'anomaly': True,
        'anomaly_reasons': ['negative_generation']
    }
    
    # Send test alert
    message_id = alerting.send_anomaly_alert(test_anomaly)
    
    if message_id:
        print("✅ Test alert sent successfully!")
        print("📧 Check your email/SMS for the alert")
    else:
        print("❌ Test alert failed")

if __name__ == "__main__":
    # Setup and test alerting
    print("🚨 Setting up Anomaly Alerting System...")
    
    # Get user email for alerts
    email = input("Enter your email for anomaly alerts: ")
    
    alerting = AnomalyAlertingSystem()
    alerting.subscribe_email(email)
    
    # Test the system
    test_choice = input("Send test alert? (y/n): ")
    if test_choice.lower() == 'y':
        test_alerting_system()