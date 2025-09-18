# pages/1_Dashboard.py

import streamlit as st
import re
import json
from utils.ai import generate_plan_with_groq
from utils.db import save_plan_to_firestore, get_user_plans, delete_plan_from_firestore, get_dashboard_summary
from utils.auth import logout_user

st.set_page_config(page_title="Dashboard - AI Learning Coach", page_icon="🎓", layout="wide")

def display_structured_plan(plan_data, plan_id):
    """Display a structured AI-generated plan"""
    
    # Plan overview
    if plan_data.get('overview'):
        st.markdown("### 📋 Overview")
        st.write(plan_data['overview'])
    
    # Plan details
    col1, col2, col3 = st.columns(3)
    with col1:
        if plan_data.get('duration'):
            st.metric("⏱️ Duration", plan_data['duration'])
    with col2:
        if plan_data.get('difficulty'):
            st.metric("📊 Level", plan_data['difficulty'])
    with col3:
        module_count = len(plan_data.get('modules', []))
        st.metric("📚 Modules", module_count)
    
    # Learning modules
    if plan_data.get('modules'):
        st.markdown("### 📚 Learning Modules")
        completed_modules = st.session_state.get(f"completed_{plan_id}", set())
        for i, module in enumerate(plan_data['modules']):
            module_key = f"{plan_id}_module_{i}"
            with st.expander(f"Week {module.get('week', i+1)}: {module.get('title', 'Module')}"):
                checked = st.checkbox("Mark as complete", value=module_key in completed_modules, key=module_key)
                if checked:
                    completed_modules.add(module_key)
                else:
                    completed_modules.discard(module_key)
                st.session_state[f"completed_{plan_id}"] = completed_modules
                # Module objectives
                if module.get('objectives'):
                    st.markdown("**🎯 Learning Objectives:**")
                    for obj in module['objectives']:
                        st.write(f"- {obj}")
                
                # Topics covered
                if module.get('topics'):
                    st.markdown("**📖 Topics Covered:**")
                    for j, topic in enumerate(module['topics']):
                        col1, col2 = st.columns([0.85, 0.15])
                        with col1:
                            st.write(f"• {topic}")
                        with col2:
                            if st.button("📝 Quiz", key=f"quiz_{plan_id}_{i}_{j}"):
                                st.session_state['current_quiz_topic'] = topic
                                st.session_state['page'] = 'quiz'
                                st.switch_page("pages/2_Quiz.py")
                
                # Activities
                if module.get('activities'):
                    st.markdown("**🛠️ Activities:**")
                    for activity in module['activities']:
                        st.write(f"• {activity}")
                
                # Resources
                if module.get('resources'):
                    st.markdown("**📚 Resources:**")
                    for resource in module['resources']:
                        st.write(f"• {resource}")
                
                # Time estimate
                if module.get('time_estimate'):
                    st.info(f"⏱️ Estimated time: {module['time_estimate']}")
    
    # Milestones
    if plan_data.get('milestones'):
        st.markdown("### 🏆 Milestones")
        for milestone in plan_data['milestones']:
            with st.container():
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    st.write(f"**W{milestone.get('week', '?')}**")
                with col2:
                    st.write(f"**{milestone.get('milestone', 'Milestone')}**")
                    if milestone.get('criteria'):
                        st.caption(milestone['criteria'])
                st.markdown("---")
    
    # Additional resources
    if plan_data.get('resources'):
        st.markdown("### 🔗 Additional Resources")
        for resource in plan_data['resources']:
            res_type = resource.get('type', 'Resource').title()
            title = resource.get('title', '')
            url = resource.get('url', '')
            if url:
                st.markdown(f"- **{res_type}: [{title}]({url})")
            else:
                st.markdown(f"- **{res_type}: {title}**")
    
    # Tips
    if plan_data.get('tips'):
        st.markdown("### 💡 Learning Tips")
        for tip in plan_data['tips']:
            st.info(f"💡 {tip}")

def display_text_plan(plan_content, plan_id):
    """Display a legacy text-based plan"""
    plan_lines = plan_content.split('\n')
    for i, line in enumerate(plan_lines):
        line = line.strip()
        if not line:
            continue
            
        # Check if line contains actionable content
        if line.startswith(('*', '-', '•')) and len(line) > 10:
            # Extract topic from bullet point
            topic_match = re.search(r'[\*\-•]\s*(.+?)(?:\s*-\s*|\s*$)', line)
            if topic_match:
                topic = topic_match.group(1).strip()
                
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.markdown(line)
                with col2:
                    if len(topic) > 5 and not any(word in topic.lower() for word in ['week', 'overview', 'introduction']):
                        if st.button("📝 Quiz", key=f"quiz_{plan_id}_{i}_{topic[:20]}"):
                            st.session_state['current_quiz_topic'] = topic
                            st.session_state['page'] = 'quiz'
                            st.switch_page("pages/2_Quiz.py")
            else:
                st.markdown(line)
        
        elif line.startswith('#'):
            # Headers
            st.markdown(line)
        
        elif 'Week' in line and ':' in line:
            # Week headers with special formatting
            st.markdown(f"### {line}")
        
        elif line.startswith(('http', 'www', '[')) or 'youtube' in line.lower():
            # Links
            st.markdown(line)
        
        else:
            # Regular content
            st.markdown(line)

# --- Authentication Check ---
if not st.session_state.get('logged_in', False):
    st.error("Please log in to view this page.")
    st.stop()

user_uid = st.session_state.get('user_id')
user_email = st.session_state.get('user_email', 'User')

# --- Header ---
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🎓 Your Learning Dashboard")
    st.markdown(f"Welcome back, **{user_email.split('@')[0].title()}**! Ready to learn something new today?")

with col2:
    st.markdown("### Quick Actions")
    if st.button("📊 Analytics", type="secondary", use_container_width=True):
        st.switch_page("pages/3_Analytics.py")

# --- Dashboard Summary Cards ---
dashboard_data = get_dashboard_summary(user_uid)
if dashboard_data:
    st.markdown("### 📈 Your Progress Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🧠 Total Quizzes", dashboard_data.get('total_quizzes', 0))
    
    with col2:
        avg_perf = dashboard_data.get('average_performance', 0)
        st.metric("📊 Average Score", f"{avg_perf:.1f}%")
    
    with col3:
        streak = dashboard_data.get('learning_streak', 0)
        st.metric("🔥 Learning Streak", f"{streak} days")
    
    with col4:
        total_plans = len(get_user_plans(user_uid))
        st.metric("📚 Study Plans", total_plans)

    st.markdown("---")

# --- Sidebar ---
with st.sidebar:
    st.header("🚀 Create New Learning Plan")
    st.markdown("*Tell me what you want to learn, and I'll create a personalized roadmap for you!*")
    
    # Create a form for better organization
    with st.form("study_plan_form"):
        st.subheader("📝 Learning Details")
        
        # Subject field
        subject = st.text_input(
            "Subject/Topic:",
            placeholder="e.g., Python, Data Science, Machine Learning, Web Development..."
        )
        
        # Learning goal field
        learning_goal = st.text_area(
            "Specific Learning Goal:", 
            height=80,
            placeholder="e.g., Build a web application, Analyze data with Python, Create ML models..."
        )
        
        # Current level
        current_level = st.selectbox(
            "Your Current Level:",
            ["Beginner", "Intermediate", "Advanced"],
            help="Select your current knowledge level in this subject"
        )
        
        # Time commitment
        time_commitment = st.selectbox(
            "Time Commitment:",
            ["1-2 hours/week", "3-5 hours/week", "6-10 hours/week", "10+ hours/week"],
            help="How much time can you dedicate to learning?"
        )
        
        # Additional context (optional)
        additional_context = st.text_area(
            "Additional Context (Optional):",
            height=60,
            placeholder="Any specific requirements, deadlines, or preferences..."
        )
        
        # Submit button
        submitted = st.form_submit_button("✨ Generate My Plan", type="primary", use_container_width=True)
        
        if submitted:
            if subject and learning_goal:
                with st.spinner("🤖 AI is crafting your personalized learning plan..."):
                    success, plan = generate_plan_with_groq(
                        subject=subject,
                        learning_goal=learning_goal,
                        current_level=current_level,
                        time_commitment=time_commitment,
                        additional_context=additional_context
                    )
                    
                    if success:
                        if save_plan_to_firestore(user_uid, f"{subject}: {learning_goal}", plan):
                            st.session_state['newly_generated_plan'] = plan
                            st.success("🎉 Plan created successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to save plan. Please try again.")
                    else:
                        st.error(f"Failed to generate plan: {plan}")
            else:
                st.warning("⚠️ Please fill in both Subject and Learning Goal fields!")
    
    st.markdown("---")
    
    # Quick Navigation
    st.markdown("### 🧭 Quick Navigation")
    if st.button("🧠 Take Quiz", type="secondary", use_container_width=True):
        st.switch_page("pages/2_Quiz.py")
    
    if st.button("📊 View Analytics", type="secondary", use_container_width=True):
        st.switch_page("pages/3_Analytics.py")
    
    st.markdown("---")
    
    # Account Actions
    st.markdown("### ⚙️ Account")
    if st.button("🚪 Logout", type="secondary", use_container_width=True):
        logout_user()

# --- Main Dashboard Content ---
user_plans = get_user_plans(user_uid)

if not user_plans:
    # Empty state with call-to-action
    st.markdown("### 🌟 Let's Start Your Learning Journey!")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        **Welcome to your AI Learning Coach!** 🎓
        
        You don't have any study plans yet, but that's about to change! Here's how to get started:
        
        1. **📝 Tell me your goal** - Use the sidebar to describe what you want to learn
        2. **🤖 Get your AI plan** - I'll create a personalized learning roadmap
        3. **🧠 Test yourself** - Take quizzes to track your progress
        4. **📊 Monitor growth** - Use analytics to see how you're improving
        
        **Popular learning topics:**
        - 🐍 Python Programming
        - 📊 Data Science & Analytics  
        - 🤖 Machine Learning & AI
        - 🌐 Web Development
        - ☁️ Cloud Computing
        - 📱 Mobile App Development
        """)
    
    with col2:
        st.image("https://via.placeholder.com/300x200/4F46E5/FFFFFF?text=AI+Learning", 
                 caption="Your AI-powered learning companion")

else:
    # Display existing plans
    st.markdown("### 📚 Your Study Plans")
    
    # Plan selection
    plan_titles = [f"📖 {plan.get('goal', 'Untitled Plan')}" for plan in user_plans]
    selected_plan_index = st.selectbox(
        "Choose a study plan to view:",
        range(len(plan_titles)),
        format_func=lambda x: plan_titles[x]
    )
    
    selected_plan = user_plans[selected_plan_index]
    selected_plan_content = selected_plan.get('content', '')
    selected_plan_id = selected_plan['id']
    selected_plan_title = selected_plan.get('goal', 'Untitled Plan')

    if selected_plan_content:
        # Plan header with actions
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### 📋 {selected_plan_title}")
            created_at = selected_plan.get('created_at')
            if created_at:
                st.caption(f"Created: {created_at.strftime('%B %d, %Y') if hasattr(created_at, 'strftime') else 'Recently'}")
        
        with col2:
            if st.button("🧠 Quick Quiz", key=f"quick_quiz_{selected_plan_id}"):
                st.session_state['current_quiz_topic'] = selected_plan_title
                st.session_state['page'] = 'quiz'
                st.switch_page("pages/2_Quiz.py")
        
        with col3:
            if st.button("🗑️ Delete Plan", key=f"delete_{selected_plan_id}"):
                if delete_plan_from_firestore(user_uid, selected_plan_id):
                    st.success("Plan deleted successfully!")
                    st.rerun()
                else:
                    st.error("Failed to delete plan.")

        st.markdown("---")
        
        # --- Plan Display ---
        if selected_plan_content:
            plan_obj = selected_plan_content
            if isinstance(selected_plan_content, str):
                try:
                    plan_obj = json.loads(selected_plan_content)
                except Exception:
                    plan_obj = selected_plan_content
            if isinstance(plan_obj, dict):
                display_structured_plan(plan_obj, selected_plan_id)
            elif isinstance(plan_obj, str):
                display_text_plan(plan_obj, selected_plan_id)
            else:
                st.error("Invalid plan format")

        # Plan statistics
        st.markdown("---")
        st.markdown("#### 📊 Plan Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            # Handle both structured and text plans for statistics
            if isinstance(selected_plan_content, dict):
                # Structured plan - count modules
                module_count = len(selected_plan_content.get('modules', []))
                st.metric("📋 Modules/Topics", module_count)
            else:
                # Text plan - count topics/bullets
                plan_lines = selected_plan_content.split('\n') if isinstance(selected_plan_content, str) else []
                topic_count = len([line for line in plan_lines if line.strip().startswith(('*', '-', '•'))])
                st.metric("📋 Topics Covered", topic_count)
        
        with col2:
            # Estimate reading time
            if isinstance(selected_plan_content, dict):
                # For structured plans, estimate based on content
                total_text = str(selected_plan_content)
                word_count = len(total_text.split())
            else:
                # For text plans, count words directly
                word_count = len(selected_plan_content.split()) if isinstance(selected_plan_content, str) else 0
            
            reading_time = max(1, word_count // 200)  # Average reading speed
            st.metric("⏱️ Est. Reading Time", f"{reading_time} min")
        
        with col3:
            # Count resources/links
            if isinstance(selected_plan_content, dict):
                # Structured plan - count resources
                resource_count = len(selected_plan_content.get('resources', []))
                st.metric("🔗 Resources", resource_count)
            else:
                # Text plan - count links
                plan_lines = selected_plan_content.split('\n') if isinstance(selected_plan_content, str) else []
                link_count = len([line for line in plan_lines if 'http' in line or 'youtube' in line.lower()])
                st.metric("🔗 Resources", link_count)

# --- Recent Activity (if user has quiz history) ---
if dashboard_data and dashboard_data.get('recent_performance'):
    st.markdown("---")
    st.markdown("### 🕐 Recent Quiz Activity")
    
    recent_quizzes = dashboard_data['recent_performance'][:3]  # Show last 3
    
    for idx, quiz in enumerate(recent_quizzes):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"📚 **{quiz['topic']}**")
        
        with col2:
            score = quiz['percentage']
            if score >= 80:
                st.success(f"🌟 {score:.0f}%")
            elif score >= 60:
                st.info(f"✅ {score:.0f}%")
            else:
                st.warning(f"📚 {score:.0f}%")
        
        with col3:
            if st.button("🔄 Retake", key=f"retake_{idx}_{quiz['topic']}"):
                st.session_state['current_quiz_topic'] = quiz['topic']
                st.session_state['page'] = 'quiz'
                st.switch_page("pages/2_Quiz.py")

# --- Quick Actions ---
st.markdown("---")
st.markdown("### 🚀 Quick Actions")

action_col1, action_col2, action_col3, action_col4 = st.columns(4)

with action_col1:
    if st.button("🧠 Take Quiz", type="primary", use_container_width=True):
        st.switch_page("pages/2_Quiz.py")

with action_col2:
    if st.button("📊 View Analytics", type="secondary", use_container_width=True):
        st.switch_page("pages/3_Analytics.py")

with action_col3:
    if st.button("🔗 Integrations", type="secondary", use_container_width=True):
        st.switch_page("pages/4_Integrations.py")

with action_col4:
    # Check if any integrations are connected
    from utils.integrations import get_integration_status
    integration_status = get_integration_status(st.session_state.user_id)
    connected_count = sum(1 for status in integration_status.values() if status['connected'])
    
    if connected_count > 0:
        if st.button(f"🔄 Sync ({connected_count})", type="secondary", use_container_width=True):
            from utils.integrations import sync_all_integrations
            with st.spinner("Syncing platforms..."):
                results = sync_all_integrations(st.session_state.user_id)
                success_count = sum(1 for r in results.values() if r['success'])
                st.success(f"✅ Synced {success_count}/{len(results)} platforms")
    else:
        if st.button("⚡ Connect Apps", type="secondary", use_container_width=True):
            st.switch_page("pages/4_Integrations.py")

# --- Footer with tips ---
st.markdown("---")
st.markdown("### 💡 Learning Tips")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **🎯 Set Clear Goals**
    - Define specific learning outcomes
    - Break down complex topics
    - Track your progress regularly
    """)

with col2:
    st.markdown("""
    **🧠 Test Frequently**
    - Take quizzes to reinforce learning
    - Review incorrect answers
    - Practice spaced repetition
    """)

with col3:
    st.markdown("""
    **📊 Monitor Progress**
    - Check your analytics regularly
    - Identify weak areas
    - Celebrate achievements
    """)