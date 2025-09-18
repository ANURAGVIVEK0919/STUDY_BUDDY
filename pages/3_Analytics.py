# pages/3_Analytics.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from utils.db import get_user_analytics, get_user_quiz_history, get_user_plans, generate_analytics_pdf, get_integration_data
from utils.integrations import get_integration_status, sync_all_integrations

st.set_page_config(page_title="Analytics - AI Learning Coach", page_icon="📊", layout="wide")

if not st.session_state.get('logged_in', False):
    st.error("Please login first")
    st.stop()

st.title("📊 Your Learning Analytics")
st.markdown("### Track your progress and identify areas for improvement")

user_id = st.session_state.get('user_id')

# Get user data
quiz_history = get_user_quiz_history(user_id, limit=50)
user_plans = get_user_plans(user_id)

if not quiz_history:
    st.info("📈 Take some quizzes to see your analytics!")
    st.markdown("### 🎯 Get Started:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Create Study Plan", type="primary"):
            st.switch_page("pages/1_Dashboard.py")
    with col2:
        if st.button("🧠 Take a Quiz", type="primary"):
            st.switch_page("pages/2_Quiz.py")
    st.stop()

# Convert to DataFrame for easier analysis
df_quizzes = pd.DataFrame(quiz_history)
if 'completed_at' in df_quizzes.columns:
    df_quizzes['completed_at'] = pd.to_datetime(df_quizzes['completed_at'])
    df_quizzes['date'] = df_quizzes['completed_at'].dt.date

# --- ANALYTICS CARDS ---
st.markdown("### 📈 Quick Stats")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_quizzes = len(quiz_history)
    st.metric("🧠 Total Quizzes", total_quizzes)

with col2:
    avg_score = df_quizzes['percentage'].mean() if not df_quizzes.empty else 0
    st.metric("📊 Average Score", f"{avg_score:.1f}%")

with col3:
    passed_quizzes = len(df_quizzes[df_quizzes['percentage'] >= 60]) if not df_quizzes.empty else 0
    pass_rate = (passed_quizzes / total_quizzes * 100) if total_quizzes > 0 else 0
    st.metric("✅ Pass Rate", f"{pass_rate:.1f}%")

with col4:
    unique_topics = df_quizzes['topic'].nunique() if not df_quizzes.empty else 0
    st.metric("📚 Topics Studied", unique_topics)

st.markdown("---")

# --- PERFORMANCE OVER TIME ---
if len(quiz_history) >= 2:
    st.subheader("📈 Performance Trend")
    
    # Prepare data for line chart
    df_trend = df_quizzes.groupby('date')['percentage'].mean().reset_index()
    df_trend = df_trend.sort_values('date')
    
    fig_trend = px.line(
        df_trend, 
        x='date', 
        y='percentage',
        title="Quiz Scores Over Time",
        markers=True,
        line_shape='spline'
    )
    fig_trend.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Pass Line (60%)")
    fig_trend.update_layout(
        xaxis_title="Date",
        yaxis_title="Average Score (%)",
        yaxis_range=[0, 100]
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Take more quizzes to see your performance trend!")

# --- TOPICS ANALYSIS ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📚 Performance by Topic")
    
    if not df_quizzes.empty:
        topic_performance = df_quizzes.groupby('topic')['percentage'].agg(['mean', 'count']).reset_index()
        topic_performance.columns = ['Topic', 'Average Score', 'Quiz Count']
        topic_performance = topic_performance.sort_values('Average Score', ascending=True)
        
        fig_topics = px.bar(
            topic_performance, 
            x='Average Score', 
            y='Topic',
            orientation='h',
            title="Average Score by Topic",
            color='Average Score',
            color_continuous_scale='RdYlGn'
        )
        fig_topics.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Pass Line")
        st.plotly_chart(fig_topics, use_container_width=True)
        
        # Show topics needing improvement
        weak_topics = topic_performance[topic_performance['Average Score'] < 70]['Topic'].tolist()
        if weak_topics:
            st.warning("🎯 **Topics to Focus On:**")
            for topic in weak_topics[:3]:  # Show top 3 weak topics
                score = topic_performance[topic_performance['Topic'] == topic]['Average Score'].iloc[0]
                st.write(f"• **{topic}** - {score:.1f}% average")

with col2:
    st.subheader("🎯 Quiz Difficulty Distribution")
    
    if not df_quizzes.empty:
        # Create difficulty categories based on scores
        df_quizzes['difficulty_category'] = pd.cut(
            df_quizzes['percentage'], 
            bins=[0, 40, 60, 80, 100], 
            labels=['Very Hard', 'Hard', 'Medium', 'Easy']
        )
        
        difficulty_counts = df_quizzes['difficulty_category'].value_counts()
        
        fig_difficulty = px.pie(
            values=difficulty_counts.values,
            names=difficulty_counts.index,
            title="Quiz Difficulty Distribution",
            color_discrete_map={
                'Very Hard': '#ff4444',
                'Hard': '#ff8800', 
                'Medium': '#ffcc00',
                'Easy': '#44ff44'
            }
        )
        st.plotly_chart(fig_difficulty, use_container_width=True)

# --- LEARNING STREAK ---
st.markdown("---")
st.subheader("🔥 Learning Activity")

col1, col2 = st.columns(2)

with col1:
    # Calculate learning streak
    if not df_quizzes.empty:
        recent_dates = df_quizzes['date'].unique()
        recent_dates = sorted(recent_dates, reverse=True)
        
        current_streak = 0
        yesterday = datetime.now().date() - timedelta(days=1)
        
        for date in recent_dates:
            if date == yesterday or (recent_dates[0] == datetime.now().date() and date == datetime.now().date()):
                current_streak += 1
                yesterday -= timedelta(days=1)
            else:
                break
        
        st.metric("🔥 Current Streak", f"{current_streak} days")
        
        # Show recent activity
        st.markdown("**📅 Recent Activity:**")
        recent_activity = df_quizzes.groupby('date').agg({
            'topic': 'count',
            'percentage': 'mean'
        }).reset_index().sort_values('date', ascending=False).head(5)
        
        for _, row in recent_activity.iterrows():
            date_str = row['date'].strftime("%b %d")
            quizzes_count = int(row['topic'])
            avg_score = row['percentage']
            st.write(f"• **{date_str}**: {quizzes_count} quiz{'s' if quizzes_count > 1 else ''} - {avg_score:.1f}% avg")

with col2:
    # Study plans progress
    st.markdown("**📚 Study Plans Progress:**")
    if user_plans:
        for plan in user_plans[:3]:  # Show first 3 plans
            plan_title = plan.get('goal', 'Untitled Plan')
            # Calculate related quiz performance
            related_quizzes = df_quizzes[df_quizzes['topic'].str.contains(plan_title.split()[0], case=False, na=False)]
            
            if not related_quizzes.empty:
                plan_avg = related_quizzes['percentage'].mean()
                st.write(f"• **{plan_title[:30]}{'...' if len(plan_title) > 30 else ''}**")
                st.progress(plan_avg / 100)
                st.write(f"  {plan_avg:.1f}% average performance")
            else:
                st.write(f"• **{plan_title[:30]}{'...' if len(plan_title) > 30 else ''}**")
                st.write("  📝 No quizzes taken yet")
    else:
        st.info("Create study plans to track progress!")

# --- INSIGHTS AND RECOMMENDATIONS ---
st.markdown("---")
st.subheader("🎯 AI Insights & Recommendations")

insights_col1, insights_col2 = st.columns(2)

with insights_col1:
    st.markdown("**💡 Key Insights:**")
    
    if not df_quizzes.empty:
        # Best performing day
        if 'completed_at' in df_quizzes.columns:
            df_quizzes['day_of_week'] = df_quizzes['completed_at'].dt.day_name()
            best_day = df_quizzes.groupby('day_of_week')['percentage'].mean().idxmax()
            best_day_score = df_quizzes.groupby('day_of_week')['percentage'].mean().max()
            st.write(f"📅 Best study day: **{best_day}** ({best_day_score:.1f}% avg)")
        
        # Improvement trend
        if len(df_quizzes) >= 5:
            recent_scores = df_quizzes.tail(5)['percentage'].mean()
            earlier_scores = df_quizzes.head(5)['percentage'].mean()
            improvement = recent_scores - earlier_scores
            
            if improvement > 5:
                st.write(f"📈 **Improving!** +{improvement:.1f}% vs early scores")
            elif improvement < -5:
                st.write(f"📉 **Needs focus** -{abs(improvement):.1f}% vs early scores")
            else:
                st.write(f"📊 **Consistent** performance maintained")

with insights_col2:
    st.markdown("**🎯 Recommendations:**")
    
    if not df_quizzes.empty:
        avg_score = df_quizzes['percentage'].mean()
        
        if avg_score >= 80:
            st.write("🌟 Excellent performance! Try advanced topics.")
        elif avg_score >= 60:
            st.write("✅ Good progress! Focus on weak areas identified above.")
        else:
            st.write("📚 Review fundamentals before taking more quizzes.")
        
        # Activity recommendation
        days_since_last = (datetime.now().date() - df_quizzes['date'].max()).days if not df_quizzes.empty else 0
        if days_since_last >= 3:
            st.write(f"⏰ It's been {days_since_last} days since your last quiz!")
        elif current_streak >= 3:
            st.write(f"🔥 Great streak! Keep it up!")

# --- EXTERNAL INTEGRATIONS OVERVIEW ---
st.markdown("---")
st.subheader("🔗 External Platform Integrations")

# Check integration status
integration_status = get_integration_status(user_id)
connected_platforms = [platform for platform, status in integration_status.items() if status['connected']]

if connected_platforms:
    st.success(f"✅ Connected to {len(connected_platforms)} platform(s): {', '.join([p.replace('_', ' ').title() for p in connected_platforms])}")
    
    # Sync button
    if st.button("🔄 Sync All Platforms", type="secondary"):
        with st.spinner("Syncing external platforms..."):
            results = sync_all_integrations(user_id)
            for platform, result in results.items():
                if result['success']:
                    st.success(f"✅ {platform.replace('_', ' ').title()}: Synced successfully")
                else:
                    st.error(f"❌ {platform.replace('_', ' ').title()}: Sync failed")
    
    # Quick integration insights
    integration_col1, integration_col2, integration_col3 = st.columns(3)
    
    if 'github' in connected_platforms:
        github_data = get_integration_data(user_id, 'github')
        with integration_col1:
            st.metric("🐙 GitHub", "Connected", delta="Coding Activity Tracked")
    
    if 'google_calendar' in connected_platforms:
        with integration_col2:
            st.metric("📅 Calendar", "Connected", delta="Study Sessions Scheduled")
    
    if 'udemy' in connected_platforms:
        with integration_col3:
            st.metric("🎓 Udemy", "Connected", delta="Course Progress Synced")

else:
    st.info("🔗 Connect external platforms to get comprehensive learning insights!")
    if st.button("⚙️ Go to Integrations", type="primary"):
        st.switch_page("pages/4_Integrations.py")

# --- NAVIGATION ---
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("← Back to Dashboard", type="secondary"):
        st.switch_page("pages/1_Dashboard.py")

with col2:
    if st.button("🧠 Take New Quiz", type="primary"):
        st.switch_page("pages/2_Quiz.py")

with col3:
    if st.button("📊 Export Report", type="secondary"):
        user_email = st.session_state.get('user_email', 'user@example.com')
        
        with st.spinner("🔄 Generating your PDF report..."):
            pdf_data, error = generate_analytics_pdf(user_id, user_email)
            
            if pdf_data:
                # Create download button
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_data,
                    file_name=f"learning_progress_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                st.success("✅ PDF report generated successfully!")
            else:
                st.error(f"❌ Failed to generate PDF: {error}")