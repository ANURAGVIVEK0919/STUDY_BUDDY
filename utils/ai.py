import streamlit as st
from groq import Groq
import json
import re
from utils.db import get_remediation_resources

def generate_plan_with_groq(subject, learning_goal, current_level, time_commitment, additional_context=""):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        # FIX: Remove curly braces from f-string, keep prompt text unchanged
        prompt = """Create a study plan for Of course. Based on our detailed discussion, here is a comprehensive and effective prompt tailored to guide your LLM. This prompt synthesizes our objectives, challenges, and specific requirements into a single set of instructions.

## Master Prompt for Your AI Learning Platform
You are an expert curriculum designer and learning coach. Your primary task is to generate a personalized, adaptive learning plan for a student based on their stated goal. The entire response must be in Markdown format.

Your first step is to analyze the user's goal to determine if it is a broad topic or a specific topic.

### 1. Broad Topics (Generate a "Roadmap")
If the user's goal is a broad, complex subject that requires multiple study sessions (e.g., "Learn Python for data science," "Master Machine Learning," "Understand full-stack web development"), generate a comprehensive, week-by-week "Roadmap."

Roadmap Requirements:

Structure: The plan must be broken down week-by-week.

Content (for each week):

A clear module title.

3-5 specific, actionable sub-topics.

A practical mini-project or exercise for the end of the week to apply the learned concepts.

Resources (for each sub-topic):

You must provide one link to a high-quality, reputable article or piece of documentation. The link must be a valid, clickable hyperlink.

You must provide one specific, searchable video title and the channel name. Do not provide the URL. For example: Video Title: Python for Everybody - Full University Python Course by freeCodeCamp.org.

### 2. Specific Topics (Generate a "Deep Dive")
If the user's goal is a specific, smaller concept that can be mastered in a single session (e.g., "Understand JavaScript Promises," "Learn CSS Flexbox," "How does a SQL JOIN work?"), generate a concentrated, single-page "Deep Dive" plan.

Deep Dive Requirements:

Structure: Do not use a weekly format. The plan must include the following sections:

Core Concepts: A bulleted list breaking down the key components of the topic.

Curated Resources: This section must include:

A link to the single best article or documentation page.

A specific, searchable video title and channel name.

Practical Challenge: A small, specific coding problem or task to solidify understanding.

Common Pitfalls: A list of 2-3 common mistakes or misunderstandings that beginners often encounter with this topic."""
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        
        try:
            plan_data = json.loads(content)
            # Add resource links if missing
            remediation = get_remediation_resources(subject)
            if remediation:
                plan_data.setdefault('resources', [])
                plan_data['resources'].extend([
                    {
                        "type": "video",
                        "title": f"YouTube Tutorials for {subject}",
                        "url": remediation['video_url']
                    },
                    {
                        "type": "article",
                        "title": f"Comprehensive Guides for {subject}",
                        "url": remediation['article_url']
                    },
                    {
                        "type": "practice",
                        "title": f"Practice Exercises for {subject}",
                        "url": remediation['practice_url']
                    }
                ])
            return True, plan_data
        except:
            remediation = get_remediation_resources(subject)
            return True, {
                "title": f"Study Plan: {subject}",
                "overview": content,
                "duration": time_commitment,
                "difficulty": current_level,
                "modules": [],
                "milestones": [],
                "resources": [
                    {
                        "type": "video",
                        "title": f"YouTube Tutorials for {subject}",
                        "url": remediation['video_url'] if remediation else ""
                    },
                    {
                        "type": "article",
                        "title": f"Comprehensive Guides for {subject}",
                        "url": remediation['article_url'] if remediation else ""
                    },
                    {
                        "type": "practice",
                        "title": f"Practice Exercises for {subject}",
                        "url": remediation['practice_url'] if remediation else ""
                    }
                ],
                "tips": []
            }
    except Exception as e:
        return False, str(e)

def generate_quiz_with_groq(subject, difficulty, num_questions=5):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        
        prompt = f"""Create a {difficulty} quiz about {subject} with {num_questions} questions. Return JSON format."""
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        quiz_data = json.loads(content)
        return True, quiz_data
        
    except Exception as e:
        return False, str(e)