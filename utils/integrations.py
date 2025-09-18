"""
External Platform Integrations Module
Handles GitHub, Google Calendar, and Udemy API integrations
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from utils.db import save_integration_data, get_integration_data

class GitHubIntegration:
    """GitHub API integration for tracking coding activity"""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        
    def authenticate(self, username, token):
        """Authenticate with GitHub using personal access token"""
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            response = requests.get(f"{self.base_url}/user", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                # Save integration credentials securely
                save_integration_data(st.session_state.user_id, 'github', {
                    'username': username,
                    'token': token,  # In production, encrypt this
                    'authenticated': True,
                    'user_data': user_data,
                    'email': user_data.get('email'),
                    'last_sync': datetime.now().isoformat()
                })
                return True, user_data
            else:
                return False, "Authentication failed"
        except Exception as e:
            return False, str(e)
    
    def authenticate_with_email(self, email, token):
        """Authenticate and verify email matches the GitHub account"""
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Get user info
            response = requests.get(f"{self.base_url}/user", headers=headers)
            if response.status_code != 200:
                return False, "Invalid GitHub token"
            
            user_data = response.json()
            
            # Get user emails (including private ones)
            emails_response = requests.get(f"{self.base_url}/user/emails", headers=headers)
            if emails_response.status_code == 200:
                emails = emails_response.json()
                user_emails = [e['email'] for e in emails]
                
                # Check if provided email matches any GitHub email
                if email.lower() in [e.lower() for e in user_emails]:
                    # Save integration credentials
                    save_integration_data(st.session_state.user_id, 'github', {
                        'username': user_data['login'],
                        'token': token,
                        'authenticated': True,
                        'user_data': user_data,
                        'verified_email': email,
                        'all_emails': user_emails,
                        'last_sync': datetime.now().isoformat()
                    })
                    return True, user_data
                else:
                    return False, f"Email {email} is not associated with this GitHub account"
            else:
                # Fallback: use public email from user data
                if user_data.get('email') and user_data['email'].lower() == email.lower():
                    save_integration_data(st.session_state.user_id, 'github', {
                        'username': user_data['login'],
                        'token': token,
                        'authenticated': True,
                        'user_data': user_data,
                        'verified_email': email,
                        'last_sync': datetime.now().isoformat()
                    })
                    return True, user_data
                else:
                    return False, "Could not verify email with GitHub account"
                    
        except Exception as e:
            return False, str(e)
    
    def get_repositories(self, username, token):
        """Fetch user's repositories"""
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            response = requests.get(f"{self.base_url}/users/{username}/repos", headers=headers)
            
            if response.status_code == 200:
                repos = response.json()
                return True, repos
            else:
                return False, "Failed to fetch repositories"
        except Exception as e:
            return False, str(e)
    
    def get_real_time_activity(self, token, username, days=30):
        """Get comprehensive real-time GitHub activity"""
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get user's repositories
            repos_response = requests.get(f"{self.base_url}/user/repos", headers=headers, 
                                        params={'sort': 'updated', 'per_page': 100})
            
            if repos_response.status_code != 200:
                return False, "Failed to fetch repositories"
            
            repos = repos_response.json()
            
            # Initialize activity data
            activity_data = {
                'total_commits': 0,
                'total_repositories': len(repos),
                'languages_used': {},
                'recent_commits': [],
                'active_repos': [],
                'repository_details': [],
                'contribution_stats': {},
                'last_updated': datetime.now().isoformat()
            }
            
            # Process each repository
            for repo in repos:
                repo_activity = {
                    'name': repo['name'],
                    'description': repo['description'],
                    'language': repo['language'],
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'last_updated': repo['updated_at'],
                    'commits_count': 0,
                    'recent_commits': []
                }
                
                # Count languages
                if repo['language']:
                    activity_data['languages_used'][repo['language']] = \
                        activity_data['languages_used'].get(repo['language'], 0) + 1
                
                # Get commits for this repository
                try:
                    commits_response = requests.get(
                        f"{self.base_url}/repos/{username}/{repo['name']}/commits",
                        headers=headers,
                        params={'since': since_date, 'author': username, 'per_page': 50}
                    )
                    
                    if commits_response.status_code == 200:
                        commits = commits_response.json()
                        repo_activity['commits_count'] = len(commits)
                        activity_data['total_commits'] += len(commits)
                        
                        # Store recent commits
                        for commit in commits[:5]:  # Last 5 commits per repo
                            commit_data = {
                                'repo': repo['name'],
                                'message': commit['commit']['message'][:100],
                                'date': commit['commit']['author']['date'],
                                'sha': commit['sha'][:7]
                            }
                            repo_activity['recent_commits'].append(commit_data)
                            activity_data['recent_commits'].append(commit_data)
                        
                        # Check if repo is active (has commits in the period)
                        if len(commits) > 0:
                            activity_data['active_repos'].append(repo['name'])
                
                except Exception as e:
                    print(f"Error fetching commits for {repo['name']}: {e}")
                    continue
                
                activity_data['repository_details'].append(repo_activity)
            
            # Get contribution stats
            try:
                events_response = requests.get(f"{self.base_url}/users/{username}/events", 
                                             headers=headers, params={'per_page': 100})
                
                if events_response.status_code == 200:
                    events = events_response.json()
                    
                    # Count different types of contributions
                    contribution_types = {}
                    for event in events:
                        event_type = event['type']
                        contribution_types[event_type] = contribution_types.get(event_type, 0) + 1
                    
                    activity_data['contribution_stats'] = contribution_types
            
            except Exception as e:
                print(f"Error fetching contribution stats: {e}")
            
            # Sort recent commits by date
            activity_data['recent_commits'] = sorted(
                activity_data['recent_commits'], 
                key=lambda x: x['date'], 
                reverse=True
            )[:20]  # Keep only the 20 most recent
            
            # Update saved data
            integration_data = get_integration_data(st.session_state.user_id, 'github')
            if integration_data:
                integration_data.update({
                    'last_activity_sync': datetime.now().isoformat(),
                    'activity_data': activity_data
                })
                save_integration_data(st.session_state.user_id, 'github', integration_data)
            
            return True, activity_data
            
        except Exception as e:
            return False, str(e)
    
    def suggest_learning_paths(self, languages_used):
        """Suggest learning paths based on GitHub activity"""
        suggestions = []
        
        language_suggestions = {
            'Python': ['Data Science with Python', 'Django Web Development', 'Machine Learning'],
            'JavaScript': ['React.js', 'Node.js', 'TypeScript'],
            'Java': ['Spring Framework', 'Android Development', 'Microservices'],
            'C++': ['System Programming', 'Game Development', 'Competitive Programming'],
            'Go': ['Cloud Computing', 'Microservices', 'DevOps'],
            'Rust': ['System Programming', 'WebAssembly', 'Blockchain Development']
        }
        
        for lang in languages_used:
            if lang in language_suggestions:
                suggestions.extend(language_suggestions[lang])
        
        return list(set(suggestions))  # Remove duplicates

class GoogleCalendarIntegration:
    """Google Calendar API integration through Firebase"""
    
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        
    def authenticate_with_firebase(self, id_token):
        """Authenticate Google Calendar using Firebase ID token"""
        try:
            # Verify the Firebase ID token
            from firebase_admin import auth
            decoded_token = auth.verify_id_token(id_token)
            user_id = decoded_token['uid']
            
            # Check if user signed in with Google
            if 'firebase' in decoded_token and 'sign_in_provider' in decoded_token['firebase']:
                if decoded_token['firebase']['sign_in_provider'] == 'google.com':
                    # User authenticated with Google through Firebase
                    
                    # Extract Google access token if available in custom claims
                    google_access_token = decoded_token.get('google_access_token')
                    
                    if google_access_token:
                        # Test Calendar API access
                        headers = {
                            'Authorization': f'Bearer {google_access_token}',
                            'Accept': 'application/json'
                        }
                        
                        test_response = requests.get(
                            'https://www.googleapis.com/calendar/v3/users/me/calendarList',
                            headers=headers
                        )
                        
                        if test_response.status_code == 200:
                            calendar_data = test_response.json()
                            
                            # Save integration data
                            save_integration_data(st.session_state.user_id, 'google_calendar', {
                                'authenticated': True,
                                'firebase_user_id': user_id,
                                'google_access_token': google_access_token,
                                'calendar_count': len(calendar_data.get('items', [])),
                                'last_auth': datetime.now().isoformat(),
                                'auth_method': 'firebase_google'
                            })
                            
                            return True, f"Successfully connected via Firebase! Found {len(calendar_data.get('items', []))} calendars"
                        else:
                            return False, "Calendar API access denied. Calendar scope may not be enabled."
                    else:
                        return False, "Google access token not available in Firebase token"
                else:
                    return False, "User did not sign in with Google provider"
            else:
                return False, "Invalid Firebase token structure"
                
        except Exception as e:
            return False, f"Firebase Google Calendar authentication failed: {str(e)}"
    
    def authenticate_with_firebase_config(self):
        """Alternative: Use Firebase project's Google Cloud credentials"""
        try:
            # Use Firebase project's default credentials for Calendar API
            import google.auth
            from google.auth.transport.requests import Request
            
            # Get default credentials (uses Firebase service account)
            credentials, project = google.auth.default(scopes=self.scopes)
            
            # Refresh credentials if needed
            if not credentials.valid:
                credentials.refresh(Request())
            
            # Test Calendar API access
            service = build('calendar', 'v3', credentials=credentials)
            calendar_list = service.calendarList().list().execute()
            
            # Save integration data
            save_integration_data(st.session_state.user_id, 'google_calendar', {
                'authenticated': True,
                'auth_method': 'firebase_service_account',
                'project_id': project,
                'calendar_count': len(calendar_list.get('items', [])),
                'last_auth': datetime.now().isoformat(),
                'service_account': True
            })
            
            return True, f"Connected via Firebase service account! Found {len(calendar_list.get('items', []))} calendars"
            
        except Exception as e:
            return False, f"Firebase service account Calendar authentication failed: {str(e)}"
    
    def create_study_event_firebase(self, title, start_time, duration_hours=1, description=""):
        """Create study event using Firebase-authenticated Calendar access"""
        try:
            integration_data = get_integration_data(st.session_state.user_id, 'google_calendar')
            if not integration_data or not integration_data.get('authenticated'):
                return False, "Not authenticated with Google Calendar via Firebase"
            
            auth_method = integration_data.get('auth_method')
            
            if auth_method == 'firebase_google':
                # Use Google access token from Firebase auth
                access_token = integration_data.get('google_access_token')
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                # Create event object
                end_time = start_time + timedelta(hours=duration_hours)
                
                event = {
                    'summary': title,
                    'description': description,
                    'start': {
                        'dateTime': start_time.isoformat(),
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': end_time.isoformat(),
                        'timeZone': 'UTC',
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'email', 'minutes': 24 * 60},
                            {'method': 'popup', 'minutes': 30},
                        ],
                    },
                }
                
                # Create event via REST API
                response = requests.post(
                    'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                    headers=headers,
                    json=event
                )
                
                if response.status_code == 200:
                    created_event = response.json()
                    return True, f"Study session created! Event ID: {created_event.get('id')}"
                else:
                    return False, f"Failed to create event: HTTP {response.status_code}"
                    
            elif auth_method == 'firebase_service_account':
                # Use Firebase service account
                import google.auth
                from google.auth.transport.requests import Request
                
                credentials, _ = google.auth.default(scopes=self.scopes)
                if not credentials.valid:
                    credentials.refresh(Request())
                
                service = build('calendar', 'v3', credentials=credentials)
                
                end_time = start_time + timedelta(hours=duration_hours)
                
                event = {
                    'summary': title,
                    'description': description,
                    'start': {
                        'dateTime': start_time.isoformat(),
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': end_time.isoformat(),
                        'timeZone': 'UTC',
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'email', 'minutes': 24 * 60},
                            {'method': 'popup', 'minutes': 30},
                        ],
                    },
                }
                
                created_event = service.events().insert(calendarId='primary', body=event).execute()
                return True, f"Study session created via Firebase! Event ID: {created_event.get('id')}"
            
            else:
                return False, "Unknown authentication method"
                
        except Exception as e:
            return False, f"Failed to create calendar event via Firebase: {str(e)}"
    
    def get_upcoming_events_firebase(self, days=7):
        """Get upcoming events using Firebase-authenticated Calendar access"""
        try:
            integration_data = get_integration_data(st.session_state.user_id, 'google_calendar')
            if not integration_data or not integration_data.get('authenticated'):
                return False, "Not authenticated with Google Calendar via Firebase"
            
            auth_method = integration_data.get('auth_method')
            
            if auth_method == 'firebase_google':
                # Use Google access token from Firebase auth
                access_token = integration_data.get('google_access_token')
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }
                
                # Calculate time range
                now = datetime.utcnow()
                time_min = now.isoformat() + 'Z'
                time_max = (now + timedelta(days=days)).isoformat() + 'Z'
                
                # Get events via REST API
                params = {
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'maxResults': 50,
                    'singleEvents': True,
                    'orderBy': 'startTime'
                }
                
                response = requests.get(
                    'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    events_data = response.json()
                    events = events_data.get('items', [])
                else:
                    return False, f"Failed to fetch events: HTTP {response.status_code}"
                    
            elif auth_method == 'firebase_service_account':
                # Use Firebase service account
                import google.auth
                from google.auth.transport.requests import Request
                
                credentials, _ = google.auth.default(scopes=self.scopes)
                if not credentials.valid:
                    credentials.refresh(Request())
                
                service = build('calendar', 'v3', credentials=credentials)
                
                now = datetime.utcnow()
                time_min = now.isoformat() + 'Z'
                time_max = (now + timedelta(days=days)).isoformat() + 'Z'
                
                events_result = service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
            
            else:
                return False, "Unknown authentication method"
            
            # Process events
            upcoming_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                event_data = {
                    'id': event.get('id'),
                    'title': event.get('summary', 'No Title'),
                    'start_time': start,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'attendees': len(event.get('attendees', [])),
                    'created': event.get('created'),
                    'html_link': event.get('htmlLink')
                }
                upcoming_events.append(event_data)
            
            return True, upcoming_events
            
        except Exception as e:
            return False, f"Failed to fetch calendar events via Firebase: {str(e)}"

class UdemyIntegration:
    """Udemy API integration for course progress tracking"""
    
    def __init__(self):
        self.base_url = "https://www.udemy.com/api-2.0"
    
    def authenticate_with_email(self, email, client_id, client_secret):
        """Authenticate with Udemy API using real credentials"""
        try:
            if not client_id or not client_secret:
                return False, "Client ID and Client Secret are required"
            
            # Test authentication with Udemy API
            auth_url = f"{self.base_url}/oauth2/token/"
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            try:
                auth_response = requests.post(auth_url, data=auth_data, timeout=10)
                
                if auth_response.status_code == 200:
                    token_data = auth_response.json()
                    access_token = token_data.get('access_token')
                    
                    if access_token:
                        # Store real authentication data
                        auth_data = {
                            'client_id': client_id,
                            'client_secret': client_secret,  # In production, encrypt this
                            'authenticated': True,
                            'verified_email': email,
                            'auth_date': datetime.now().isoformat(),
                            'access_token': access_token,
                            'token_type': token_data.get('token_type', 'Bearer'),
                            'expires_in': token_data.get('expires_in', 3600)
                        }
                        
                        save_integration_data(st.session_state.user_id, 'udemy', auth_data)
                        return True, "Successfully authenticated with Udemy API"
                    else:
                        return False, "No access token received from Udemy"
                
                elif auth_response.status_code == 401:
                    return False, "Invalid Udemy API credentials (Client ID or Secret incorrect)"
                elif auth_response.status_code == 403:
                    return False, "Access forbidden - check your Udemy API permissions"
                else:
                    return False, f"Udemy authentication failed with status code: {auth_response.status_code}"
                    
            except requests.exceptions.Timeout:
                return False, "Udemy API request timed out - please try again"
            except requests.exceptions.ConnectionError:
                return False, "Cannot connect to Udemy API - check your internet connection"
            except requests.exceptions.RequestException as e:
                return False, f"Network error during Udemy authentication: {str(e)}"
            
        except Exception as e:
            return False, f"Unexpected error during Udemy authentication: {str(e)}"
    
    def get_real_enrolled_courses(self, email):
        """Get user's real enrolled courses from Udemy API"""
        try:
            integration_data = get_integration_data(st.session_state.user_id, 'udemy')
            if not integration_data or not integration_data.get('authenticated'):
                return False, "Not authenticated with Udemy"
            
            client_id = integration_data.get('client_id')
            client_secret = integration_data.get('client_secret')
            
            if not client_id or not client_secret:
                return False, "Missing Udemy API credentials"
            
            # Authenticate with Udemy API
            auth_url = f"{self.base_url}/oauth2/token/"
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            try:
                auth_response = requests.post(auth_url, data=auth_data)
                if auth_response.status_code != 200:
                    return False, f"Udemy authentication failed: {auth_response.status_code}"
                
                access_token = auth_response.json().get('access_token')
                if not access_token:
                    return False, "Failed to get Udemy access token"
                
            except requests.exceptions.RequestException as e:
                return False, f"Network error during Udemy authentication: {str(e)}"
            
            # Get user's enrolled courses using Udemy API
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            try:
                # Note: Udemy's public API has limitations for user-specific data
                # This endpoint may require additional permissions or may not be available
                courses_url = f"{self.base_url}/users/me/subscribed-courses/"
                courses_response = requests.get(courses_url, headers=headers)
                
                if courses_response.status_code == 200:
                    courses_data = courses_response.json()
                    courses = courses_data.get('results', [])
                    
                    # Process real course data
                    processed_courses = []
                    for course in courses:
                        processed_course = {
                            'id': course.get('id'),
                            'title': course.get('title'),
                            'instructor': course.get('visible_instructors', [{}])[0].get('display_name', 'Unknown'),
                            'category': course.get('primary_category', {}).get('title', 'General'),
                            'enrollment_date': course.get('created', ''),
                            'last_accessed': course.get('last_accessed_time', ''),
                            'total_lectures': course.get('num_lectures', 0),
                            'completed_lectures': course.get('num_completed_lectures', 0),
                            'total_duration_minutes': course.get('content_length_video', 0) // 60,
                            'progress_minutes': course.get('completion_time', 0) // 60,
                            'rating': course.get('avg_rating', 0),
                            'difficulty': course.get('instructional_level_simple', 'Beginner'),
                            'url': course.get('url', ''),
                            'image': course.get('image_240x135', '')
                        }
                        
                        # Calculate progress percentages
                        if processed_course['total_lectures'] > 0:
                            processed_course['progress_percentage'] = round(
                                (processed_course['completed_lectures'] / processed_course['total_lectures']) * 100, 1
                            )
                        else:
                            processed_course['progress_percentage'] = 0
                        
                        # Determine status based on real progress
                        if processed_course['progress_percentage'] >= 90:
                            processed_course['status'] = 'Completed'
                        elif processed_course['progress_percentage'] >= 50:
                            processed_course['status'] = 'In Progress'
                        elif processed_course['progress_percentage'] >= 10:
                            processed_course['status'] = 'Started'
                        else:
                            processed_course['status'] = 'Enrolled'
                        
                        processed_courses.append(processed_course)
                    
                    # Update integration data with real courses
                    integration_data['courses'] = processed_courses
                    integration_data['last_course_sync'] = datetime.now().isoformat()
                    save_integration_data(st.session_state.user_id, 'udemy', integration_data)
                    
                    return True, processed_courses
                
                elif courses_response.status_code == 403:
                    return False, "Access denied: Udemy API credentials may not have sufficient permissions for user course data"
                elif courses_response.status_code == 404:
                    return False, "Udemy user courses endpoint not found - may require different API access level"
                else:
                    return False, f"Failed to fetch courses from Udemy API: HTTP {courses_response.status_code}"
                    
            except requests.exceptions.RequestException as e:
                return False, f"Network error while fetching Udemy courses: {str(e)}"
            
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def get_detailed_analytics(self, email):
        """Get detailed learning analytics from Udemy data"""
        try:
            success, courses = self.get_real_enrolled_courses(email)
            if not success:
                return False, courses
            
            if not courses:
                return False, "No courses found"
            
            # Calculate comprehensive analytics
            total_courses = len(courses)
            completed_courses = len([c for c in courses if c['progress_percentage'] >= 90])
            in_progress_courses = len([c for c in courses if 10 <= c['progress_percentage'] < 90])
            not_started_courses = len([c for c in courses if c['progress_percentage'] < 10])
            
            total_time_enrolled = sum(c['total_duration_minutes'] for c in courses)
            total_time_completed = sum(c['progress_minutes'] for c in courses)
            
            avg_progress = sum(c['progress_percentage'] for c in courses) / total_courses
            avg_rating = sum(c['rating'] for c in courses) / total_courses
            
            # Category breakdown
            categories = {}
            for course in courses:
                cat = course['category']
                if cat not in categories:
                    categories[cat] = {'count': 0, 'avg_progress': 0, 'total_progress': 0}
                categories[cat]['count'] += 1
                categories[cat]['total_progress'] += course['progress_percentage']
            
            for cat in categories:
                categories[cat]['avg_progress'] = categories[cat]['total_progress'] / categories[cat]['count']
            
            # Learning streaks and patterns
            recent_activity = [c for c in courses 
                             if (datetime.now() - datetime.strptime(c['last_accessed'], '%Y-%m-%d')).days <= 7]
            
            analytics = {
                'total_courses': total_courses,
                'completed_courses': completed_courses,
                'in_progress_courses': in_progress_courses,
                'not_started_courses': not_started_courses,
                'completion_rate': round((completed_courses / total_courses) * 100, 1),
                'average_progress': round(avg_progress, 1),
                'average_rating': round(avg_rating, 1),
                'total_learning_hours': round(total_time_enrolled / 60, 1),
                'completed_learning_hours': round(total_time_completed / 60, 1),
                'categories': categories,
                'recent_activity_courses': len(recent_activity),
                'courses_needing_attention': [c for c in courses if c['progress_percentage'] < 30],
                'high_performing_courses': [c for c in courses if c['progress_percentage'] > 70],
                'last_updated': datetime.now().isoformat()
            }
            
            return True, analytics
            
        except Exception as e:
            return False, str(e)

def get_integration_status(user_id):
    """Get the status of all integrations for a user"""
    status = {}
    
    # Check each integration
    for platform in ['github', 'google_calendar', 'udemy']:
        data = get_integration_data(user_id, platform)
        status[platform] = {
            'connected': data is not None and data.get('authenticated', False),
            'last_sync': data.get('last_sync') if data else None
        }
    
    return status

def sync_all_integrations(user_id):
    """Sync data from all connected integrations"""
    results = {}
    
    # Get user email from session
    user_email = st.session_state.get('user_email', '')
    
    # GitHub sync
    github_data = get_integration_data(user_id, 'github')
    if github_data and github_data.get('authenticated'):
        github = GitHubIntegration()
        success, activity = github.get_real_time_activity(
            github_data['token'], 
            github_data['username']
        )
        results['github'] = {'success': success, 'data': activity if success else None}
    
    # Google Calendar sync
    calendar_data = get_integration_data(user_id, 'google_calendar')
    if calendar_data and calendar_data.get('authenticated'):
        calendar = GoogleCalendarIntegration()
        success, events = calendar.get_upcoming_events()
        results['google_calendar'] = {'success': success, 'data': events if success else None}
    
    # Udemy sync
    udemy_data = get_integration_data(user_id, 'udemy')
    if udemy_data and udemy_data.get('authenticated'):
        udemy = UdemyIntegration()
        success, analytics = udemy.get_detailed_analytics(user_email)
        results['udemy'] = {'success': success, 'data': analytics if success else None}
    
    return results

def get_user_learning_insights(user_id, user_email):
    """Get comprehensive learning insights from all connected platforms"""
    insights = {
        'github': None,
        'udemy': None,
        'calendar': None,
        'recommendations': [],
        'overall_score': 0
    }
    
    try:
        # GitHub insights
        github_data = get_integration_data(user_id, 'github')
        if github_data and github_data.get('authenticated'):
            github = GitHubIntegration()
            success, activity = github.get_real_time_activity(
                github_data['token'], 
                github_data['username']
            )
            if success:
                insights['github'] = {
                    'total_commits': activity['total_commits'],
                    'active_repos': len(activity['active_repos']),
                    'languages': list(activity['languages_used'].keys()),
                    'recent_activity': activity['recent_commits'][:5]
                }
        
        # Udemy insights
        udemy_data = get_integration_data(user_id, 'udemy')
        if udemy_data and udemy_data.get('authenticated'):
            udemy = UdemyIntegration()
            success, analytics = udemy.get_detailed_analytics(user_email)
            if success:
                insights['udemy'] = {
                    'completion_rate': analytics['completion_rate'],
                    'total_courses': analytics['total_courses'],
                    'learning_hours': analytics['completed_learning_hours'],
                    'categories': list(analytics['categories'].keys())
                }
        
        # Generate AI-powered recommendations
        recommendations = []
        
        if insights['github'] and insights['udemy']:
            github_languages = set(insights['github']['languages'])
            udemy_categories = set(insights['udemy']['categories'])
            
            # Cross-platform recommendations
            if 'Python' in github_languages and 'Data Science' not in udemy_categories:
                recommendations.append({
                    'type': 'course_suggestion',
                    'title': 'Complete a Data Science course',
                    'reason': 'You are active in Python - perfect for Data Science!'
                })
            
            if insights['github']['total_commits'] > 50 and 'DevOps' not in udemy_categories:
                recommendations.append({
                    'type': 'skill_development',
                    'title': 'Learn DevOps and CI/CD',
                    'reason': 'Your high coding activity suggests you\'d benefit from DevOps skills'
                })
        
        elif insights['udemy'] and not insights['github']:
            recommendations.append({
                'type': 'platform_integration',
                'title': 'Connect your GitHub account',
                'reason': 'Track your coding progress alongside your courses'
            })
        
        elif insights['github'] and not insights['udemy']:
            recommendations.append({
                'type': 'learning_enhancement',
                'title': 'Add structured learning with online courses',
                'reason': 'Complement your coding with formal education'
            })
        
        insights['recommendations'] = recommendations
        
        # Calculate overall learning score
        score = 0
        if insights['github']:
            score += min(insights['github']['total_commits'] / 10, 30)  # Max 30 points
            score += len(insights['github']['languages']) * 5  # 5 points per language
        
        if insights['udemy']:
            score += insights['udemy']['completion_rate'] / 2  # Max 50 points
            score += len(insights['udemy']['categories']) * 3  # 3 points per category
        
        insights['overall_score'] = min(round(score), 100)
        
        return True, insights
        
    except Exception as e:
        return False, str(e)