import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import random
import time
from datetime import datetime, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="Battery Management System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .status-good { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-critical { color: #dc3545; }
    
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'cells_data' not in st.session_state:
    st.session_state.cells_data = {}
if 'tasks_data' not in st.session_state:
    st.session_state.tasks_data = {}
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = []

class BatteryCell:
    def __init__(self, cell_id, cell_type, capacity=50):
        self.cell_id = cell_id
        self.cell_type = cell_type.lower()
        self.capacity = capacity
        self.current_capacity = capacity
        
        # Set voltage parameters based on cell type
        if self.cell_type == "lfp":
            self.nominal_voltage = 3.2
            self.min_voltage = 2.8
            self.max_voltage = 3.6
        else:  # li-ion or other
            self.nominal_voltage = 3.6
            self.min_voltage = 3.2
            self.max_voltage = 4.0
            
        self.current_voltage = self.nominal_voltage
        self.current = 0.0
        self.temperature = round(random.uniform(25, 40), 1)
        self.soc = 100.0  # State of charge
        self.health = 100.0  # Battery health
        self.cycle_count = 0
        self.last_updated = datetime.now()
    
    def update_parameters(self, current=None, voltage=None):
        if current is not None:
            self.current = current
        if voltage is not None:
            self.current_voltage = max(self.min_voltage, min(self.max_voltage, voltage))
        
        # Update SOC based on current (simplified model)
        if self.current > 0:  # Charging
            self.soc = min(100, self.soc + abs(self.current) * 0.1)
        elif self.current < 0:  # Discharging
            self.soc = max(0, self.soc - abs(self.current) * 0.1)
        
        # Update temperature (simplified thermal model)
        base_temp = 25 + abs(self.current) * 2
        self.temperature = round(base_temp + random.uniform(-2, 2), 1)
        
        # Update health based on usage
        if abs(self.current) > self.capacity * 0.5:  # High current usage
            self.health -= 0.001
        
        self.last_updated = datetime.now()
    
    def get_status(self):
        if self.soc > 80 and self.temperature < 45 and self.health > 90:
            return "Good"
        elif self.soc > 20 and self.temperature < 60 and self.health > 70:
            return "Warning"
        else:
            return "Critical"

def create_header():
    st.markdown("""
    <div class="main-header">
        <h1>🔋 Advanced Battery Management System</h1>
        <p>Real-time monitoring, configuration, and performance analysis</p>
    </div>
    """, unsafe_allow_html=True)

def sidebar_navigation():
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Dashboard", "Battery Configuration", "Task Management", "Performance Analysis", "Settings"]
    )
    return page

def battery_configuration_page():
    st.header("🔧 Battery Configuration")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Add New Battery Cell")
        
        with st.form("add_cell_form"):
            cell_type = st.selectbox("Cell Type", ["LFP", "Li-ion", "NMC", "LTO"])
            capacity = st.number_input("Capacity (Ah)", min_value=1.0, max_value=200.0, value=50.0)
            cell_count = st.number_input("Number of Cells", min_value=1, max_value=20, value=1)
            
            submitted = st.form_submit_button("Add Cell(s)")
            
            if submitted:
                for i in range(cell_count):
                    cell_id = f"cell_{len(st.session_state.cells_data) + 1}_{cell_type.lower()}"
                    st.session_state.cells_data[cell_id] = BatteryCell(cell_id, cell_type, capacity)
                
                st.success(f"Added {cell_count} {cell_type} cell(s) successfully!")
                st.rerun()
    
    with col2:
        st.subheader("Current Battery Configuration")
        
        if st.session_state.cells_data:
            # Create configuration table
            config_data = []
            for cell_id, cell in st.session_state.cells_data.items():
                config_data.append({
                    "Cell ID": cell_id,
                    "Type": cell.cell_type.upper(),
                    "Capacity (Ah)": cell.capacity,
                    "Voltage Range": f"{cell.min_voltage}V - {cell.max_voltage}V",
                    "Current SOC (%)": f"{cell.soc:.1f}",
                    "Health (%)": f"{cell.health:.1f}",
                    "Status": cell.get_status()
                })
            
            df = pd.DataFrame(config_data)
            st.dataframe(df, use_container_width=True)
            
            # Remove cells option
            st.subheader("Remove Cells")
            if st.button("Clear All Cells", type="secondary"):
                st.session_state.cells_data = {}
                st.success("All cells removed!")
                st.rerun()
        else:
            st.info("No battery cells configured. Add some cells to get started!")

def task_management_page():
    st.header("⚡ Task Management")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Create New Task")
        
        if not st.session_state.cells_data:
            st.warning("Please configure battery cells first!")
            return
        
        with st.form("task_form"):
            task_type = st.selectbox("Task Type", ["CC_CV", "CC_CD", "IDLE", "PULSE"])
            
            # Common parameters
            duration = st.number_input("Duration (seconds)", min_value=1, value=3600)
            
            # Task-specific parameters
            if task_type == "CC_CV":
                st.write("**Constant Current - Constant Voltage**")
                cc_current = st.number_input("CC Current (A)", value=5.0)
                cv_voltage = st.number_input("CV Voltage (V)", value=4.0)
                cutoff_current = st.number_input("Cutoff Current (A)", value=0.1)
                
            elif task_type == "CC_CD":
                st.write("**Constant Current - Constant Discharge**")
                cc_current = st.number_input("CC Current (A)", value=-5.0)
                cutoff_voltage = st.number_input("Cutoff Voltage (V)", value=3.0)
                
            elif task_type == "IDLE":
                st.write("**Idle/Rest Period**")
                cc_current = 0.0
                cv_voltage = 0.0
                cutoff_current = 0.0
                cutoff_voltage = 0.0
                
            elif task_type == "PULSE":
                st.write("**Pulse Test**")
                pulse_current = st.number_input("Pulse Current (A)", value=10.0)
                pulse_duration = st.number_input("Pulse Duration (s)", value=10)
                rest_duration = st.number_input("Rest Duration (s)", value=30)
            
            submitted = st.form_submit_button("Add Task")
            
            if submitted:
                task_id = f"task_{len(st.session_state.tasks_data) + 1}"
                task_data = {
                    "task_id": task_id,
                    "task_type": task_type,
                    "duration": duration,
                    "created_at": datetime.now(),
                    "status": "Pending"
                }
                
                if task_type == "CC_CV":
                    task_data.update({
                        "cc_current": cc_current,
                        "cv_voltage": cv_voltage,
                        "cutoff_current": cutoff_current
                    })
                elif task_type == "CC_CD":
                    task_data.update({
                        "cc_current": cc_current,
                        "cutoff_voltage": cutoff_voltage
                    })
                elif task_type == "PULSE":
                    task_data.update({
                        "pulse_current": pulse_current,
                        "pulse_duration": pulse_duration,
                        "rest_duration": rest_duration
                    })
                
                st.session_state.tasks_data[task_id] = task_data
                st.success("Task added successfully!")
                st.rerun()
    
    with col2:
        st.subheader("Task Queue")
        
        if st.session_state.tasks_data:
            # Display tasks
            for task_id, task in st.session_state.tasks_data.items():
                with st.expander(f"{task_id} - {task['task_type']} ({task['status']})"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Duration:** {task['duration']}s")
                        st.write(f"**Created:** {task['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                    with col_b:
                        if st.button(f"Remove {task_id}", key=f"remove_{task_id}"):
                            del st.session_state.tasks_data[task_id]
                            st.rerun()
            
            # Task execution controls
            st.subheader("Task Execution")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("▶️ Start Tasks", type="primary"):
                    st.session_state.simulation_running = True
                    st.success("Task execution started!")
            with col_b:
                if st.button("⏹️ Stop Tasks", type="secondary"):
                    st.session_state.simulation_running = False
                    st.success("Task execution stopped!")
        else:
            st.info("No tasks configured.")

def dashboard_page():
    st.header("📊 Battery Dashboard")
    
    if not st.session_state.cells_data:
        st.warning("Please configure battery cells first!")
        return
    
    # Real-time updates
    if st.session_state.simulation_running:
        # Simulate battery parameter changes
        for cell_id, cell in st.session_state.cells_data.items():
            # Simulate current based on active tasks
            if st.session_state.tasks_data:
                # Simple simulation - apply first active task
                active_tasks = [t for t in st.session_state.tasks_data.values() if t['status'] == 'Pending']
                if active_tasks:
                    task = active_tasks[0]
                    if task['task_type'] == 'CC_CV':
                        cell.update_parameters(current=task.get('cc_current', 0))
                    elif task['task_type'] == 'CC_CD':
                        cell.update_parameters(current=task.get('cc_current', 0))
                    else:
                        cell.update_parameters(current=0)
            
            # Store historical data
            st.session_state.historical_data.append({
                'timestamp': datetime.now(),
                'cell_id': cell_id,
                'voltage': cell.current_voltage,
                'current': cell.current,
                'soc': cell.soc,
                'temperature': cell.temperature,
                'health': cell.health
            })
    
    # Key metrics
    st.subheader("System Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_cells = len(st.session_state.cells_data)
    avg_soc = np.mean([cell.soc for cell in st.session_state.cells_data.values()]) if total_cells > 0 else 0
    avg_temp = np.mean([cell.temperature for cell in st.session_state.cells_data.values()]) if total_cells > 0 else 0
    healthy_cells = sum(1 for cell in st.session_state.cells_data.values() if cell.get_status() == "Good")
    
    with col1:
        st.metric("Total Cells", total_cells)
    with col2:
        st.metric("Average SOC", f"{avg_soc:.1f}%")
    with col3:
        st.metric("Average Temperature", f"{avg_temp:.1f}°C")
    with col4:
        st.metric("Healthy Cells", f"{healthy_cells}/{total_cells}")
    
    # Real-time cell status
    st.subheader("Cell Status")
    
    cols = st.columns(min(4, len(st.session_state.cells_data)))
    for i, (cell_id, cell) in enumerate(st.session_state.cells_data.items()):
        with cols[i % 4]:
            status = cell.get_status()
            status_color = {"Good": "🟢", "Warning": "🟡", "Critical": "🔴"}[status]
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>{status_color} {cell_id}</h4>
                <p><strong>SOC:</strong> {cell.soc:.1f}%</p>
                <p><strong>Voltage:</strong> {cell.current_voltage:.2f}V</p>
                <p><strong>Current:</strong> {cell.current:.2f}A</p>
                <p><strong>Temp:</strong> {cell.temperature:.1f}°C</p>
                <p><strong>Health:</strong> {cell.health:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Real-time charts
    if st.session_state.historical_data:
        st.subheader("Real-time Monitoring")
        
        # Convert historical data to DataFrame
        df_hist = pd.DataFrame(st.session_state.historical_data)
        
        # Keep only recent data (last 100 points per cell)
        if len(df_hist) > 100 * len(st.session_state.cells_data):
            df_hist = df_hist.tail(100 * len(st.session_state.cells_data))
            st.session_state.historical_data = df_hist.to_dict('records')
        
        # Create subplots for different parameters
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Voltage', 'Current', 'SOC', 'Temperature'),
            vertical_spacing=0.1
        )
        
        colors = px.colors.qualitative.Set1
        
        for i, cell_id in enumerate(st.session_state.cells_data.keys()):
            cell_data = df_hist[df_hist['cell_id'] == cell_id]
            color = colors[i % len(colors)]
            
            # Voltage
            fig.add_trace(go.Scatter(
                x=cell_data['timestamp'], y=cell_data['voltage'],
                name=f'{cell_id} Voltage', line=dict(color=color)
            ), row=1, col=1)
            
            # Current  
            fig.add_trace(go.Scatter(
                x=cell_data['timestamp'], y=cell_data['current'],
                name=f'{cell_id} Current', line=dict(color=color),
                showlegend=False
            ), row=1, col=2)
            
            # SOC
            fig.add_trace(go.Scatter(
                x=cell_data['timestamp'], y=cell_data['soc'],
                name=f'{cell_id} SOC', line=dict(color=color),
                showlegend=False
            ), row=2, col=1)
            
            # Temperature
            fig.add_trace(go.Scatter(
                x=cell_data['timestamp'], y=cell_data['temperature'],
                name=f'{cell_id} Temp', line=dict(color=color),
                showlegend=False
            ), row=2, col=2)
        
        fig.update_layout(height=600, showlegend=True)
        fig.update_xaxes(title_text="Time")
        fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
        fig.update_yaxes(title_text="Current (A)", row=1, col=2)
        fig.update_yaxes(title_text="SOC (%)", row=2, col=1)
        fig.update_yaxes(title_text="Temperature (°C)", row=2, col=2)
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Auto-refresh when simulation is running
    if st.session_state.simulation_running:
        time.sleep(1)
        st.rerun()

def performance_analysis_page():
    st.header("📈 Performance Analysis")
    
    if not st.session_state.historical_data:
        st.info("No historical data available. Run some tasks to collect data.")
        return
    
    df = pd.DataFrame(st.session_state.historical_data)
    
    # Analysis options
    analysis_type = st.selectbox(
        "Select Analysis Type",
        ["Battery Efficiency", "Capacity Fade", "Temperature Analysis", "Cycle Life", "Energy Throughput"]
    )
    
    if analysis_type == "Battery Efficiency":
        st.subheader("Battery Efficiency Analysis")
        
        # Calculate efficiency metrics
        efficiency_data = []
        for cell_id in df['cell_id'].unique():
            cell_data = df[df['cell_id'] == cell_id].copy()
            
            # Calculate energy in/out
            cell_data['power'] = cell_data['voltage'] * cell_data['current']
            energy_in = cell_data[cell_data['power'] > 0]['power'].sum() / 3600  # Wh
            energy_out = abs(cell_data[cell_data['power'] < 0]['power'].sum()) / 3600  # Wh
            
            efficiency = (energy_out / energy_in * 100) if energy_in > 0 else 0
            
            efficiency_data.append({
                'Cell ID': cell_id,
                'Energy In (Wh)': round(energy_in, 2),
                'Energy Out (Wh)': round(energy_out, 2),
                'Efficiency (%)': round(efficiency, 2)
            })
        
        st.dataframe(pd.DataFrame(efficiency_data))
        
        # Efficiency chart
        fig = px.bar(
            pd.DataFrame(efficiency_data),
            x='Cell ID', y='Efficiency (%)',
            title='Battery Efficiency by Cell'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif analysis_type == "Temperature Analysis":
        st.subheader("Temperature Analysis")
        
        # Temperature distribution
        fig = px.histogram(
            df, x='temperature', color='cell_id',
            title='Temperature Distribution',
            nbins=20
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Temperature vs SOC correlation
        fig = px.scatter(
            df, x='temperature', y='soc', color='cell_id',
            title='Temperature vs SOC Correlation'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif analysis_type == "Capacity Fade":
        st.subheader("Capacity Fade Analysis")
        
        # Calculate capacity fade over time
        fade_data = []
        for cell_id in df['cell_id'].unique():
            cell_data = df[df['cell_id'] == cell_id].sort_values('timestamp')
            initial_health = cell_data['health'].iloc[0]
            current_health = cell_data['health'].iloc[-1]
            fade_rate = initial_health - current_health
            
            fade_data.append({
                'Cell ID': cell_id,
                'Initial Health (%)': round(initial_health, 2),
                'Current Health (%)': round(current_health, 2),
                'Fade Rate (%)': round(fade_rate, 2)
            })
        
        st.dataframe(pd.DataFrame(fade_data))
        
        # Health over time
        fig = px.line(
            df, x='timestamp', y='health', color='cell_id',
            title='Battery Health Over Time'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Export data option
    st.subheader("Data Export")
    if st.button("Download Historical Data"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"battery_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def settings_page():
    st.header("⚙️ Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Settings")
        
        # Simulation settings
        st.write("**Simulation Parameters**")
        update_interval = st.slider("Update Interval (seconds)", 1, 10, 2)
        data_retention = st.slider("Data Retention (hours)", 1, 24, 6)
        
        # Alert settings
        st.write("**Alert Thresholds**")
        temp_threshold = st.slider("Temperature Alert (°C)", 40, 80, 60)
        soc_low_threshold = st.slider("Low SOC Alert (%)", 5, 30, 20)
        voltage_low_threshold = st.slider("Low Voltage Alert (V)", 2.5, 3.5, 3.0)
        
    with col2:
        st.subheader("Data Management")
        
        # System statistics
        st.write("**System Statistics**")
        st.write(f"Total Cells: {len(st.session_state.cells_data)}")
        st.write(f"Total Tasks: {len(st.session_state.tasks_data)}")
        st.write(f"Historical Records: {len(st.session_state.historical_data)}")
        
        # Data management
        st.write("**Data Management**")
        if st.button("Clear Historical Data", type="secondary"):
            st.session_state.historical_data = []
            st.success("Historical data cleared!")
        
        if st.button("Reset All Data", type="secondary"):
            st.session_state.cells_data = {}
            st.session_state.tasks_data = {}
            st.session_state.historical_data = []
            st.session_state.simulation_running = False
            st.success("All data reset!")
            st.rerun()

def main():
    create_header()
    
    # Sidebar navigation
    page = sidebar_navigation()
    
    # Display selected page
    if page == "Dashboard":
        dashboard_page()
    elif page == "Battery Configuration":
        battery_configuration_page()
    elif page == "Task Management":
        task_management_page()
    elif page == "Performance Analysis":
        performance_analysis_page()
    elif page == "Settings":
        settings_page()

if __name__ == "__main__":
    main()