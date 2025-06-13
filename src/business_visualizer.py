import requests
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime

class EnergyBusinessVisualizer:
    def __init__(self, api_base_url="http://localhost:8000"):
        """Initialize with API connection"""
        self.api_url = api_base_url
        
    def fetch_api_data(self, endpoint):
        """Fetch data from API endpoint"""
        try:
            response = requests.get(f"{self.api_url}{endpoint}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return None
    
    def create_site_performance_comparison(self):
        """Create bar chart comparing site performance"""
        print("Creating Site Performance Comparison...")
        
        # Fetch summary data
        summary_data = self.fetch_api_data("/summary")
        
        if not summary_data or 'site_summaries' not in summary_data:
            print("No summary data available")
            return None
            
        sites = []
        avg_generation = []
        avg_consumption = []
        avg_net_energy = []
        record_counts = []
        
        for site_id, data in summary_data['site_summaries'].items():
            sites.append(site_id)
            avg_generation.append(data.get('avg_generation_kwh', 0))
            avg_consumption.append(data.get('avg_consumption_kwh', 0))
            avg_net_energy.append(data.get('avg_net_energy_kwh', 0))
            record_counts.append(data.get('record_count', 0))
        
        # Create grouped bar chart
        fig = go.Figure(data=[
            go.Bar(name='Average Generation', x=sites, y=avg_generation, 
                   marker_color='lightgreen', text=[f'{x:.1f}' for x in avg_generation], textposition='auto'),
            go.Bar(name='Average Consumption', x=sites, y=avg_consumption,
                   marker_color='lightcoral', text=[f'{x:.1f}' for x in avg_consumption], textposition='auto'),
            go.Bar(name='Net Energy', x=sites, y=avg_net_energy,
                   marker_color='lightblue', text=[f'{x:.1f}' for x in avg_net_energy], textposition='auto')
        ])
        
        fig.update_layout(
            title='Energy Performance Comparison by Site',
            xaxis_title='Energy Sites',
            yaxis_title='Energy (kWh)',
            barmode='group',
            template='plotly_white',
            height=500,
            showlegend=True
        )
        
        # Save and show
        fig.write_html("site_performance_comparison.html")
        fig.show()
        print("Site performance chart saved as 'site_performance_comparison.html'")
        
        return fig
    
    def create_energy_efficiency_chart(self):
        """Create efficiency analysis chart"""
        print("Creating Energy Efficiency Analysis...")
        
        summary_data = self.fetch_api_data("/summary")
        
        if not summary_data or 'site_summaries' not in summary_data:
            print("No summary data available")
            return None
            
        sites = []
        efficiency_ratios = []
        net_energies = []
        colors = []
        
        for site_id, data in summary_data['site_summaries'].items():
            generation = data.get('avg_generation_kwh', 0)
            consumption = data.get('avg_consumption_kwh', 0)
            net_energy = data.get('avg_net_energy_kwh', 0)
            
            # Calculate efficiency ratio (generation/consumption)
            efficiency = (generation / consumption * 100) if consumption > 0 else 0
            
            sites.append(site_id)
            efficiency_ratios.append(efficiency)
            net_energies.append(net_energy)
            
            # Color coding: green = efficient, yellow = moderate, red = inefficient
            if efficiency >= 120:
                colors.append('green')
            elif efficiency >= 100:
                colors.append('orange')
            else:
                colors.append('red')
        
        # Create scatter plot
        fig = go.Figure(data=go.Scatter(
            x=efficiency_ratios,
            y=net_energies,
            mode='markers+text',
            marker=dict(size=15, color=colors, opacity=0.8),
            text=sites,
            textposition="middle center",
            textfont=dict(color="white", size=10)
        ))
        
        fig.update_layout(
            title='Site Efficiency Analysis<br><sub>X-axis: Generation/Consumption Ratio (%) | Y-axis: Net Energy (kWh)</sub>',
            xaxis_title='Efficiency Ratio (%)',
            yaxis_title='Average Net Energy (kWh)',
            template='plotly_white',
            height=500
        )
        
        # Add efficiency zones
        fig.add_hline(y=0, line_dash="dash", line_color="red", 
                     annotation_text="Break-even line", annotation_position="bottom right")
        fig.add_vline(x=100, line_dash="dash", line_color="blue",
                     annotation_text="100% Efficiency", annotation_position="top left")
        
        fig.write_html("energy_efficiency_analysis.html")
        fig.show()
        print("Energy efficiency chart saved as 'energy_efficiency_analysis.html'")
        
        return fig
    
    def create_anomaly_distribution_chart(self):
        """Create anomaly distribution visualization"""
        print("Creating Anomaly Distribution Analysis...")
        
        # Get anomaly data for all sites
        all_anomalies = self.fetch_api_data("/anomalies")
        
        if not all_anomalies:
            print("No anomaly data available")
            return None
        
        anomaly_count = all_anomalies.get('total_anomalies', 0)
        anomalies_by_site = all_anomalies.get('anomalies_by_site', {})
        
        if anomaly_count == 0:
            # Create a "no anomalies" visualization
            fig = go.Figure(data=go.Bar(
                x=['SITE_001', 'SITE_002', 'SITE_003', 'SITE_004', 'SITE_005'],
                y=[0, 0, 0, 0, 0],
                marker_color='lightgreen',
                text=['No Anomalies'] * 5,
                textposition='auto'
            ))
            
            fig.update_layout(
                title='Anomaly Distribution Across Sites<br><sub>✅ All sites operating normally</sub>',
                xaxis_title='Energy Sites',
                yaxis_title='Number of Anomalies',
                template='plotly_white',
                height=400
            )
            
        else:
            # Create pie chart for anomaly distribution
            sites = list(anomalies_by_site.keys())
            counts = list(anomalies_by_site.values())
            
            fig = go.Figure(data=[go.Pie(
                labels=sites,
                values=counts,
                hole=0.3,
                textinfo='label+percent+value'
            )])
            
            fig.update_layout(
                title=f'Anomaly Distribution Across Sites<br><sub>Total: {anomaly_count} anomalies detected</sub>',
                template='plotly_white',
                height=500
            )
        
        fig.write_html("anomaly_distribution.html")
        fig.show()
        print("Anomaly distribution chart saved as 'anomaly_distribution.html'")
        
        return fig
    
    def create_overall_summary_dashboard(self):
        """Create summary dashboard with key metrics"""
        print("Creating Overall Summary Dashboard...")
        
        summary_data = self.fetch_api_data("/summary")
        
        if not summary_data:
            print("No summary data available")
            return None
            
        overall_stats = summary_data.get('overall_statistics', {})
        
        # Create dashboard with key metrics
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Total Energy Generation vs Consumption',
                'System Health Overview', 
                'Record Distribution by Site',
                'Performance Summary'
            ),
            specs=[[{"type": "bar"}, {"type": "indicator"}],
                   [{"type": "pie"}, {"type": "table"}]]
        )
        
        # Chart 1: Total Generation vs Consumption
        fig.add_trace(
            go.Bar(x=['Generation', 'Consumption'], 
                   y=[overall_stats.get('total_generation_kwh', 0),
                      overall_stats.get('total_consumption_kwh', 0)],
                   marker_color=['lightgreen', 'lightcoral'],
                   name='Energy'),
            row=1, col=1
        )
        
        # Chart 2: System Health Indicator
        anomaly_rate = overall_stats.get('overall_anomaly_rate_percent', 0)
        health_score = max(0, 100 - anomaly_rate * 10)  # Simple health calculation
        
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=health_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "System Health Score"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "green" if health_score > 80 else "orange" if health_score > 60 else "red"},
                    'steps': [{'range': [0, 60], 'color': "lightgray"},
                             {'range': [60, 80], 'color': "yellow"},
                             {'range': [80, 100], 'color': "lightgreen"}],
                    'threshold': {'line': {'color': "red", 'width': 4},
                                'thickness': 0.75, 'value': 90}
                }
            ),
            row=1, col=2
        )
        
        # Chart 3: Records by site (if we have site summaries)
        if 'site_summaries' in summary_data:
            sites = list(summary_data['site_summaries'].keys())
            record_counts = [data.get('record_count', 0) for data in summary_data['site_summaries'].values()]
            
            fig.add_trace(
                go.Pie(labels=sites, values=record_counts, name="Records"),
                row=2, col=1
            )
        
        # Chart 4: Summary table
        fig.add_trace(
            go.Table(
                header=dict(values=['Metric', 'Value'],
                           fill_color='lightblue',
                           align='left'),
                cells=dict(values=[
                    ['Total Sites', 'Total Records', 'Total Anomalies', 'Anomaly Rate', 'Net Energy'],
                    [overall_stats.get('total_sites', 0),
                     overall_stats.get('total_records', 0),
                     overall_stats.get('total_anomalies', 0),
                     f"{overall_stats.get('overall_anomaly_rate_percent', 0)}%",
                     f"{overall_stats.get('total_net_energy_kwh', 0)} kWh"]
                ], fill_color='white', align='left')
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title_text="Renewable Energy System Dashboard",
            template='plotly_white',
            height=800,
            showlegend=False
        )
        
        fig.write_html("energy_dashboard.html")
        fig.show()
        print("Overall dashboard saved as 'energy_dashboard.html'")
        
        return fig
    
    def generate_all_business_visualizations(self):
        """Generate all business-focused visualizations"""
        print("Generating Business-Focused Energy Visualizations...")
        print("=" * 60)
        
        # Check API health first
        health = self.fetch_api_data("/health")
        if not health or health.get('status') != 'healthy':
            print("API is not responding or unhealthy")
            return
        
        print("API is healthy - proceeding with visualizations...")
        
        # Generate all visualizations
        viz_count = 0
        
        if self.create_site_performance_comparison():
            viz_count += 1
            
        if self.create_energy_efficiency_chart():
            viz_count += 1
            
        if self.create_anomaly_distribution_chart():
            viz_count += 1
            
        if self.create_overall_summary_dashboard():
            viz_count += 1
        
        print("=" * 60)
        print(f"Generated {viz_count} business visualizations!")
        print("HTML files saved in your project directory:")
        print("   • site_performance_comparison.html")
        print("   • energy_efficiency_analysis.html") 
        print("   • anomaly_distribution.html")
        print("   • energy_dashboard.html")
        print("Open these files in your browser for interactive charts")

def main():
    """Main function"""
    visualizer = EnergyBusinessVisualizer()
    visualizer.generate_all_business_visualizations()

if __name__ == "__main__":
    main()