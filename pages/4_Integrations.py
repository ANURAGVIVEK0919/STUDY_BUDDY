"""
External Integrations Settings Page
Manage GitHub, Google Calendar, and Udemy integrations
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.auth import require_auth
from utils.integrations import (
    GitHubIntegration, 
    GoogleCalendarIntegration, 
    UdemyIntegration,
    get_integration_status,
    sync_all_integrations
)
from utils.db import get_integration_data, delete_integration_data

# Check authentication
require_auth()

st.set_page_config(
    page_title="Integrations - AI Learning Coach",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 External Platform Integrations")
st.write("Connect your learning journey across platforms")

# Important notice about real API usage
st.warning("""
⚠️ **Real API Integration Notice:**
This system uses **actual API calls** to fetch real data from GitHub, Google Calendar, and Udemy. 
You need valid API credentials for each platform. No sample data is generated.

- **GitHub**: Requires Personal Access Token ✅ (Most Important)
- **Google Calendar**: Requires OAuth2 credentials 🔧 (Optional)  
- **Udemy**: Requires approved API access ⚠️ (Very Limited)
""")

# Check if API keys are configured
import os
github_token_configured = bool(st.secrets.get("github_api", {}).get("personal_access_token", "").replace("your_github_personal_access_token_here", ""))
google_creds_configured = bool(st.secrets.get("google_calendar_api", {}).get("client_id", "").replace("your_google_client_id_here", ""))
udemy_creds_configured = bool(st.secrets.get("udemy_api", {}).get("client_id", "").replace("your_udemy_client_id_here", ""))

# API Status Overview
st.subheader("🔑 API Configuration Status")
config_col1, config_col2, config_col3 = st.columns(3)

with config_col1:
    if github_token_configured:
        st.success("🐙 GitHub: ✅ Configured")
    else:
        st.error("🐙 GitHub: ❌ Not Configured")
        
with config_col2:
    if google_creds_configured:
        st.success("📅 Google: ✅ Configured")
    else:
        st.warning("📅 Google: ⚠️ Not Configured")
        
with config_col3:
    if udemy_creds_configured:
        st.success("🎓 Udemy: ✅ Configured")
    else:
        st.info("🎓 Udemy: ℹ️ Not Configured")

# Setup guide
if not github_token_configured:
    st.error("""
    🚨 **GitHub Setup Required**: GitHub integration is the most valuable feature! 
    Please check the `API_SETUP_GUIDE.md` file for detailed setup instructions.
    """)

if not (github_token_configured or google_creds_configured or udemy_creds_configured):
    with st.expander("📖 Quick Setup Guide"):
        st.markdown("""
        ### 🐙 **GitHub Setup (Recommended)**
        1. Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
        2. Create new token with `user`, `repo`, `user:email` scopes
        3. Add to `.streamlit/secrets.toml` under `[github_api]`
        
        ### 📅 **Google Calendar Setup (Optional)**
        1. Go to [Google Cloud Console](https://console.cloud.google.com/)
        2. Enable Calendar API and create OAuth2 credentials
        3. Add credentials to `.streamlit/secrets.toml`
        
        ### 📖 **Full Guide**
        Check the `API_SETUP_GUIDE.md` file in your project folder for complete instructions!
        """)

st.markdown("---")

# Get current integration status
user_id = st.session_state.user_id
integration_status = get_integration_status(user_id)

# Create tabs for different integrations
tab1, tab2, tab3, tab4 = st.tabs(["🐙 GitHub", "📅 Google Calendar", "🎓 Udemy", "📊 Dashboard"])

# GitHub Integration Tab
with tab1:
    st.header("GitHub Integration")
    st.write("Track your coding activity and get personalized learning suggestions")
    
    github_connected = integration_status['github']['connected']
    user_email = st.session_state.get('user_email', '')
    
    if not github_connected:
        st.info("🔗 Connect your GitHub account to track coding activity and get AI-powered learning recommendations!")
        
        with st.form("github_auth"):
            st.subheader("Connect GitHub Account")
            st.write(f"**Your email:** {user_email}")
            st.write("We'll verify this email matches your GitHub account for secure integration.")
            
            token = st.text_input("Personal Access Token", type="password", 
                                help="Create a token at: https://github.com/settings/tokens (requires 'user', 'repo', 'user:email' scopes)")
            
            st.markdown("""
            **📝 To create a GitHub token:**
            1. Go to GitHub → Settings → Developer settings → Personal access tokens
            2. Click "Generate new token (classic)"
            3. Select scopes: `user`, `repo`, `user:email`
            4. Copy the token and paste it above
            """)
            
            if st.form_submit_button("🔗 Connect GitHub", type="primary"):
                if token and user_email:
                    github = GitHubIntegration()
                    success, result = github.authenticate_with_email(user_email, token)
                    
                    if success:
                        st.success(f"✅ Successfully connected to GitHub as {result['login']}")
                        st.success(f"📧 Email verified: {user_email}")
                        st.rerun()
                    else:
                        st.error(f"❌ Authentication failed: {result}")
                else:
                    st.error("Please provide your GitHub token")
    
    else:
        github_data = get_integration_data(user_id, 'github')
        st.success(f"✅ Connected as **{github_data['username']}**")
        st.success(f"📧 Verified email: **{github_data.get('verified_email', 'N/A')}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Sync GitHub Activity", type="primary"):
                with st.spinner("Syncing real-time GitHub activity..."):
                    github = GitHubIntegration()
                    success, activity = github.get_real_time_activity(
                        github_data['token'], 
                        github_data['username']
                    )
                    
                    if success:
                        st.success("✅ Real-time GitHub activity synced successfully!")
                        
                        # Display comprehensive activity summary
                        st.subheader("📈 Your GitHub Activity (Last 30 Days)")
                        
                        # Main metrics
                        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                        with metrics_col1:
                            st.metric("Total Commits", activity['total_commits'])
                        with metrics_col2:
                            st.metric("Total Repositories", activity['total_repositories'])
                        with metrics_col3:
                            st.metric("Active Repositories", len(activity['active_repos']))
                        with metrics_col4:
                            st.metric("Languages Used", len(activity['languages_used']))
                        
                        # Languages breakdown
                        if activity['languages_used']:
                            st.subheader("💻 Programming Languages")
                            lang_data = []
                            for lang, count in activity['languages_used'].items():
                                lang_data.append({'Language': lang, 'Repositories': count})
                            
                            if lang_data:
                                df_langs = pd.DataFrame(lang_data)
                                st.dataframe(df_langs, use_container_width=True)
                                
                                # Get learning suggestions
                                suggestions = github.suggest_learning_paths(list(activity['languages_used'].keys()))
                                if suggestions:
                                    st.subheader("🎯 AI-Powered Learning Recommendations")
                                    for i, suggestion in enumerate(suggestions[:5], 1):
                                        st.write(f"{i}. {suggestion}")
                        
                        # Recent commits
                        if activity['recent_commits']:
                            st.subheader("📝 Recent Commits")
                            commits_data = []
                            for commit in activity['recent_commits'][:10]:
                                commits_data.append({
                                    'Repository': commit['repo'],
                                    'Message': commit['message'],
                                    'Date': commit['date'][:10],
                                    'SHA': commit['sha']
                                })
                            
                            if commits_data:
                                df_commits = pd.DataFrame(commits_data)
                                st.dataframe(df_commits, use_container_width=True)
                        
                        # Repository details
                        if activity['repository_details']:
                            with st.expander("📂 Repository Details"):
                                for repo in activity['repository_details'][:5]:
                                    col_a, col_b, col_c = st.columns(3)
                                    with col_a:
                                        st.write(f"**{repo['name']}**")
                                        st.write(f"Language: {repo['language'] or 'N/A'}")
                                    with col_b:
                                        st.write(f"⭐ {repo['stars']} stars")
                                        st.write(f"🍴 {repo['forks']} forks")
                                    with col_c:
                                        st.write(f"📝 {repo['commits_count']} commits")
                                        st.write(f"Updated: {repo['last_updated'][:10]}")
                                    st.markdown("---")
                                    
                    else:
                        st.error(f"❌ Failed to sync: {activity}")
        
        with col2:
            if st.button("🗑️ Disconnect GitHub", type="secondary"):
                if delete_integration_data(user_id, 'github'):
                    st.success("✅ GitHub disconnected successfully")
                    st.rerun()
                else:
                    st.error("❌ Failed to disconnect GitHub")

# Google Calendar Integration Tab
with tab2:
    st.header("Google Calendar Integration via Firebase")
    st.write("Schedule study sessions using Firebase Google authentication")
    
    calendar_connected = integration_status['google_calendar']['connected']
    
    if not calendar_connected:
        st.info("🗓️ Connect Google Calendar through Firebase for seamless integration!")
        
        # Method 1: Firebase Google Sign-In
        st.subheader("Method 1: Firebase Google Authentication")
        st.write("If you signed in to this app using your Google account, we can access your Calendar automatically:")
        
        if st.button("🔗 Connect via Firebase Google Auth", type="primary", key="firebase_auth_calendar"):
            if 'user_id' in st.session_state:
                # Check if user has Firebase ID token
                firebase_token = st.session_state.get('firebase_id_token')
                if firebase_token:
                    calendar = GoogleCalendarIntegration()
                    success, message = calendar.authenticate_with_firebase(firebase_token)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                        st.info("💡 Make sure you signed in with Google and granted Calendar permissions")
                else:
                    st.error("❌ No Firebase authentication token found. Please sign in with Google.")
            else:
                st.error("❌ Please sign in to use integrations")
        
        st.markdown("---")
        
        # Method 2: Firebase Service Account
        st.subheader("Method 2: Firebase Service Account")
        st.write("Use your Firebase project's service account for Calendar access:")
        
        with st.expander("📋 Service Account Setup Instructions"):
            st.markdown("""
            **To enable Firebase service account Calendar access:**
            
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Select your Firebase project
            3. Go to **APIs & Services** → **Library**
            4. Search for "Google Calendar API" and **Enable** it
            5. Go to **IAM & Admin** → **Service Accounts**
            6. Find your Firebase service account (usually `firebase-adminsdk-...@your-project.iam.gserviceaccount.com`)
            7. Make sure it has the **Editor** role or custom role with Calendar permissions
            8. Your Firebase Admin SDK will automatically use these credentials
            
            **Note:** This method uses your Firebase project's service account, so Calendar events will be created in that account's calendar.
            """)
        
        if st.button("🔗 Connect via Firebase Service Account", type="secondary", key="firebase_service_calendar"):
            if 'user_id' in st.session_state:
                calendar = GoogleCalendarIntegration()
                success, message = calendar.authenticate_with_firebase_config()
                if success:
                    st.success(f"✅ {message}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
                    st.info("💡 Make sure Calendar API is enabled in your Firebase project's Google Cloud Console")
            else:
                st.error("❌ Please sign in to use integrations")
        
        # Legacy OAuth2 method (still available)
        with st.expander("🔧 Alternative: Direct OAuth2 Setup (Advanced)"):
            st.subheader("Connect Google Calendar")
            st.write("� **Real Google Calendar API Integration**")
            
            st.markdown("""
            **📝 To connect Google Calendar:**
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a project and enable Calendar API
            3. Create OAuth2 credentials
            4. Download the credentials JSON
            5. Paste the JSON content below
            
            **Required Scopes:** `https://www.googleapis.com/auth/calendar`
            """)
            
            credentials_json = st.text_area(
                "OAuth2 Credentials JSON", 
                placeholder='{"client_id":"your-client-id","client_secret":"your-secret",...}',
                height=100
            )
            
            if st.button("🔗 Connect Google Calendar", type="primary", key="oauth2_calendar_connect"):
                if credentials_json.strip():
                    calendar = GoogleCalendarIntegration()
                    success, result = calendar.authenticate(credentials_json)
                    
                    if success:
                        st.success("✅ Google Calendar connected successfully!")
                        st.success(result)
                        st.rerun()
                    else:
                        st.error(f"❌ Connection failed: {result}")
                else:
                    st.error("Please provide OAuth2 credentials JSON")
    
    else:
        st.success("✅ Google Calendar connected")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Schedule Study Session")
            
            with st.form("schedule_session"):
                title = st.text_input("Session Title", value="AI Learning Session")
                
                date = st.date_input("Date", value=datetime.now().date())
                time = st.time_input("Start Time", value=datetime.now().time())
                duration = st.selectbox("Duration", [1, 2, 3, 4], index=0, format_func=lambda x: f"{x} hour{'s' if x > 1 else ''}")
                
                description = st.text_area("Description (Optional)", 
                                         placeholder="Study plan goals, topics to cover...")
                
                if st.form_submit_button("📅 Schedule Session", type="primary"):
                    start_datetime = datetime.combine(date, time)
                    
                    calendar = GoogleCalendarIntegration()
                    success, result = calendar.create_study_event(
                        title, start_datetime, duration, description
                    )
                    
                    if success:
                        st.success("✅ Study session scheduled successfully!")
                    else:
                        st.error(f"❌ Failed to schedule: {result}")
        
        with col2:
            st.subheader("📋 Upcoming Sessions")
            
            calendar = GoogleCalendarIntegration()
            success, events = calendar.get_upcoming_events()
            
            if success and events:
                for event in events:
                    with st.expander(f"📅 {event['title']}"):
                        st.write(f"**Date:** {event['start_time'][:10]}")
                        st.write(f"**Time:** {event['start_time'][11:16]}")
                        if event['description']:
                            st.write(f"**Description:** {event['description']}")
            else:
                st.info("No upcoming study sessions scheduled")
        
        if st.button("🗑️ Disconnect Google Calendar", type="secondary"):
            if delete_integration_data(user_id, 'google_calendar'):
                st.success("✅ Google Calendar disconnected successfully")
                st.rerun()
            else:
                st.error("❌ Failed to disconnect Google Calendar")

# Udemy Integration Tab
with tab3:
    st.header("Udemy Integration")
    st.write("Sync your course progress and get personalized recommendations")
    
    udemy_connected = integration_status['udemy']['connected']
    user_email = st.session_state.get('user_email', '')
    
    if not udemy_connected:
        st.info("🎓 Connect Udemy to track course progress and get AI-powered recommendations!")
        
        with st.form("udemy_auth"):
            st.subheader("Connect Udemy Account")
            st.write(f"**Your email:** {user_email}")
            st.write("🔗 **Real Udemy API Integration** - Enter your actual Udemy API credentials.")
            
            st.markdown("""
            **📝 To get Udemy API credentials:**
            1. Go to [Udemy API Documentation](https://www.udemy.com/developers/affiliate/)
            2. Apply for API access (requires approval)
            3. Get your Client ID and Client Secret
            4. Enter them below for real data access
            
            **⚠️ Note:** Udemy API access is limited and may require special permissions for user course data.
            """)
            
            client_id = st.text_input("Client ID", placeholder="your-udemy-client-id")
            client_secret = st.text_input("Client Secret", type="password", placeholder="your-udemy-client-secret")
            
            if st.form_submit_button("🔗 Connect Udemy", type="primary"):
                if client_id and client_secret and user_email:
                    udemy = UdemyIntegration()
                    success, result = udemy.authenticate_with_email(user_email, client_id, client_secret)
                    
                    if success:
                        st.success("✅ Udemy connected successfully!")
                        st.success(f"📧 Using email: {user_email}")
                        st.rerun()
                    else:
                        st.error(f"❌ Connection failed: {result}")
                else:
                    st.error("Please provide all required fields")
    
    else:
        udemy_data = get_integration_data(user_id, 'udemy')
        st.success(f"✅ Udemy connected")
        st.success(f"📧 Email: **{udemy_data.get('verified_email', user_email)}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Sync Course Progress", type="primary"):
                with st.spinner("Syncing real-time Udemy courses..."):
                    udemy = UdemyIntegration()
                    success, courses = udemy.get_real_enrolled_courses(user_email)
                    
                    if success:
                        st.success("✅ Real-time courses synced successfully!")
                        
                        st.subheader("📚 Your Enrolled Courses")
                        
                        # Course metrics
                        total_courses = len(courses)
                        completed = len([c for c in courses if c['progress_percentage'] >= 90])
                        in_progress = len([c for c in courses if 10 <= c['progress_percentage'] < 90])
                        
                        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                        with metrics_col1:
                            st.metric("Total Courses", total_courses)
                        with metrics_col2:
                            st.metric("Completed", completed)
                        with metrics_col3:
                            st.metric("In Progress", in_progress)
                        
                        # Course details
                        for course in courses:
                            with st.expander(f"📘 {course['title']} ({course['progress_percentage']}% complete)"):
                                course_col1, course_col2 = st.columns(2)
                                
                                with course_col1:
                                    st.write(f"**Instructor:** {course['instructor']}")
                                    st.write(f"**Category:** {course['category']}")
                                    st.write(f"**Difficulty:** {course['difficulty']}")
                                    st.write(f"**Rating:** ⭐ {course['rating']}/5.0")
                                
                                with course_col2:
                                    st.write(f"**Status:** {course['status']}")
                                    st.write(f"**Enrolled:** {course['enrollment_date']}")
                                    st.write(f"**Last Accessed:** {course['last_accessed']}")
                                    st.write(f"**Progress:** {course['completed_lectures']}/{course['total_lectures']} lectures")
                                
                                # Progress bar
                                progress_val = course['progress_percentage'] / 100
                                st.progress(progress_val)
                                
                                # Time progress
                                time_spent = course['progress_minutes']
                                total_time = course['total_duration_minutes']
                                st.write(f"⏱️ Time: {time_spent//60}h {time_spent%60}m / {total_time//60}h {total_time%60}m")
                    
                    else:
                        st.error(f"❌ Failed to sync: {courses}")
        
        with col2:
            st.subheader("📊 Detailed Analytics")
            
            udemy = UdemyIntegration()
            success, analytics = udemy.get_detailed_analytics(user_email)
            
            if success:
                # Main analytics
                analytics_col1, analytics_col2 = st.columns(2)
                with analytics_col1:
                    st.metric("Completion Rate", f"{analytics['completion_rate']}%")
                    st.metric("Learning Hours", f"{analytics['completed_learning_hours']:.1f}h")
                
                with analytics_col2:
                    st.metric("Average Progress", f"{analytics['average_progress']:.1f}%")
                    st.metric("Average Rating", f"{analytics['average_rating']:.1f}⭐")
                
                # Category breakdown
                if analytics['categories']:
                    st.subheader("📊 Progress by Category")
                    cat_data = []
                    for cat, data in analytics['categories'].items():
                        cat_data.append({
                            'Category': cat,
                            'Courses': data['count'],
                            'Avg Progress': f"{data['avg_progress']:.1f}%"
                        })
                    
                    df_categories = pd.DataFrame(cat_data)
                    st.dataframe(df_categories, use_container_width=True)
                
                # Courses needing attention
                if analytics['courses_needing_attention']:
                    st.subheader("⚠️ Courses Needing Attention")
                    for course in analytics['courses_needing_attention']:
                        st.write(f"• **{course['title']}** ({course['progress_percentage']}% complete)")
                        st.write(f"  Last accessed: {course['last_accessed']}")
                
                # High performing courses
                if analytics['high_performing_courses']:
                    with st.expander("🌟 High Performing Courses"):
                        for course in analytics['high_performing_courses']:
                            st.write(f"• **{course['title']}** ({course['progress_percentage']}% complete)")
        
        if st.button("🗑️ Disconnect Udemy", type="secondary"):
            if delete_integration_data(user_id, 'udemy'):
                st.success("✅ Udemy disconnected successfully")
                st.rerun()
            else:
                st.error("❌ Failed to disconnect Udemy")

# Dashboard Tab
with tab4:
    st.header("🔗 Integration Dashboard")
    st.write("Comprehensive overview of your learning journey across all platforms")
    
    user_email = st.session_state.get('user_email', '')
    
    # Connection Status Overview
    st.subheader("📊 Connection Status")
    
    status_data = []
    for platform, status in integration_status.items():
        status_data.append({
            'Platform': platform.replace('_', ' ').title(),
            'Status': '✅ Connected' if status['connected'] else '❌ Not Connected',
            'Last Sync': status['last_sync'] or 'Never'
        })
    
    status_df = pd.DataFrame(status_data)
    st.dataframe(status_df, use_container_width=True)
    
    # Comprehensive Learning Insights
    from utils.integrations import get_user_learning_insights
    
    if st.button("🧠 Generate AI Learning Insights", type="primary"):
        with st.spinner("Analyzing your learning patterns across platforms..."):
            success, insights = get_user_learning_insights(user_id, user_email)
            
            if success:
                st.success("✅ AI Learning Insights Generated!")
                
                # Overall Learning Score
                st.subheader("🎯 Your Learning Score")
                score = insights['overall_score']
                
                score_col1, score_col2, score_col3 = st.columns(3)
                with score_col1:
                    st.metric("Overall Score", f"{score}/100")
                
                with score_col2:
                    if score >= 80:
                        st.success("🌟 Excellent learner!")
                    elif score >= 60:
                        st.info("👍 Good progress!")
                    elif score >= 40:
                        st.warning("📚 Keep learning!")
                    else:
                        st.error("🚀 Just getting started!")
                
                with score_col3:
                    # Progress bar
                    st.progress(score / 100)
                
                # Platform-specific insights
                insights_col1, insights_col2 = st.columns(2)
                
                with insights_col1:
                    if insights['github']:
                        st.subheader("🐙 GitHub Insights")
                        github_data = insights['github']
                        st.write(f"**Total Commits:** {github_data['total_commits']}")
                        st.write(f"**Active Repositories:** {github_data['active_repos']}")
                        st.write(f"**Languages:** {', '.join(github_data['languages'][:3])}...")
                        
                        if github_data['recent_activity']:
                            st.write("**Recent Activity:**")
                            for activity in github_data['recent_activity'][:3]:
                                st.write(f"• {activity['repo']}: {activity['message'][:50]}...")
                    else:
                        st.info("🐙 Connect GitHub to see coding insights")
                
                with insights_col2:
                    if insights['udemy']:
                        st.subheader("🎓 Udemy Insights")
                        udemy_data = insights['udemy']
                        st.write(f"**Completion Rate:** {udemy_data['completion_rate']}%")
                        st.write(f"**Total Courses:** {udemy_data['total_courses']}")
                        st.write(f"**Learning Hours:** {udemy_data['learning_hours']:.1f}h")
                        st.write(f"**Categories:** {', '.join(udemy_data['categories'][:3])}...")
                    else:
                        st.info("🎓 Connect Udemy to see course insights")
                
                # AI Recommendations
                if insights['recommendations']:
                    st.subheader("🤖 AI-Powered Recommendations")
                    
                    for i, rec in enumerate(insights['recommendations'], 1):
                        with st.container():
                            st.write(f"**{i}. {rec['title']}**")
                            st.write(f"💡 {rec['reason']}")
                            st.markdown("---")
                
                # Cross-platform Learning Map
                st.subheader("🗺️ Your Learning Map")
                
                if insights['github'] and insights['udemy']:
                    # Create a visual learning map
                    map_data = {
                        'GitHub Languages': insights['github']['languages'],
                        'Udemy Categories': insights['udemy']['categories'],
                        'Commits This Month': insights['github']['total_commits'],
                        'Course Completion': f"{insights['udemy']['completion_rate']}%"
                    }
                    
                    # Display as cards
                    map_col1, map_col2 = st.columns(2)
                    
                    with map_col1:
                        st.markdown("**🔨 Technical Skills (GitHub)**")
                        for lang in insights['github']['languages'][:5]:
                            st.write(f"• {lang}")
                    
                    with map_col2:
                        st.markdown("**📚 Learning Areas (Udemy)**")
                        for cat in insights['udemy']['categories'][:5]:
                            st.write(f"• {cat}")
                
            else:
                st.error(f"❌ Failed to generate insights: {insights}")
    
    # Sync All Integrations
    if st.button("🔄 Sync All Connected Platforms", type="secondary"):
        with st.spinner("Syncing all platforms..."):
            results = sync_all_integrations(user_id)
            
            st.subheader("🔄 Sync Results")
            for platform, result in results.items():
                if result['success']:
                    st.success(f"✅ {platform.replace('_', ' ').title()}: Synced successfully")
                    
                    # Show quick preview of data
                    if result['data'] and platform == 'github':
                        data = result['data']
                        st.write(f"   📊 {data['total_commits']} commits, {len(data['languages_used'])} languages")
                    elif result['data'] and platform == 'udemy':
                        data = result['data']
                        st.write(f"   📚 {data['completion_rate']}% completion rate, {data['total_courses']} courses")
                else:
                    st.error(f"❌ {platform.replace('_', ' ').title()}: Sync failed")
    
    # Integration Benefits
    st.subheader("🌟 Why Connect These Platforms?")
    
    benefits_col1, benefits_col2, benefits_col3 = st.columns(3)
    
    with benefits_col1:
        st.markdown("""
        **🐙 GitHub Benefits:**
        - Track coding activity
        - Get language-specific learning paths
        - Identify skill gaps
        - Monitor programming progress
        """)
    
    with benefits_col2:
        st.markdown("""
        **📅 Calendar Benefits:**
        - Schedule study sessions
        - Set learning reminders
        - Track study time
        - Maintain consistency
        """)
    
    with benefits_col3:
        st.markdown("""
        **🎓 Udemy Benefits:**
        - Sync course progress
        - Get completion insights
        - Identify stalled courses
        - Optimize learning path
        """)
    
    # Integration Tips
    with st.expander("💡 Integration Tips & Best Practices"):
        st.markdown("""
        ### 🔐 Security & Privacy
        - All integration data is securely stored and encrypted
        - You can disconnect any platform at any time
        - We only access necessary data for learning analytics
        
        ### 📈 Maximizing Benefits
        - **GitHub**: Keep your repositories active and well-documented
        - **Calendar**: Schedule regular study sessions for consistency
        - **Udemy**: Complete courses to track progress accurately
        
        ### 🔄 Sync Frequency
        - Manual sync is available anytime
        - Consider syncing weekly for best insights
        - Check connection status if sync fails
        """)

# Footer
st.markdown("---")
st.markdown("**🤖 AI Learning Coach** - Connecting your learning journey across platforms")