"""Memory graph visualization using Plotly and NetworkX."""
import plotly.graph_objects as go
import networkx as nx
from typing import List, Dict, Tuple, Optional
from memory.hybrid import HybridMemory
import json
import time


class MemoryVisualizer:
    """Visualize memory graph and statistics."""
    
    def __init__(self, memory: HybridMemory):
        """
        Initialize visualizer with memory instance.
        
        Args:
            memory: HybridMemory instance to visualize
        """
        self.memory = memory
    
    def create_graph_network(self) -> Tuple[go.Figure, Dict]:
        """
        Create interactive network graph of memories.
        
        Returns:
            Tuple of (Plotly figure, statistics dict)
        """
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes from memory graph
        for node_id, node in self.memory.graph.nodes.items():
            # Truncate content for display
            label = node.content[:30] + "..." if len(node.content) > 30 else node.content
            
            G.add_node(
                node_id,
                label=label,
                type=node.type,
                importance=node.importance,
                full_content=node.content,
                timestamp=node.timestamp,
                access_count=node.access_count
            )
        
        # Add edges (connections)
        for node_id, node in self.memory.graph.nodes.items():
            for conn in node.connections:
                if isinstance(conn, tuple):
                    target_id, weight = conn
                else:
                    target_id, weight = conn, 1.0
                
                if target_id in G.nodes:
                    G.add_edge(node_id, target_id, weight=weight)
        
        # If no nodes, return empty figure
        if len(G.nodes) == 0:
            fig = go.Figure()
            fig.update_layout(
                title="No memories to visualize",
                annotations=[{
                    'text': 'Create some memories to see the graph!',
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.5,
                    'y': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'middle',
                    'showarrow': False,
                    'font': {'size': 16}
                }]
            )
            return fig, {'total_nodes': 0, 'total_edges': 0, 'avg_connections': 0}
        
        # Generate layout
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # Create edge traces
        edge_trace = go.Scatter(
            x=[],
            y=[],
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        )
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace['x'] += tuple([x0, x1, None])
            edge_trace['y'] += tuple([y0, y1, None])
        
        # Create node traces by type
        node_traces = []
        type_colors = {
            'fact': '#1f77b4',       # Blue
            'thought': '#ff7f0e',    # Orange
            'preference': '#2ca02c', # Green
            'tool_output': '#d62728',# Red
            'result': '#9467bd'      # Purple
        }
        
        memory_types = set(nx.get_node_attributes(G, 'type').values())
        
        for node_type in memory_types:
            nodes_of_type = [n for n in G.nodes() if G.nodes[n]['type'] == node_type]
            
            if not nodes_of_type:
                continue
            
            node_trace = go.Scatter(
                x=[pos[n][0] for n in nodes_of_type],
                y=[pos[n][1] for n in nodes_of_type],
                mode='markers+text',
                hoverinfo='text',
                name=node_type.capitalize(),
                marker=dict(
                    color=type_colors.get(node_type, '#999'),
                    size=[10 + G.nodes[n]['importance'] * 20 for n in nodes_of_type],
                    line=dict(width=2, color='white'),
                    opacity=0.8
                ),
                text=[G.nodes[n]['label'] for n in nodes_of_type],
                textposition="top center",
                textfont=dict(size=8),
                hovertext=[
                    f"<b>Type:</b> {G.nodes[n]['type']}<br>"
                    f"<b>Importance:</b> {G.nodes[n]['importance']:.2f}<br>"
                    f"<b>Accessed:</b> {G.nodes[n]['access_count']} times<br>"
                    f"<b>Content:</b> {G.nodes[n]['full_content'][:100]}..."
                    for n in nodes_of_type
                ]
            )
            node_traces.append(node_trace)
        
        # Create figure
        fig = go.Figure(
            data=[edge_trace] + node_traces,
            layout=go.Layout(
                title=dict(
                    text='<b>Memory Graph Network</b>',
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20)
                ),
                showlegend=True,
                hovermode='closest',
                margin=dict(b=20, l=20, r=20, t=60),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='#f9f9f9',
                height=600,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
        )
        
        # Calculate stats
        stats = {
            'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(),
            'avg_connections': G.number_of_edges() / max(G.number_of_nodes(), 1),
            'types': dict(nx.get_node_attributes(G, 'type'))
        }
        
        return fig, stats
    
    def create_importance_distribution(self) -> go.Figure:
        """
        Create importance distribution histogram.
        
        Returns:
            Plotly figure
        """
        importances = [node.importance for node in self.memory.graph.nodes.values()]
        
        if not importances:
            fig = go.Figure()
            fig.update_layout(title="No data available")
            return fig
        
        fig = go.Figure(data=[
            go.Histogram(
                x=importances,
                nbinsx=20,
                marker=dict(
                    color='#1f77b4',
                    line=dict(color='white', width=1)
                ),
                hovertemplate='<b>Importance:</b> %{x:.2f}<br><b>Count:</b> %{y}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title='<b>Memory Importance Distribution</b>',
            xaxis_title='Importance Score',
            yaxis_title='Number of Memories',
            plot_bgcolor='#f9f9f9',
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_memory_timeline(self) -> go.Figure:
        """
        Create timeline of memory creation.
        
        Returns:
            Plotly figure
        """
        import datetime
        from collections import defaultdict
        
        memories = sorted(
            self.memory.graph.nodes.values(),
            key=lambda x: x.timestamp
        )
        
        if not memories:
            fig = go.Figure()
            fig.update_layout(
                title="No memories to display",
                xaxis_title="Date",
                yaxis_title="Memories Created"
            )
            return fig
        
        # Group by day
        by_day = defaultdict(lambda: {'count': 0, 'types': defaultdict(int)})
        
        for mem in memories:
            date = datetime.datetime.fromtimestamp(mem.timestamp).date()
            by_day[date]['count'] += 1
            by_day[date]['types'][mem.type] += 1
        
        dates = sorted(by_day.keys())
        counts = [by_day[d]['count'] for d in dates]
        
        fig = go.Figure(data=[
            go.Scatter(
                x=dates,
                y=counts,
                mode='lines+markers',
                marker=dict(size=8, color='#1f77b4'),
                line=dict(width=2, color='#1f77b4'),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.2)',
                hovertemplate='<b>Date:</b> %{x}<br><b>Memories:</b> %{y}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title='<b>Memory Creation Timeline</b>',
            xaxis_title='Date',
            yaxis_title='Memories Created',
            plot_bgcolor='#f9f9f9',
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_type_distribution(self) -> go.Figure:
        """
        Create pie chart of memory types.
        
        Returns:
            Plotly figure
        """
        from collections import Counter
        
        types = [node.type for node in self.memory.graph.nodes.values()]
        
        if not types:
            fig = go.Figure()
            fig.update_layout(title="No data available")
            return fig
        
        type_counts = Counter(types)
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(type_counts.keys()),
                values=list(type_counts.values()),
                hole=0.3,
                marker=dict(colors=colors),
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>',
                textinfo='label+percent',
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title='<b>Memory Types Distribution</b>',
            height=400,
            showlegend=True
        )
        
        return fig
    
    def create_access_heatmap(self) -> go.Figure:
        """
        Create heatmap of memory access patterns.
        
        Returns:
            Plotly figure
        """
        import datetime
        from collections import defaultdict
        
        memories = list(self.memory.graph.nodes.values())
        
        if not memories:
            fig = go.Figure()
            fig.update_layout(title="No data available")
            return fig
        
        # Create access pattern matrix
        access_data = defaultdict(lambda: defaultdict(int))
        
        for mem in memories:
            date = datetime.datetime.fromtimestamp(mem.timestamp)
            hour = date.hour
            day = date.strftime('%Y-%m-%d')
            access_data[day][hour] += 1
        
        # Convert to matrix
        days = sorted(access_data.keys())
        hours = list(range(24))
        
        z_data = [[access_data[day][hour] for hour in hours] for day in days]
        
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=[f"{h:02d}:00" for h in hours],
            y=days,
            colorscale='Blues',
            hovertemplate='<b>Day:</b> %{y}<br><b>Hour:</b> %{x}<br><b>Memories:</b> %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title='<b>Memory Creation Heatmap</b>',
            xaxis_title='Hour of Day',
            yaxis_title='Date',
            height=400
        )
        
        return fig
    
    def get_memory_table_data(self) -> List[Dict]:
        """
        Get memory data formatted for table display.
        
        Returns:
            List of dictionaries with memory data
        """
        data = []
        
        for node in self.memory.graph.nodes.values():
            # Format timestamp
            import datetime
            date_str = datetime.datetime.fromtimestamp(node.timestamp).strftime('%Y-%m-%d %H:%M')
            
            data.append({
                'id': node.id,
                'type': node.type,
                'content': node.content[:100] + '...' if len(node.content) > 100 else node.content,
                'importance': f"{node.importance:.2f}",
                'connections': len(node.connections),
                'access_count': node.access_count,
                'created': date_str
            })
        
        # Sort by importance (descending)
        return sorted(data, key=lambda x: float(x['importance']), reverse=True)
    
    def get_statistics_summary(self) -> Dict:
        """
        Get comprehensive statistics summary.
        
        Returns:
            Dictionary with various statistics
        """
        nodes = list(self.memory.graph.nodes.values())
        
        if not nodes:
            return {
                'total_memories': 0,
                'avg_importance': 0,
                'max_importance': 0,
                'min_importance': 0,
                'total_connections': 0,
                'avg_connections': 0,
                'most_connected': None,
                'types': {}
            }
        
        importances = [n.importance for n in nodes]
        connection_counts = [len(n.connections) for n in nodes]
        
        from collections import Counter
        type_counts = Counter(n.type for n in nodes)
        
        # Find most connected node
        most_connected = max(nodes, key=lambda n: len(n.connections))
        
        return {
            'total_memories': len(nodes),
            'avg_importance': sum(importances) / len(importances),
            'max_importance': max(importances),
            'min_importance': min(importances),
            'total_connections': sum(connection_counts),
            'avg_connections': sum(connection_counts) / len(connection_counts),
            'most_connected': {
                'id': most_connected.id,
                'content': most_connected.content[:50],
                'connections': len(most_connected.connections)
            },
            'types': dict(type_counts)
        }
    
    def export_graph_json(self) -> str:
        """
        Export graph as JSON string.
        
        Returns:
            JSON string representation of the graph
        """
        export_data = {
            'metadata': {
                'export_timestamp': time.time(),
                'total_nodes': len(self.memory.graph.nodes),
                'session_id': self.memory.session_id
            },
            'nodes': [],
            'edges': []
        }
        
        for node_id, node in self.memory.graph.nodes.items():
            export_data['nodes'].append({
                'id': node_id,
                'type': node.type,
                'content': node.content,
                'importance': node.importance,
                'timestamp': node.timestamp,
                'access_count': node.access_count,
                'metadata': node.metadata
            })
            
            for conn in node.connections:
                if isinstance(conn, tuple):
                    target_id, weight = conn
                else:
                    target_id, weight = conn, 1.0
                
                export_data['edges'].append({
                    'from': node_id,
                    'to': target_id,
                    'weight': weight
                })
        
        return json.dumps(export_data, indent=2)
    
    def create_dashboard(self) -> Dict[str, go.Figure]:
        """
        Create all visualizations for a complete dashboard.
        
        Returns:
            Dictionary mapping visualization names to Plotly figures
        """
        return {
            'network': self.create_graph_network()[0],
            'importance': self.create_importance_distribution(),
            'timeline': self.create_memory_timeline(),
            'types': self.create_type_distribution(),
            'heatmap': self.create_access_heatmap()
        }


# Example usage and testing
if __name__ == "__main__":
    print("Memory Visualizer - Example Usage")
    print("=" * 60)
    
    # This would normally use an actual HybridMemory instance
    print("""
Example usage:

from ez_agent import EZAgent
from ui.visualize import MemoryVisualizer

# Create agent and add some memories
agent = EZAgent("test.db")
agent.remember("Python is a programming language", importance=0.9)
agent.remember("AI is transforming technology", importance=0.8)
agent.ask("What is machine learning?")

# Create visualizer
viz = MemoryVisualizer(agent.memory)

# Create network graph
fig, stats = viz.create_graph_network()
fig.show()  # Opens in browser

# Create importance distribution
fig = viz.create_importance_distribution()
fig.show()

# Create timeline
fig = viz.create_memory_timeline()
fig.show()

# Create type distribution
fig = viz.create_type_distribution()
fig.show()

# Get statistics
stats = viz.get_statistics_summary()
print(stats)

# Export as JSON
json_data = viz.export_graph_json()
with open("memory_graph.json", "w") as f:
    f.write(json_data)

# Create all visualizations at once
dashboard = viz.create_dashboard()
for name, fig in dashboard.items():
    print(f"Created {name} visualization")
    """)