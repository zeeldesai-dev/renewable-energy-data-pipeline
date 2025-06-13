from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import json
from decimal import Decimal

# Initialize FastAPI app
app = FastAPI(
    title="Renewable Energy Data API",
    description="Complete API to query processed energy generation and consumption data",
    version="2.0.0"
)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('energy-data')

def convert_decimals(obj):
    """Convert DynamoDB Decimal types to float"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

@app.get("/")
async def root():
    """API welcome message with all endpoints"""
    return {
        "message": "Renewable Energy Data API v2.0",
        "status": "running",
        "endpoints": {
            "GET /sites/{site_id}": "Get data for a specific site with optional time range",
            "GET /sites/{site_id}/anomalies": "Get anomalies for a specific site",
            "GET /sites/{site_id}/range": "Get data for specific time range",
            "GET /anomalies": "Get all anomalies across all sites",
            "GET /summary": "Get performance summary of all sites",
            "GET /health": "Check API health and database connectivity"
        },
        "example_urls": {
            "site_data": "/sites/SITE_001",
            "site_anomalies": "/sites/SITE_001/anomalies",
            "time_range": "/sites/SITE_001/range?start_date=2025-06-11&end_date=2025-06-12",
            "all_anomalies": "/anomalies",
            "summary": "/summary"
        }
    }

@app.get("/sites/{site_id}")
async def get_site_data(
    site_id: str,
    limit: Optional[int] = Query(50, description="Maximum number of records to return"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get data for a specific site with optional time filtering"""
    try:
        # Build query
        query_kwargs = {
            'KeyConditionExpression': Key('site_id').eq(site_id),
            'Limit': limit,
            'ScanIndexForward': False  # Most recent first
        }
        
        # Add time range filter if provided
        if start_date or end_date:
            filter_conditions = []
            if start_date:
                filter_conditions.append(Attr('timestamp').gte(start_date))
            if end_date:
                filter_conditions.append(Attr('timestamp').lte(end_date + 'T23:59:59Z'))
            
            if filter_conditions:
                filter_expr = filter_conditions[0]
                for condition in filter_conditions[1:]:
                    filter_expr = filter_expr & condition
                query_kwargs['FilterExpression'] = filter_expr
        
        response = table.query(**query_kwargs)
        records = convert_decimals(response['Items'])
        
        # Calculate basic stats
        total_records = len(records)
        anomaly_count = sum(1 for r in records if r.get('anomaly', False))
        avg_generation = sum(r.get('energy_generated_kwh', 0) for r in records) / total_records if total_records > 0 else 0
        avg_consumption = sum(r.get('energy_consumed_kwh', 0) for r in records) / total_records if total_records > 0 else 0
        
        return {
            "site_id": site_id,
            "query_params": {
                "limit": limit,
                "start_date": start_date,
                "end_date": end_date
            },
            "statistics": {
                "total_records": total_records,
                "anomaly_count": anomaly_count,
                "avg_generation_kwh": round(avg_generation, 2),
                "avg_consumption_kwh": round(avg_consumption, 2)
            },
            "records": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying site data: {str(e)}")

@app.get("/sites/{site_id}/anomalies")
async def get_site_anomalies(
    site_id: str,
    limit: Optional[int] = Query(50, description="Maximum number of anomalies to return")
):
    """Get all anomalies for a specific site"""
    try:
        response = table.query(
            KeyConditionExpression=Key('site_id').eq(site_id),
            FilterExpression=Attr('anomaly').eq(True),
            Limit=limit,
            ScanIndexForward=False
        )
        
        anomalies = convert_decimals(response['Items'])
        
        # Analyze anomaly types
        negative_generation = sum(1 for a in anomalies if a.get('energy_generated_kwh', 0) < 0)
        negative_consumption = sum(1 for a in anomalies if a.get('energy_consumed_kwh', 0) < 0)
        
        return {
            "site_id": site_id,
            "anomaly_summary": {
                "total_anomalies": len(anomalies),
                "negative_generation_count": negative_generation,
                "negative_consumption_count": negative_consumption
            },
            "anomalies": anomalies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying anomalies: {str(e)}")

@app.get("/sites/{site_id}/range")
async def get_site_data_by_range(
    site_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(100, description="Maximum records to return")
):
    """Get site data for a specific time range (REQUIRED parameters)"""
    try:
        response = table.query(
            KeyConditionExpression=Key('site_id').eq(site_id),
            FilterExpression=Attr('timestamp').between(start_date, end_date + 'T23:59:59Z'),
            Limit=limit,
            ScanIndexForward=True  # Chronological order for time range
        )
        
        records = convert_decimals(response['Items'])
        
        return {
            "site_id": site_id,
            "time_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "record_count": len(records),
            "records": records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying time range: {str(e)}")

@app.get("/anomalies")
async def get_all_anomalies(
    limit: Optional[int] = Query(100, description="Maximum anomalies to return across all sites")
):
    """Get anomalies across all sites"""
    try:
        sites = ['SITE_001', 'SITE_002', 'SITE_003', 'SITE_004', 'SITE_005']
        all_anomalies = []
        
        for site_id in sites:
            response = table.query(
                KeyConditionExpression=Key('site_id').eq(site_id),
                FilterExpression=Attr('anomaly').eq(True),
                Limit=limit // len(sites),  # Distribute limit across sites
                ScanIndexForward=False
            )
            
            site_anomalies = convert_decimals(response['Items'])
            all_anomalies.extend(site_anomalies)
        
        # Sort by timestamp (most recent first)
        all_anomalies.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Limit total results
        all_anomalies = all_anomalies[:limit]
        
        # Analyze by site
        anomaly_by_site = {}
        for anomaly in all_anomalies:
            site = anomaly.get('site_id')
            if site not in anomaly_by_site:
                anomaly_by_site[site] = 0
            anomaly_by_site[site] += 1
        
        return {
            "total_anomalies": len(all_anomalies),
            "anomalies_by_site": anomaly_by_site,
            "anomalies": all_anomalies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying all anomalies: {str(e)}")

@app.get("/summary")
async def get_summary():
    """Get comprehensive performance summary for all sites"""
    try:
        sites = ['SITE_001', 'SITE_002', 'SITE_003', 'SITE_004', 'SITE_005']
        summary = {}
        overall_stats = {
            "total_records": 0,
            "total_anomalies": 0,
            "total_generation": 0,
            "total_consumption": 0
        }
        
        for site_id in sites:
            response = table.query(
                KeyConditionExpression=Key('site_id').eq(site_id),
                Limit=100
            )
            
            records = response['Items']
            if records:
                # Calculate site statistics
                total_generated = sum(float(r.get('energy_generated_kwh', 0)) for r in records)
                total_consumed = sum(float(r.get('energy_consumed_kwh', 0)) for r in records)
                net_energy = sum(float(r.get('net_energy_kwh', 0)) for r in records)
                anomaly_count = sum(1 for r in records if r.get('anomaly', False))
                
                site_summary = {
                    "record_count": len(records),
                    "avg_generation_kwh": round(total_generated / len(records), 2),
                    "avg_consumption_kwh": round(total_consumed / len(records), 2),
                    "avg_net_energy_kwh": round(net_energy / len(records), 2),
                    "total_generation_kwh": round(total_generated, 2),
                    "total_consumption_kwh": round(total_consumed, 2),
                    "anomaly_count": anomaly_count,
                    "anomaly_rate_percent": round((anomaly_count / len(records)) * 100, 1)
                }
                
                summary[site_id] = site_summary
                
                # Update overall stats
                overall_stats["total_records"] += len(records)
                overall_stats["total_anomalies"] += anomaly_count
                overall_stats["total_generation"] += total_generated
                overall_stats["total_consumption"] += total_consumed
        
        return {
            "summary_timestamp": datetime.utcnow().isoformat() + 'Z',
            "overall_statistics": {
                "total_sites": len(summary),
                "total_records": overall_stats["total_records"],
                "total_anomalies": overall_stats["total_anomalies"],
                "overall_anomaly_rate_percent": round((overall_stats["total_anomalies"] / overall_stats["total_records"]) * 100, 1) if overall_stats["total_records"] > 0 else 0,
                "total_generation_kwh": round(overall_stats["total_generation"], 2),
                "total_consumption_kwh": round(overall_stats["total_consumption"], 2),
                "total_net_energy_kwh": round(overall_stats["total_generation"] - overall_stats["total_consumption"], 2)
            },
            "site_summaries": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        # Test DynamoDB connection
        response = table.scan(Limit=1)
        record_count = response.get('Count', 0)
        
        # Test AWS connectivity
        s3_client = boto3.client('s3')
        s3_client.head_bucket(Bucket='zeel-energy-data-2025')
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "services": {
                "dynamodb": "connected",
                "s3": "accessible",
                "api": "running"
            },
            "data_available": record_count > 0,
            "version": "2.0.0"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "error": str(e),
            "version": "2.0.0"
        }

if __name__ == "__main__":
    import uvicorn
    print("Starting Energy Data API...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)