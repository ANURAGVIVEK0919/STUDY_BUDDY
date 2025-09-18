# utils/db.py

import streamlit as st
from firebase_admin import firestore
from datetime import datetime, timedelta
from collections import defaultdict
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def save_plan_to_firestore(user_id, goal, plan_content):
    """Save study plan to Firestore"""
    try:
        db = firestore.client()
        plan_data = {
            'goal': goal,
            'content': plan_content,
            'created_at': firestore.SERVER_TIMESTAMP,
            'completed': False
        }
        
        db.collection('users').document(user_id).collection('plans').add(plan_data)
        return True
    except Exception as e:
        st.error(f"Error saving plan: {e}")
        return False

def get_user_plans(user_id):
    """Get all user's study plans"""
    try:
        db = firestore.client()
        plans_ref = db.collection('users').document(user_id).collection('plans')
        plans = plans_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        plan_list = []
        for plan in plans:
            plan_data = plan.to_dict()
            plan_data['id'] = plan.id
            plan_list.append(plan_data)
        
        return plan_list
    except Exception as e:
        st.error(f"Error fetching plans: {e}")
        return []

def save_quiz_score(user_id, topic, score, total_questions):
    """Save quiz score to Firestore"""
    try:
        db = firestore.client()
        score_data = {
            'topic': topic,
            'score': score,
            'total_questions': total_questions,
            'percentage': (score / total_questions) * 100,
            'completed_at': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('users').document(user_id).collection('quiz_scores').add(score_data)
        return True
    except Exception as e:
        st.error(f"Error saving quiz score: {e}")
        return False

def delete_plan_from_firestore(user_id, plan_id):
    """Delete a study plan from Firestore"""
    try:
        db = firestore.client()
        db.collection('users').document(user_id).collection('plans').document(plan_id).delete()
        return True
    except Exception as e:
        st.error(f"Error deleting plan: {e}")
        return False

def get_user_analytics(user_id):
    """Get comprehensive user analytics data"""
    try:
        db = firestore.client()
        
        # Get quiz scores
        scores_ref = db.collection('users').document(user_id).collection('quiz_scores')
        scores = scores_ref.order_by('completed_at', direction=firestore.Query.DESCENDING).stream()
        
        analytics_data = {
            'total_quizzes': 0,
            'average_score': 0,
            'topics_studied': set(),
            'quiz_history': [],
            'best_topic': None,
            'worst_topic': None,
            'current_streak': 0
        }
        
        quiz_list = []
        for score in scores:
            score_data = score.to_dict()
            quiz_list.append(score_data)
            analytics_data['topics_studied'].add(score_data.get('topic', 'Unknown'))
        
        if quiz_list:
            analytics_data['total_quizzes'] = len(quiz_list)
            analytics_data['average_score'] = sum(q.get('percentage', 0) for q in quiz_list) / len(quiz_list)
            analytics_data['quiz_history'] = quiz_list
            
            # Calculate best and worst topics
            topic_scores = defaultdict(list)
            for quiz in quiz_list:
                topic_scores[quiz.get('topic', 'Unknown')].append(quiz.get('percentage', 0))
            
            topic_averages = {topic: sum(scores)/len(scores) for topic, scores in topic_scores.items()}
            analytics_data['best_topic'] = max(topic_averages, key=topic_averages.get) if topic_averages else None
            analytics_data['worst_topic'] = min(topic_averages, key=topic_averages.get) if topic_averages else None
        
        analytics_data['topics_studied'] = list(analytics_data['topics_studied'])
        return analytics_data
        
    except Exception as e:
        st.error(f"Error fetching analytics: {e}")
        return None

def get_user_quiz_history(user_id, limit=50):
    """Get detailed quiz history for analytics"""
    try:
        db = firestore.client()
        scores_ref = db.collection('users').document(user_id).collection('quiz_scores')
        scores = scores_ref.order_by('completed_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        history = []
        for score in scores:
            score_data = score.to_dict()
            # Convert Firestore timestamp to datetime if needed
            if 'completed_at' in score_data and score_data['completed_at']:
                score_data['completed_at'] = score_data['completed_at']
            history.append(score_data)
        
        return history
    except Exception as e:
        st.error(f"Error fetching quiz history: {e}")
        return []

def get_learning_streak(user_id):
    """Calculate user's current learning streak"""
    try:
        db = firestore.client()
        scores_ref = db.collection('users').document(user_id).collection('quiz_scores')
        
        # Get recent quiz dates
        recent_scores = scores_ref.order_by('completed_at', direction=firestore.Query.DESCENDING).limit(30).stream()
        
        quiz_dates = []
        for score in recent_scores:
            score_data = score.to_dict()
            if 'completed_at' in score_data and score_data['completed_at']:
                quiz_date = score_data['completed_at'].date()
                if quiz_date not in quiz_dates:
                    quiz_dates.append(quiz_date)
        
        if not quiz_dates:
            return 0
        
        # Calculate streak
        quiz_dates.sort(reverse=True)
        current_streak = 0
        expected_date = datetime.now().date()
        
        for quiz_date in quiz_dates:
            if quiz_date == expected_date or quiz_date == expected_date - timedelta(days=1):
                current_streak += 1
                expected_date = quiz_date - timedelta(days=1)
            else:
                break
        
        return current_streak
        
    except Exception as e:
        st.error(f"Error calculating streak: {e}")
        return 0

def get_topic_performance(user_id):
    """Get performance breakdown by topic"""
    try:
        db = firestore.client()
        scores_ref = db.collection('users').document(user_id).collection('quiz_scores')
        scores = scores_ref.stream()
        
        topic_data = {}
        for score in scores:
            score_data = score.to_dict()
            topic = score_data.get('topic', 'Unknown')
            percentage = score_data.get('percentage', 0)
            
            if topic not in topic_data:
                topic_data[topic] = {'scores': [], 'total_quizzes': 0}
            
            topic_data[topic]['scores'].append(percentage)
            topic_data[topic]['total_quizzes'] += 1
        
        # Calculate averages
        for topic in topic_data:
            scores = topic_data[topic]['scores']
            topic_data[topic]['average_score'] = sum(scores) / len(scores) if scores else 0
            topic_data[topic]['best_score'] = max(scores) if scores else 0
            topic_data[topic]['worst_score'] = min(scores) if scores else 0
        
        return topic_data
        
    except Exception as e:
        st.error(f"Error fetching topic performance: {e}")
        return {}

def get_remediation_resources(topic):
    """Get remediation resources for a specific topic"""
    try:
        # For now, return generic resources based on topic
        # You can expand this to store and retrieve specific resources from Firestore
        topic_clean = topic.replace(' ', '+')
        
        return {
            'video_url': f"https://www.youtube.com/results?search_query={topic_clean}+tutorial",
            'article_url': f"https://www.google.com/search?q={topic_clean}+comprehensive+guide",
            'practice_url': f"https://www.google.com/search?q={topic_clean}+practice+exercises",
            'description': f"Additional learning resources for {topic}"
        }
    except Exception as e:
        st.error(f"Error fetching resources: {e}")
        return None

def get_study_recommendations(user_id):
    """Get personalized study recommendations based on performance"""
    try:
        analytics = get_user_analytics(user_id)
        if not analytics:
            return []
        
        recommendations = []
        
        # Recommendation based on average score
        avg_score = analytics.get('average_score', 0)
        if avg_score < 60:
            recommendations.append({
                'type': 'improvement',
                'title': 'Focus on Fundamentals',
                'description': 'Your average score suggests reviewing basic concepts before advancing.',
                'action': 'Review study materials and retake quizzes'
            })
        elif avg_score >= 80:
            recommendations.append({
                'type': 'advancement',
                'title': 'Ready for Advanced Topics',
                'description': 'Excellent performance! Consider exploring more challenging subjects.',
                'action': 'Create study plans for advanced topics'
            })
        
        # Recommendation based on worst topic
        worst_topic = analytics.get('worst_topic')
        if worst_topic:
            recommendations.append({
                'type': 'focus_area',
                'title': f'Improve {worst_topic}',
                'description': f'{worst_topic} appears to be your weakest area.',
                'action': f'Take more quizzes on {worst_topic} and review related materials'
            })
        
        return recommendations
        
    except Exception as e:
        st.error(f"Error generating recommendations: {e}")
        return []

def update_plan_progress(user_id, plan_id, progress_data):
    """Update progress on a specific study plan"""
    try:
        db = firestore.client()
        plan_ref = db.collection('users').document(user_id).collection('plans').document(plan_id)
        
        plan_ref.update({
            'progress': progress_data,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        
        return True
    except Exception as e:
        st.error(f"Error updating plan progress: {e}")
        return False

def get_dashboard_summary(user_id):
    """Get summary data for dashboard display"""
    try:
        db = firestore.client()
        
        # Get recent quiz performance
        recent_scores = db.collection('users').document(user_id).collection('quiz_scores')\
                         .order_by('completed_at', direction=firestore.Query.DESCENDING)\
                         .limit(5).stream()
        
        recent_performance = []
        for score in recent_scores:
            score_data = score.to_dict()
            recent_performance.append({
                'topic': score_data.get('topic', 'Unknown'),
                'percentage': score_data.get('percentage', 0),
                'date': score_data.get('completed_at')
            })
        
        # Get total stats
        all_scores = db.collection('users').document(user_id).collection('quiz_scores').stream()
        total_quizzes = 0
        total_percentage = 0
        
        for score in all_scores:
            score_data = score.to_dict()
            total_quizzes += 1
            total_percentage += score_data.get('percentage', 0)
        
        average_performance = total_percentage / total_quizzes if total_quizzes > 0 else 0
        
        return {
            'total_quizzes': total_quizzes,
            'average_performance': average_performance,
            'recent_performance': recent_performance,
            'learning_streak': get_learning_streak(user_id)
        }
        
    except Exception as e:
        st.error(f"Error fetching dashboard summary: {e}")
        return None

def save_integration_data(user_id, platform, data):
    """Save integration data for a user"""
    try:
        db = firestore.client()
        integration_ref = db.collection('integrations').document(f"{user_id}_{platform}")
        data['updated_at'] = datetime.now()
        integration_ref.set(data)
        return True
    except Exception as e:
        print(f"Error saving integration data: {e}")
        return False

def get_integration_data(user_id, platform):
    """Get integration data for a user and platform"""
    try:
        db = firestore.client()
        integration_ref = db.collection('integrations').document(f"{user_id}_{platform}")
        doc = integration_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting integration data: {e}")
        return None

def delete_integration_data(user_id, platform):
    """Delete integration data for a user and platform"""
    try:
        db = firestore.client()
        integration_ref = db.collection('integrations').document(f"{user_id}_{platform}")
        integration_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting integration data: {e}")
        return False

def generate_analytics_pdf(user_id, user_name, user_email=None):
    """Generate a PDF report of user's learning analytics"""
    try:
        # Get user data
        analytics = get_user_analytics(user_id)
        quiz_history = get_user_quiz_history(user_id, limit=50)
        user_plans = get_user_plans(user_id)
        
        if not analytics or not quiz_history:
            return None, "No data available for PDF generation"
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Title
        story.append(Paragraph("🎓 AI Learning Coach - Progress Report", title_style))
        story.append(Spacer(1, 20))
        
        # Header Info
        header_data = [
            ['Student Name:', user_name],
            ['Student Email:', user_email or 'Not provided'],
            ['Report Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Total Quizzes:', str(analytics['total_quizzes'])],
            ['Average Score:', f"{analytics['average_score']:.1f}%"]
        ]
        
        header_table = Table(header_data, colWidths=[2*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # Learning Summary
        story.append(Paragraph("📈 Learning Summary", heading_style))
        
        # Calculate additional metrics
        import pandas as pd
        df_quizzes = pd.DataFrame(quiz_history)
        if not df_quizzes.empty:
            passed_quizzes = len(df_quizzes[df_quizzes['percentage'] >= 60])
            pass_rate = (passed_quizzes / len(quiz_history) * 100)
            unique_topics = df_quizzes['topic'].nunique()
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Quizzes Taken', str(analytics['total_quizzes'])],
                ['Average Performance', f"{analytics['average_score']:.1f}%"],
                ['Pass Rate (≥60%)', f"{pass_rate:.1f}%"],
                ['Unique Topics Studied', str(unique_topics)],
                ['Best Topic', analytics.get('best_topic', 'N/A')],
                ['Areas for Improvement', analytics.get('worst_topic', 'N/A')]
            ]
            
            summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
        
        # Topic Performance
        story.append(Paragraph("📚 Performance by Topic", heading_style))
        
        if not df_quizzes.empty:
            topic_performance = df_quizzes.groupby('topic').agg({
                'percentage': ['mean', 'count', 'max', 'min']
            }).round(1)
            
            topic_data = [['Topic', 'Avg Score', 'Quizzes', 'Best', 'Worst']]
            
            for topic in topic_performance.index:
                avg_score = topic_performance.loc[topic, ('percentage', 'mean')]
                quiz_count = int(topic_performance.loc[topic, ('percentage', 'count')])
                best_score = topic_performance.loc[topic, ('percentage', 'max')]
                worst_score = topic_performance.loc[topic, ('percentage', 'min')]
                
                topic_data.append([
                    topic[:25] + "..." if len(topic) > 25 else topic,
                    f"{avg_score:.1f}%",
                    str(quiz_count),
                    f"{best_score:.1f}%",
                    f"{worst_score:.1f}%"
                ])
            
            topic_table = Table(topic_data, colWidths=[2*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            topic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(topic_table)
            story.append(Spacer(1, 20))
        
        # Study Plans
        if user_plans:
            story.append(Paragraph("📋 Study Plans", heading_style))
            
            for i, plan in enumerate(user_plans[:3]):  # Show first 3 plans
                plan_title = plan.get('goal', 'Untitled Plan')
                created_date = plan.get('created_at')
                date_str = created_date.strftime('%B %d, %Y') if created_date and hasattr(created_date, 'strftime') else 'Recently'
                
                story.append(Paragraph(f"<b>{i+1}. {plan_title}</b>", styles['Normal']))
                story.append(Paragraph(f"Created: {date_str}", styles['Normal']))
                story.append(Spacer(1, 10))
        
        # Recommendations
        story.append(Paragraph("🎯 Personalized Recommendations", heading_style))
        
        recommendations = []
        if not df_quizzes.empty:
            avg_score = df_quizzes['percentage'].mean()
            
            if avg_score >= 80:
                recommendations.append("🌟 Excellent performance! You're ready for advanced topics.")
            elif avg_score >= 60:
                recommendations.append("✅ Good progress! Focus on improving weak areas.")
            else:
                recommendations.append("📚 Consider reviewing fundamentals before advancing.")
            
            if analytics.get('worst_topic'):
                recommendations.append(f"🎯 Focus more practice on: {analytics['worst_topic']}")
            
            if len(quiz_history) >= 10:
                recommendations.append("🚀 Great consistency! Keep up the regular practice.")
        
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", styles['Normal']))
            story.append(Spacer(1, 8))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Generated by AI Learning Coach", styles['Normal']))
        story.append(Paragraph("Continue your learning journey at your dashboard!", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data, None
        
    except Exception as e:
        return None, f"Error generating PDF: {str(e)}"