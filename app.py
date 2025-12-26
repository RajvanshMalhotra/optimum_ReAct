# # """Streamlit UI for EZAgent with memory visualization."""
# # import streamlit as st
# # import asyncio
# # import os
# # from pathlib import Path
# # import pandas as pd
# # from datetime import datetime

# # # Page config
# # st.set_page_config(
# #     page_title="EZAgent Dashboard",
# #     page_icon="🤖",
# #     layout="wide",
# #     initial_sidebar_state="expanded"
# # )

# # # Custom CSS
# # st.markdown("""
# # <style>
# #     .main-header {
# #         font-size: 2.5rem;
# #         font-weight: bold;
# #         color: #1f77b4;
# #         text-align: center;
# #         margin-bottom: 2rem;
# #     }
# #     .stat-card {
# #         background-color: #f0f2f6;
# #         padding: 1rem;
# #         border-radius: 0.5rem;
# #         border-left: 4px solid #1f77b4;
# #     }
# #     .memory-card {
# #         background-color: white;
# #         padding: 1rem;
# #         border-radius: 0.5rem;
# #         border: 1px solid #e0e0e0;
# #         margin-bottom: 0.5rem;
# #     }
# # </style>
# # """, unsafe_allow_html=True)

# # # Initialize session state
# # if 'agent' not in st.session_state:
# #     st.session_state.agent = None
# # if 'chat_history' not in st.session_state:
# #     st.session_state.chat_history = []
# # if 'db_path' not in st.session_state:
# #     st.session_state.db_path = "agent_ui.db"

# # # Import after session state
# # try:
# #     from AgenT import EZAgent
# #     from ui.visualizer import MemoryVisualizer
# #     AGENT_AVAILABLE = True
# # except ImportError as e:
# #     AGENT_AVAILABLE = False
# #     st.error(f"Error importing agent: {e}")

# # # Sidebar
# # with st.sidebar:
# #     st.markdown("## 👾 Agent Control Panel")
    
# #     # Database selection
# #     st.markdown("### Database")
# #     db_name = st.text_input("Database name:", value=st.session_state.db_path)
    
# #     col1, col2 = st.columns(2)
# #     with col1:
# #         if st.button("Load Agent", type="primary"):
# #             if AGENT_AVAILABLE:
# #                 try:
# #                     st.session_state.agent = EZAgent(db_name)
# #                     st.session_state.db_path = db_name
# #                     st.success("Agent loaded!")
# #                 except Exception as e:
# #                     st.error(f"Error: {e}")
# #             else:
# #                 st.error("Agent not available")
    
# #     with col2:
# #         if st.button(" New Agent"):
# #             st.session_state.agent = None
# #             st.session_state.chat_history = []
# #             st.rerun()
    
# #     st.markdown("---")
    
# #     # Agent status
# #     if st.session_state.agent:
# #         st.success("✅ Agent Active")
        
# #         # Get stats
# #         try:
# #             stats = st.session_state.agent.stats()
# #             st.metric("Memories in RAM", stats['graph']['total_nodes'])
# #             st.metric("Total in DB", stats['store']['total_memories'])
# #             st.metric("Current Session", stats['session_memory_count'])
# #         except Exception as e:
# #             st.error(f"Stats error: {e}")
# #     else:
# #         st.warning(" No Agent Loaded")
    
# #     st.markdown("---")
    
# #     # Quick actions
# #     st.markdown("### Quick Actions")
# #     if st.button("View Dashboard"):
# #         st.session_state.page = "dashboard"
# #     if st.button("Chat"):
# #         st.session_state.page = "chat"
# #     if st.button("Memory Explorer"):
# #         st.session_state.page = "memory"
# #     if st.button("Visualizations"):
# #         st.session_state.page = "visualize"
    
# #     st.markdown("---")
    
# #     # Danger zone
# #     with st.expander("💀🤙 Danger Zone"):
# #         if st.button("🗑️ Clear Session"):
# #             if st.session_state.agent:
# #                 st.session_state.agent.clear_session()
# #                 st.success("Session cleared!")
        
# #         if st.button("Delete Database", type="secondary"):
# #             if st.session_state.agent:
# #                 db_path = st.session_state.agent.memory.store.db_path
# #                 st.session_state.agent = None
# #                 try:
# #                     os.remove(db_path)
# #                     st.success("Database deleted!")
# #                 except Exception as e:
# #                     st.error(f"Error: {e}")

# # # Initialize page
# # if 'page' not in st.session_state:
# #     st.session_state.page = "dashboard"

# # # Main content based on page
# # if st.session_state.page == "dashboard":
# #     st.markdown('<div class="main-header">👾Agent Dashboard</div>', unsafe_allow_html=True)
    
# #     if not st.session_state.agent:
# #         st.info("👈 Load an agent from the sidebar to get started!")
        
# #         st.markdown("## Quick Start")
# #         st.code("""
# # from ez_agent import EZAgent

# # # Create agent
# # agent = EZAgent("my_agent.db")

# # # Ask questions
# # result = agent.ask("What is AI?")
# # print(result)

# # # Store information
# # agent.remember("Important fact")

# # # Retrieve information
# # memories = agent.recall("Important")
# #         """, language="python")
        
# #     else:
# #         # Show stats
# #         try:
# #             stats = st.session_state.agent.stats()
            
# #             col1, col2, col3, col4 = st.columns(4)
            
# #             with col1:
# #                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
# #                 st.metric("Total Memories", stats['total_memories'])
# #                 st.markdown('</div>', unsafe_allow_html=True)
            
# #             with col2:
# #                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
# #                 st.metric("In RAM", stats['graph']['total_nodes'])
# #                 st.markdown('</div>', unsafe_allow_html=True)
            
# #             with col3:
# #                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
# #                 st.metric("In Database", stats['store']['total_memories'])
# #                 st.markdown('</div>', unsafe_allow_html=True)
            
# #             with col4:
# #                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
# #                 st.metric("Sessions", stats['store']['total_sessions'])
# #                 st.markdown('</div>', unsafe_allow_html=True)
            
# #             # Recent activity
# #             st.markdown("## 📝 Recent Activity")
# #             if st.session_state.chat_history:
# #                 for i, (query, response) in enumerate(reversed(st.session_state.chat_history[-5:])):
# #                     with st.expander(f"Query {len(st.session_state.chat_history) - i}: {query[:50]}..."):
# #                         st.markdown(f"**Query:** {query}")
# #                         st.markdown(f"**Response:** {response}")
# #             else:
# #                 st.info("No recent activity")
        
# #         except Exception as e:
# #             st.error(f"Error loading dashboard: {e}")

# # elif st.session_state.page == "chat":
# #     st.markdown('<div class="main-header">💬 Chat with Agent</div>', unsafe_allow_html=True)
    
# #     if not st.session_state.agent:
# #         st.warning("Please load an agent first!")
# #     else:
# #         # Chat interface
# #         st.markdown("### Conversation")
        
# #         # Display chat history
# #         for query, response in st.session_state.chat_history:
# #             st.markdown(f"**You:** {query}")
# #             st.markdown(f"**Agent:** {response}")
# #             st.markdown("---")
        
# #         # Input form
# #         with st.form("chat_form", clear_on_submit=True):
# #             user_input = st.text_area("Ask something:", height=100, key="chat_input")
# #             col1, col2 = st.columns([1, 4])
# #             with col1:
# #                 max_steps = st.number_input("Max steps:", 1, 20, 10)
# #             with col2:
# #                 submitted = st.form_submit_button("🚀 Send", type="primary", use_container_width=True)
            
# #             if submitted and user_input:
# #                 with st.spinner("Thinking..."):
# #                     try:
# #                         response = st.session_state.agent.ask(user_input, max_steps=max_steps)
# #                         st.session_state.chat_history.append((user_input, response))
# #                         st.rerun()
# #                     except Exception as e:
# #                         st.error(f"Error: {e}")

# # elif st.session_state.page == "memory":
# #     st.markdown('<div class="main-header">🧠 Memory Explorer</div>', unsafe_allow_html=True)
    
# #     if not st.session_state.agent:
# #         st.warning("Please load an agent first!")
# #     else:
# #         # Search memories
# #         col1, col2 = st.columns([3, 1])
# #         with col1:
# #             search_query = st.text_input("Search memories:", placeholder="Enter search term...")
# #         with col2:
# #             search_limit = st.number_input("Results:", 1, 50, 10)
        
# #         if st.button("🔍 Search") or search_query:
# #             try:
# #                 memories = st.session_state.agent.recall(search_query, limit=search_limit)
                
# #                 st.markdown(f"### Found {len(memories)} memories")
                
# #                 for i, memory in enumerate(memories, 1):
# #                     st.markdown(f'<div class="memory-card">', unsafe_allow_html=True)
# #                     st.markdown(f"**Memory {i}:**")
# #                     st.write(memory)
# #                     st.markdown('</div>', unsafe_allow_html=True)
            
# #             except Exception as e:
# #                 st.error(f"Search error: {e}")
        
# #         # Add memory
# #         st.markdown("---")
# #         st.markdown("### 📝 Add New Memory")
        
# #         with st.form("add_memory_form"):
# #             new_memory = st.text_area("Memory content:", height=100)
# #             importance = st.slider("Importance:", 0.0, 1.0, 0.8, 0.1)
            
# #             if st.form_submit_button("💾 Save"):
# #                 try:
# #                     st.session_state.agent.remember(new_memory, importance=importance)
# #                     st.success("Memory saved!")
# #                 except Exception as e:
# #                     st.error(f"Error: {e}")

# # elif st.session_state.page == "visualize":
# #     st.markdown('<div class="main-header">📈 Memory Visualizations</div>', unsafe_allow_html=True)
    
# #     if not st.session_state.agent:
# #         st.warning("Please load an agent first!")
# #     else:
# #         try:
# #             visualizer = MemoryVisualizer(st.session_state.agent.memory)
            
# #             # Tabs for different visualizations
# #             tab1, tab2, tab3, tab4 = st.tabs(["🕸️ Network Graph", "📊 Statistics", "📅 Timeline", "🗂️ Data"])
            
# #             with tab1:
# #                 st.markdown("### Memory Network Graph")
# #                 st.info("Node size represents importance. Colors represent memory types.")
                
# #                 try:
# #                     fig, stats = visualizer.create_graph_network()
# #                     st.plotly_chart(fig, use_container_width=True)
                    
# #                     col1, col2, col3 = st.columns(3)
# #                     with col1:
# #                         st.metric("Nodes", stats['total_nodes'])
# #                     with col2:
# #                         st.metric("Connections", stats['total_edges'])
# #                     with col3:
# #                         st.metric("Avg Connections", f"{stats['avg_connections']:.2f}")
                
# #                 except Exception as e:
# #                     st.error(f"Graph error: {e}")
            
# #             with tab2:
# #                 st.markdown("### Statistical Distributions")
                
# #                 col1, col2 = st.columns(2)
                
# #                 with col1:
# #                     try:
# #                         fig = visualizer.create_importance_distribution()
# #                         st.plotly_chart(fig, use_container_width=True)
# #                     except Exception as e:
# #                         st.error(f"Distribution error: {e}")
                
# #                 with col2:
# #                     try:
# #                         fig = visualizer.create_type_distribution()
# #                         st.plotly_chart(fig, use_container_width=True)
# #                     except Exception as e:
# #                         st.error(f"Pie chart error: {e}")
            
# #             with tab3:
# #                 st.markdown("### Memory Timeline")
# #                 try:
# #                     fig = visualizer.create_memory_timeline()
# #                     st.plotly_chart(fig, use_container_width=True)
# #                 except Exception as e:
# #                     st.error(f"Timeline error: {e}")
            
# #             with tab4:
# #                 st.markdown("### Memory Data Table")
# #                 try:
# #                     data = visualizer.get_memory_table_data()
# #                     if data:
# #                         df = pd.DataFrame(data)
# #                         st.dataframe(df, use_container_width=True, height=400)
                        
# #                         # Export options
# #                         col1, col2 = st.columns(2)
# #                         with col1:
# #                             csv = df.to_csv(index=False)
# #                             st.download_button(
# #                                 "📥 Download CSV",
# #                                 csv,
# #                                 "memories.csv",
# #                                 "text/csv"
# #                             )
# #                         with col2:
# #                             json_data = visualizer.export_graph_json()
# #                             st.download_button(
# #                                 "📥 Download JSON",
# #                                 json_data,
# #                                 "memory_graph.json",
# #                                 "application/json"
# #                             )
# #                     else:
# #                         st.info("No memories to display")
                
# #                 except Exception as e:
# #                     st.error(f"Data table error: {e}")
        
# #         except Exception as e:
# #             st.error(f"Visualization error: {e}")

# # # Footer
# # st.markdown("---")
# # st.markdown(
# #     '<div style="text-align: center; color: #888;">EZAgent Dashboard v1.0 | Built with Streamlit</div>',
# #     unsafe_allow_html=True
# # )

# """Streamlit UI for EZAgent with live chat and memory visualization."""
# import streamlit as st
# import asyncio
# import os
# import sys
# from pathlib import Path
# import pandas as pd
# from datetime import datetime
# from io import StringIO

# # Page config
# st.set_page_config(
#     page_title="EZAgent Dashboard",
#     page_icon="🤖",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS
# st.markdown("""
# <style>
#     .main-header {
#         font-size: 2.5rem;
#         font-weight: bold;
#         color: #1f77b4;
#         text-align: center;
#         margin-bottom: 2rem;
#     }
#     .stat-card {
#         background-color: #f0f2f6;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         border-left: 4px solid #1f77b4;
#     }
#     .chat-message {
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin-bottom: 1rem;
#     }
#     .user-message {
#         background-color: #e3f2fd;
#         border-left: 4px solid #2196f3;
#     }
#     .agent-message {
#         background-color: #f1f8e9;
#         border-left: 4px solid #8bc34a;
#     }
#     .thinking-step {
#         background-color: #fff3e0;
#         padding: 0.5rem;
#         border-radius: 0.3rem;
#         margin: 0.3rem 0;
#         font-size: 0.9rem;
#         border-left: 3px solid #ff9800;
#     }
#     .tool-execution {
#         background-color: #e8eaf6;
#         padding: 0.5rem;
#         border-radius: 0.3rem;
#         margin: 0.3rem 0;
#         font-size: 0.9rem;
#         border-left: 3px solid #3f51b5;
#     }
# </style>
# """, unsafe_allow_html=True)

# # Initialize session state
# if 'agent' not in st.session_state:
#     st.session_state.agent = None
# if 'chat_history' not in st.session_state:
#     st.session_state.chat_history = []
# if 'db_path' not in st.session_state:
#     st.session_state.db_path = "agent_ui.db"
# if 'thinking_steps' not in st.session_state:
#     st.session_state.thinking_steps = []
# if 'show_thinking' not in st.session_state:
#     st.session_state.show_thinking = False

# # Import after session state
# try:
#     from AgenT import EZAgent
#     from ui.visualizer import MemoryVisualizer
#     AGENT_AVAILABLE = True
# except ImportError as e:
#     AGENT_AVAILABLE = False
#     st.error(f"Error importing agent: {e}")

# # Capture agent output
# # class StreamCapture:
# #     """Capture print statements from agent."""
# #     def __init__(self, container):
# #         self.container = container
# #         self.content = []
        
# #     def write(self, text):
# #         if text.strip():
# #             self.content.append(text)
# #             # Parse thinking steps
# #             if "💭 Step" in text:
# #                 with self.container:
# #                     st.markdown(f'<div class="thinking-step">💭 {text.strip()}</div>', unsafe_allow_html=True)
# #             elif "🔧" in text:
# #                 with self.container:
# #                     st.markdown(f'<div class="tool-execution">🔧 {text.strip()}</div>', unsafe_allow_html=True)
    
# #     def flush(self):
# #         pass

# # Sidebar
# with st.sidebar:
#     st.markdown("## 🤖 EZAgent Control Panel")
    
#     # Database selection
#     st.markdown("### Database")
#     db_name = st.text_input("Database name:", value=st.session_state.db_path)
    
#     col1, col2 = st.columns(2)
#     with col1:
#         if st.button("🔄 Load Agent", type="primary"):
#             if AGENT_AVAILABLE:
#                 try:
#                     st.session_state.agent = EZAgent(db_name)
#                     st.session_state.db_path = db_name
#                     st.session_state.chat_history = []
#                     st.success("Agent loaded!")
#                     st.rerun()
#                 except Exception as e:
#                     st.error(f"Error: {e}")
#             else:
#                 st.error("Agent not available")
    
#     with col2:
#         if st.button("🆕 New Agent"):
#             st.session_state.agent = None
#             st.session_state.chat_history = []
#             st.session_state.thinking_steps = []
#             st.rerun()
    
#     st.markdown("---")
    
#     # Agent status
#     if st.session_state.agent:
#         st.success("✅ Agent Active")
        
#         # Get stats
#         try:
#             stats = st.session_state.agent.stats()
#             st.metric("Memories in RAM", stats['graph']['total_nodes'])
#             st.metric("Total in DB", stats['store']['total_memories'])
#             st.metric("Current Session", stats['session_memory_count'])
#         except Exception as e:
#             st.error(f"Stats error: {e}")
#     else:
#         st.warning("⚠️ No Agent Loaded")
    
#     st.markdown("---")
    
#     # Settings
#     # st.markdown("### ⚙️ Settings")
#     # st.session_state.show_thinking = st.checkbox("Show thinking process", value=True)
#     # max_steps = st.slider("Max reasoning steps", 1, 20, 10)
#     st.markdown("### ⚙️ Settings")
#     max_steps = st.slider("Max reasoning steps", 1, 20, 10)

    
#     st.markdown("---")
    
#     # Quick actions
#     st.markdown("### Navigation")
#     if st.button("📊 Dashboard", use_container_width=True):
#         st.session_state.page = "dashboard"
#         st.rerun()
#     if st.button("💬 Chat", use_container_width=True):
#         st.session_state.page = "chat"
#         st.rerun()
#     if st.button("🧠 Memory", use_container_width=True):
#         st.session_state.page = "memory"
#         st.rerun()
#     if st.button("📈 Visualizations", use_container_width=True):
#         st.session_state.page = "visualize"
#         st.rerun()
    
#     st.markdown("---")
    
#     # Danger zone
#     with st.expander("⚠️ Danger Zone"):
#         if st.button("🗑️ Clear Session"):
#             if st.session_state.agent:
#                 st.session_state.agent.clear_session()
#                 st.session_state.chat_history = []
#                 st.success("Session cleared!")
#                 st.rerun()
        
#         if st.button("💥 Delete Database", type="secondary"):
#             if st.session_state.agent:
#                 db_path = st.session_state.agent.memory.store.db_path
#                 st.session_state.agent = None
#                 try:
#                     os.remove(db_path)
#                     st.success("Database deleted!")
#                     st.rerun()
#                 except Exception as e:
#                     st.error(f"Error: {e}")

# # Initialize page
# if 'page' not in st.session_state:
#     st.session_state.page = "chat"

# # Main content based on page
# if st.session_state.page == "dashboard":
#     st.markdown('<div class="main-header">🤖 EZAgent Dashboard</div>', unsafe_allow_html=True)
    
#     if not st.session_state.agent:
#         st.info("👈 Load an agent from the sidebar to get started!")
        
#         st.markdown("## Quick Start")
#         st.code("""
# from ez_agent import EZAgent

# # Create agent
# agent = EZAgent("my_agent.db")

# # Ask questions
# result = agent.ask("What is AI?")
# print(result)

# # Store information
# agent.remember("Important fact")

# # Retrieve information
# memories = agent.recall("Important")
#         """, language="python")
        
#     else:
#         # Show stats
#         try:
#             stats = st.session_state.agent.stats()
            
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
#                 st.metric("Total Memories", stats['total_memories'])
#                 st.markdown('</div>', unsafe_allow_html=True)
            
#             with col2:
#                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
#                 st.metric("In RAM", stats['graph']['total_nodes'])
#                 st.markdown('</div>', unsafe_allow_html=True)
            
#             with col3:
#                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
#                 st.metric("In Database", stats['store']['total_memories'])
#                 st.markdown('</div>', unsafe_allow_html=True)
            
#             with col4:
#                 st.markdown('<div class="stat-card">', unsafe_allow_html=True)
#                 st.metric("Sessions", stats['store']['total_sessions'])
#                 st.markdown('</div>', unsafe_allow_html=True)
            
#             # Recent activity
#             st.markdown("## 📝 Recent Activity")
#             if st.session_state.chat_history:
#                 for i, chat_item in enumerate(reversed(st.session_state.chat_history[-5:])):
#                     query = chat_item.get('query', '')
#                     response = chat_item.get('response', '')
#                     with st.expander(f"Query {len(st.session_state.chat_history) - i}: {query[:50]}..."):
#                         st.markdown(f"**Query:** {query}")
#                         st.markdown(f"**Response:** {response}")
#             else:
#                 st.info("No recent activity")
        
#         except Exception as e:
#             st.error(f"Error loading dashboard: {e}")

# elif st.session_state.page == "chat":
#     st.markdown('<div class="main-header">💬 Chat with Agent</div>', unsafe_allow_html=True)
    
#     if not st.session_state.agent:
#         st.warning("👈 Please load an agent from the sidebar first!")
#         st.info("Click 'Load Agent' in the sidebar to get started")
#     else:
#         # Chat container
#         chat_container = st.container()
        
#         # Display chat history
#         with chat_container:
#             for chat_item in st.session_state.chat_history:
#                 # User message
#                 st.markdown(f'<div class="chat-message user-message">', unsafe_allow_html=True)
#                 st.markdown(f"**You:** {chat_item['query']}")
#                 st.markdown('</div>', unsafe_allow_html=True)
                
#                 # # Thinking steps (if enabled and available)
#                 # if st.session_state.show_thinking and 'thinking' in chat_item:
#                 #     with st.expander("🧠 Thinking Process", expanded=False):
#                 #         for step in chat_item['thinking']:
#                 #             st.markdown(step, unsafe_allow_html=True)
                
#                 # Agent response
#                 st.markdown(f'<div class="chat-message agent-message">', unsafe_allow_html=True)
#                 st.markdown(f"**Agent:** {chat_item['response']}")
#                 st.markdown('</div>', unsafe_allow_html=True)
        
#         # Input area (always at bottom)
#         st.markdown("---")
        
#         col1, col2 = st.columns([5, 1])
        
#         with col1:
#             user_input = st.text_input(
#                 "Message:",
#                 key="chat_input",
#                 placeholder="Ask me anything...",
#                 label_visibility="collapsed"
#             )
        
#         with col2:
#             send_button = st.button("🚀 Send", type="primary", use_container_width=True)
        
#         # Process message
#         if send_button and user_input:
#             # Create a container for thinking process
#             thinking_container = st.container()
            
#             with st.spinner("🤔 Thinking..."):
#                 try:
#                     # Capture stdout

                    
#                     # Get response
#                     response = st.session_state.agent.ask(user_input, max_steps=max_steps)
                    
#                     # Restore stdout

                    
#                     # Save to history
#                     chat_item = {
#                         'query': user_input,
#                         'response': response,
#                         'thinking': thinking_steps if st.session_state.show_thinking else [],
#                         'timestamp': datetime.now().isoformat()
#                     }
#                     st.session_state.chat_history.append(chat_item)
                    
#                     # Rerun to show new message
#                     st.rerun()
                    
#                 except Exception as e:
#                     st.error(f"Error: {e}")
#                     import traceback
#                     st.code(traceback.format_exc())
#                 finally:
#                     sys.stdout = old_stdout
        
#         # Clear chat button
#         if st.session_state.chat_history:
#             st.markdown("---")
#             if st.button("🗑️ Clear Chat History"):
#                 st.session_state.chat_history = []
#                 st.rerun()

# elif st.session_state.page == "memory":
#     st.markdown('<div class="main-header">🧠 Memory Explorer</div>', unsafe_allow_html=True)
    
#     if not st.session_state.agent:
#         st.warning("Please load an agent first!")
#     else:
#         # Search memories
#         col1, col2 = st.columns([3, 1])
#         with col1:
#             search_query = st.text_input("Search memories:", placeholder="Enter search term...")
#         with col2:
#             search_limit = st.number_input("Results:", 1, 50, 10)
        
#         if st.button("🔍 Search") or search_query:
#             try:
#                 memories = st.session_state.agent.recall(search_query, limit=search_limit)
                
#                 st.markdown(f"### Found {len(memories)} memories")
                
#                 if memories:
#                     for i, memory in enumerate(memories, 1):
#                         with st.expander(f"Memory {i}: {memory[:50]}..."):
#                             st.write(memory)
#                 else:
#                     st.info("No memories found")
            
#             except Exception as e:
#                 st.error(f"Search error: {e}")
        
#         # Add memory
#         st.markdown("---")
#         st.markdown("### 📝 Add New Memory")
        
#         new_memory = st.text_area("Memory content:", height=100, placeholder="Enter information to remember...")
#         importance = st.slider("Importance:", 0.0, 1.0, 0.8, 0.1)
        
#         if st.button("💾 Save Memory", type="primary"):
#             if new_memory:
#                 try:
#                     st.session_state.agent.remember(new_memory, importance=importance)
#                     st.success("Memory saved!")
#                     st.balloons()
#                 except Exception as e:
#                     st.error(f"Error: {e}")
#             else:
#                 st.warning("Please enter some content first")

# elif st.session_state.page == "visualize":
#     st.markdown('<div class="main-header">📈 Memory Visualizations</div>', unsafe_allow_html=True)
    
#     if not st.session_state.agent:
#         st.warning("Please load an agent first!")
#     else:
#         try:
#             visualizer = MemoryVisualizer(st.session_state.agent.memory)
            
#             # Tabs for different visualizations
#             tab1, tab2, tab3, tab4 = st.tabs(["🕸️ Network Graph", "📊 Statistics", "📅 Timeline", "🗂️ Data"])
            
#             with tab1:
#                 st.markdown("### Memory Network Graph")
#                 st.info("Node size = importance • Colors = memory types • Click and drag to explore")
                
#                 try:
#                     fig, stats = visualizer.create_graph_network()
#                     st.plotly_chart(fig, use_container_width=True)
                    
#                     col1, col2, col3 = st.columns(3)
#                     with col1:
#                         st.metric("Nodes", stats['total_nodes'])
#                     with col2:
#                         st.metric("Connections", stats['total_edges'])
#                     with col3:
#                         st.metric("Avg Connections", f"{stats['avg_connections']:.2f}")
                
#                 except Exception as e:
#                     st.error(f"Graph error: {e}")
            
#             with tab2:
#                 st.markdown("### Statistical Distributions")
                
#                 col1, col2 = st.columns(2)
                
#                 with col1:
#                     try:
#                         fig = visualizer.create_importance_distribution()
#                         st.plotly_chart(fig, use_container_width=True)
#                     except Exception as e:
#                         st.error(f"Distribution error: {e}")
                
#                 with col2:
#                     try:
#                         fig = visualizer.create_type_distribution()
#                         st.plotly_chart(fig, use_container_width=True)
#                     except Exception as e:
#                         st.error(f"Pie chart error: {e}")
            
#             with tab3:
#                 st.markdown("### Memory Timeline")
#                 try:
#                     fig = visualizer.create_memory_timeline()
#                     st.plotly_chart(fig, use_container_width=True)
#                 except Exception as e:
#                     st.error(f"Timeline error: {e}")
            
#             with tab4:
#                 st.markdown("### Memory Data Table")
#                 try:
#                     data = visualizer.get_memory_table_data()
#                     if data:
#                         df = pd.DataFrame(data)
#                         st.dataframe(df, use_container_width=True, height=400)
                        
#                         # Export options
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             csv = df.to_csv(index=False)
#                             st.download_button(
#                                 "📥 Download CSV",
#                                 csv,
#                                 "memories.csv",
#                                 "text/csv"
#                             )
#                         with col2:
#                             json_data = visualizer.export_graph_json()
#                             st.download_button(
#                                 "📥 Download JSON",
#                                 json_data,
#                                 "memory_graph.json",
#                                 "application/json"
#                             )
#                     else:
#                         st.info("No memories to display")
                
#                 except Exception as e:
#                     st.error(f"Data table error: {e}")
        
#         except Exception as e:
#             st.error(f"Visualization error: {e}")

# # Footer
# st.markdown("---")
# st.markdown(
#     '<div style="text-align: center; color: #888;">EZAgent Dashboard v1.0 | Built with Streamlit</div>',
#     unsafe_allow_html=True
# )
"""Streamlit UI for EZAgent with live chat and memory visualization."""
import streamlit as st
import asyncio
import os
from pathlib import Path
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="EZAgent Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .agent-message {
        background-color: #f1f8e9;
        border-left: 4px solid #8bc34a;
    }
    .thinking-step {
        background-color: #fff3e0;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.3rem 0;
        font-size: 0.9rem;
        border-left: 3px solid #ff9800;
    }
    .tool-execution {
        background-color: #e8eaf6;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.3rem 0;
        font-size: 0.9rem;
        border-left: 3px solid #3f51b5;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
for key, value in {
    'agent': None,
    'chat_history': [],
    'db_path': "agent_ui.db",
    'thinking_steps': [],
    'show_thinking': False
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Import agent after session state
try:
    from AgenT import EZAgent
    from ui.visualizer import MemoryVisualizer
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    st.error(f"Error importing agent: {e}")

# Sidebar
with st.sidebar:
    st.markdown("## 🤖 EZAgent Control Panel")
    
    db_name = st.text_input("Database name:", value=st.session_state.db_path)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Load Agent", type="primary"):
            if AGENT_AVAILABLE:
                try:
                    st.session_state.agent = EZAgent(db_name)
                    st.session_state.db_path = db_name
                    st.session_state.chat_history = []
                    st.success("Agent loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Agent not available")
    
    with col2:
        if st.button("🆕 New Agent"):
            st.session_state.agent = None
            st.session_state.chat_history = []
            st.session_state.thinking_steps = []
            st.rerun()
    
    st.markdown("---")
    
    if st.session_state.agent:
        st.success("✅ Agent Active")
        try:
            stats = st.session_state.agent.stats()
            st.metric("Memories in RAM", stats['graph']['total_nodes'])
            st.metric("Total in DB", stats['store']['total_memories'])
            st.metric("Current Session", stats['session_memory_count'])
        except Exception as e:
            st.error(f"Stats error: {e}")
    else:
        st.warning("⚠️ No Agent Loaded")
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    max_steps = st.slider("Max reasoning steps", 1, 20, 10)
    
    st.markdown("---")
    st.markdown("### Navigation")
    for name, page in [("📊 Dashboard", "dashboard"), ("💬 Chat", "chat"), ("🧠 Memory", "memory"), ("📈 Visualizations", "visualize")]:
        if st.button(name, use_container_width=True):
            st.session_state.page = page
            st.rerun()
    
    st.markdown("---")
    with st.expander("⚠️ Danger Zone"):
        if st.button("🗑️ Clear Session"):
            if st.session_state.agent:
                st.session_state.agent.clear_session()
                st.session_state.chat_history = []
                st.success("Session cleared!")
                st.rerun()
        if st.button("💥 Delete Database", type="secondary"):
            if st.session_state.agent:
                db_path = st.session_state.agent.memory.store.db_path
                st.session_state.agent = None
                try:
                    os.remove(db_path)
                    st.success("Database deleted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# Initialize page
if 'page' not in st.session_state:
    st.session_state.page = "chat"

# Main content
if st.session_state.page == "dashboard":
    st.markdown('<div class="main-header">🤖 EZAgent Dashboard</div>', unsafe_allow_html=True)
    if not st.session_state.agent:
        st.info("👈 Load an agent from the sidebar to get started!")
        st.markdown("## Quick Start")
        st.code("""
from ez_agent import EZAgent

agent = EZAgent("my_agent.db")
result = agent.ask("What is AI?")
agent.remember("Important fact")
memories = agent.recall("Important")
        """, language="python")
    else:
        try:
            stats = st.session_state.agent.stats()
            cols = st.columns(4)
            metrics = [
                ("Total Memories", stats['total_memories']),
                ("In RAM", stats['graph']['total_nodes']),
                ("In Database", stats['store']['total_memories']),
                ("Sessions", stats['store']['total_sessions'])
            ]
            for col, (name, val) in zip(cols, metrics):
                with col:
                    st.markdown('<div class="stat-card">', unsafe_allow_html=True)
                    st.metric(name, val)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("## 📝 Recent Activity")
            if st.session_state.chat_history:
                for i, chat_item in enumerate(reversed(st.session_state.chat_history[-5:])):
                    query = chat_item.get('query', '')
                    response = chat_item.get('response', '')
                    with st.expander(f"Query {len(st.session_state.chat_history) - i}: {query[:50]}..."):
                        st.markdown(f"**Query:** {query}")
                        st.markdown(f"**Response:** {response}")
            else:
                st.info("No recent activity")
        except Exception as e:
            st.error(f"Error loading dashboard: {e}")

elif st.session_state.page == "chat":
    st.markdown('<div class="main-header">💬 Chat with Agent</div>', unsafe_allow_html=True)
    
    if not st.session_state.agent:
        st.warning("👈 Please load an agent from the sidebar first!")
        st.info("Click 'Load Agent' in the sidebar to get started")
    else:
        chat_container = st.container()
        for chat_item in st.session_state.chat_history:
            st.markdown(f'<div class="chat-message user-message">', unsafe_allow_html=True)
            st.markdown(f"**You:** {chat_item['query']}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="chat-message agent-message">', unsafe_allow_html=True)
            st.markdown(f"**Agent:** {chat_item['response']}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        col1, col2 = st.columns([5,1])
        with col1:
            user_input = st.text_input(
                "Message:",
                key="chat_input",
                placeholder="Ask me anything...",
                label_visibility="collapsed"
            )
        with col2:
            send_button = st.button("🚀 Send", type="primary", use_container_width=True)
        
        if send_button and user_input:
            with st.spinner("🤔 Thinking..."):
                try:
                    response = st.session_state.agent.ask(user_input, max_steps=max_steps)
                    chat_item = {
                        'query': user_input,
                        'response': response,
                        'thinking': [],  # optionally add thinking steps if available
                        'timestamp': datetime.now().isoformat()
                    }
                    st.session_state.chat_history.append(chat_item)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        if st.session_state.chat_history:
            st.markdown("---")
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()

# Memory and Visualize pages remain unchanged (same as your original code)
# ...

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #888;">EZAgent Dashboard v1.0 | Built with Streamlit</div>',
    unsafe_allow_html=True
)


