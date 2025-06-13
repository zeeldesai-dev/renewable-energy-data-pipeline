import boto3
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import json

class EnergyDataVisualizer:
    def __init__(self):
        """Initialize the visualizer with DynamoDB connection"""
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('energy-data')
        
    def convert_decimals(self, obj):
        """Convert DynamoDB Decimal types to float"""
        if isinstance(obj, list):
            return [self.convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj
    
    def fetch_all_data(self):
        """Fetch all energy data from DynamoDB"""
        sites = ['SITE_001', 'SITE_002', 'SITE_003', 'SITE_004', 'SITE_005']
        all_data = []
        
        for site_id in sites:
            try:
                response = self.table.query(
                    KeyConditionExpression=Key('site_id').eq(site_id),
                    Limit=50,
                    ScanIndexForward=False
                )
                
                records = self.convert_decimals(response['Items'])
                all_data.extend(records)
                print(f"Fetched {len(records)} records for {site_id}")
                
            except Exception as e:
                print(f"Error fetching data for {site_id}: {e}")
        
        return all_data
    
    def create_dataframe(self, data):
        """Convert data to pandas DataFrame for easy visualization"""
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            
            # Ensure numeric columns are float
            numeric_cols = ['energy_generated_kwh', 'energy_consumed_kwh', 'net_energy_kwh']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def create_site_comparison_chart(self, df):
        """Create bar chart comparing average performance by site"""
        if df.empty:
            print("No data available for site comparison")
            return None
            
        site_summary = df.groupby('site_id').agg({
            'energy_generated_kwh': 'mean',
            'energy_consumed_kwh': 'mean', 
            'net_energy_kwh': 'mean'
        }).round(2)
        
        fig = go.Figure(data=[
            go.Bar(name='Generation', x=site_summary.index, y=site_summary['energy_generated_kwh'], 
                   marker_color='lightgreen'),
            go.Bar(name='Consumption', x=site_summary.index, y=site_summary['energy_consumed_kwh'],
                   marker_color='lightcoral'),
            go.Bar(name='Net Energy', x=site_summary.index, y=site_summary['net_energy_kwh'],
                   marker_color='lightblue')
        ])
        
        fig.update_layout(
            title='Average Energy Performance by Site',
            xaxis_title='Site ID',
            yaxis_title='Energy (kWh)',
            barmode='group',
            template='plotly_white'
        )
        
        return fig
    
    def create_time_series_chart(self, df):
        """Create time series chart showing energy trends"""
        if df.empty:
            print("No data available for time series")
            return None
            
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Energy Generation Over Time', 'Net Energy Over Time'),
            vertical_spacing=0.1
        )
        
        # Plot for each site
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        
        for i, site in enumerate(df['site_id'].unique()):
            site_data = df[df['site_id'] == site].sort_values('timestamp')
            color = colors[i % len(colors)]
            
            # Generation chart
            fig.add_trace(
                go.Scatter(x=site_data['timestamp'], y=site_data['energy_generated_kwh'],
                          mode='lines+markers', name=f'{site} Generation', 
                          line=dict(color=color)),
                row=1, col=1
            )
            
            # Net energy chart  
            fig.add_trace(
                go.Scatter(x=site_data['timestamp'], y=site_data['net_energy_kwh'],
                          mode='lines+markers', name=f'{site} Net Energy',
                          line=dict(color=color, dash='dash')),
                row=2, col=1
            )
        
        fig.update_layout(
            title_text="Energy Trends Over Time",
            template='plotly_white',
            height=800
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Generation (kWh)", row=1, col=1)
        fig.update_yaxes(title_text="Net Energy (kWh)", row=2, col=1)
        
        return fig
    
    def create_performance_heatmap(self, df):
        """Create heatmap showing performance by site and hour"""
        if df.empty:
            print("No data available for heatmap")
            return None
            
        # Group by site and hour
        heatmap_data = df.groupby(['site_id', 'hour'])['net_energy_kwh'].mean().reset_index()
        heatmap_pivot = heatmap_data.pivot(index='site_id', columns='hour', values='net_energy_kwh')
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            colorscale='RdYlGn',
            colorbar=dict(title="Net Energy (kWh)")
        ))
        
        fig.update_layout(
            title='Average Net Energy by Site and Hour',
            xaxis_title='Hour of Day',
            yaxis_title='Site ID',
            template='plotly_white'
        )
        
        return fig
    
    def create_summary_stats(self, df):
        """Create summary statistics visualization"""
        if df.empty:
            print("No data available for summary stats")
            return None
            
        # Calculate summary statistics
        summary = df.groupby('site_id').agg({
            'energy_generated_kwh': ['mean', 'max', 'min'],
            'energy_consumed_kwh': ['mean', 'max', 'min'],
            'net_energy_kwh': ['mean', 'max', 'min'],
            'anomaly': 'sum'
        }).round(2)
        
        print("\nENERGY PERFORMANCE SUMMARY:")
        print("=" * 50)
        for site in summary.index:
            print(f"\n🏭 {site}:")
            print(f"   Avg Generation: {summary.loc[site, ('energy_generated_kwh', 'mean')]} kWh")
            print(f"   Avg Consumption: {summary.loc[site, ('energy_consumed_kwh', 'mean')]} kWh") 
            print(f"   Avg Net Energy: {summary.loc[site, ('net_energy_kwh', 'mean')]} kWh")
            print(f"   Anomalies: {summary.loc[site, ('anomaly', 'sum')]}")
        
        return summary
    
    def generate_all_visualizations(self):
        """Generate all visualizations and save them"""
        print("Starting Energy Data Visualization...")
        
        # Fetch data
        print("Fetching data from DynamoDB...")
        data = self.fetch_all_data()
        
        if not data:
            print("No data found in DynamoDB")
            return
            
        print(f"Fetched {len(data)} total records")
        
        # Create DataFrame
        df = self.create_dataframe(data)
        print(f"Created DataFrame with {len(df)} rows")
        
        # Generate summary statistics
        self.create_summary_stats(df)
        
        # Create and save visualizations
        print("\nCreating visualizations...")
        
        # 1. Site comparison chart
        fig1 = self.create_site_comparison_chart(df)
        if fig1:
            fig1.write_html("site_comparison.html")
            fig1.show()
            print("Site comparison chart saved as 'site_comparison.html'")
        
        # 2. Time series chart
        fig2 = self.create_time_series_chart(df)
        if fig2:
            fig2.write_html("energy_trends.html")
            fig2.show()
            print("Energy trends chart saved as 'energy_trends.html'")
        
        # 3. Performance heatmap
        fig3 = self.create_performance_heatmap(df)
        if fig3:
            fig3.write_html("performance_heatmap.html")
            fig3.show()
            print("Performance heatmap saved as 'performance_heatmap.html'")
        
        print("\nAll visualizations completed!")
        print("HTML files saved in your project directory")
        print("Open the HTML files in your browser to view interactive charts")

def main():
    """Main function to run the visualizer"""
    visualizer = EnergyDataVisualizer()
    visualizer.generate_all_visualizations()

if __name__ == "__main__":
    main()