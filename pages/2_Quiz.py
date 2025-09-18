import streamlit as st
import json
from utils.ai import generate_quiz_with_groq
from utils.db import save_quiz_score, get_remediation_resources

st.set_page_config(page_title="Quiz - AI Learning Coach", page_icon="🧠")

if not st.session_state.get('logged_in', False):
    st.error("Please login first")
    st.stop()

st.title("🧠 Knowledge Quiz")

# Quiz configuration
col1, col2 = st.columns(2)

with col1:
    # Get topic from Dashboard or allow manual input
    if 'current_quiz_topic' in st.session_state:
        topic = st.text_input("Quiz Topic:", value=st.session_state['current_quiz_topic'])
    else:
        topic = st.text_input("Enter a topic for your quiz:", placeholder="e.g., Python basics, Machine Learning")

with col2:
    difficulty = st.selectbox("Difficulty Level:", ["Beginner", "Intermediate", "Advanced"])
    num_questions = st.slider("Number of Questions:", 3, 10, 5)

if st.button("Generate Quiz", type="primary") and topic:
    with st.spinner("Generating quiz questions..."):
        success, quiz_data = generate_quiz_with_groq(topic, difficulty, num_questions)
        if success:
            # Store the quiz data in session state
            st.session_state['current_quiz'] = quiz_data
            st.session_state['quiz_answers'] = {}
            st.success("✅ Quiz generated successfully!")
            st.rerun()
        else:
            st.error(f"Failed to generate quiz: {quiz_data}")

# Display quiz if available
if 'current_quiz' in st.session_state:
    quiz_data = st.session_state['current_quiz']
    
    st.markdown("---")
    st.markdown(f"### 📝 {quiz_data.get('title', 'Quiz')}")
    st.markdown(f"**Subject:** {quiz_data.get('subject', topic)}")
    st.markdown(f"**Difficulty:** {quiz_data.get('difficulty', difficulty)}")
    
    questions = quiz_data.get('questions', [])
    
    if questions:
        user_answers = {}
        
        # Display questions
        for i, q in enumerate(questions):
            st.markdown(f"**Question {i+1}:** {q['question']}")
            
            # Get user's answer
            answer_index = st.radio(
                "Select your answer:",
                range(len(q['options'])),
                format_func=lambda x: q['options'][x],
                key=f"q_{i}"
            )
            user_answers[i] = answer_index
            st.markdown("---")
        
        # Submit quiz
        if st.button("Submit Quiz", type="primary"):
            score = 0
            results = []
            
            # Calculate score and collect results
            for i, q in enumerate(questions):
                user_answer = user_answers[i]
                correct_answer = q['correct_answer']
                is_correct = user_answer == correct_answer
                
                if is_correct:
                    score += 1
                
                results.append({
                    'question': q['question'],
                    'user_answer': q['options'][user_answer],
                    'correct_answer': q['options'][correct_answer],
                    'is_correct': is_correct,
                    'explanation': q.get('explanation', 'No explanation provided')
                })
            
            # Save score to database
            percentage = (score / len(questions)) * 100
            save_quiz_score(
                st.session_state['user_id'], 
                quiz_data.get('subject', topic), 
                score, 
                len(questions)
            )
            
            # Display results
            st.markdown("---")
            st.markdown("### 📊 Quiz Results")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{score}/{len(questions)}")
            with col2:
                st.metric("Percentage", f"{percentage:.1f}%")
            with col3:
                if percentage >= 80:
                    st.success("🌟 Excellent!")
                elif percentage >= 60:
                    st.info("✅ Good job!")
                else:
                    st.warning("📚 Keep studying!")
            
            # Show detailed results
            st.markdown("### 📝 Detailed Results")
            for i, result in enumerate(results):
                with st.expander(f"Question {i+1} - {'✅ Correct' if result['is_correct'] else '❌ Incorrect'}"):
                    st.write(f"**Question:** {result['question']}")
                    st.write(f"**Your Answer:** {result['user_answer']}")
                    st.write(f"**Correct Answer:** {result['correct_answer']}")
                    st.write(f"**Explanation:** {result['explanation']}")
            
            # Clear quiz from session
            if st.button("Take Another Quiz"):
                st.session_state.pop('current_quiz', None)
                st.session_state.pop('current_quiz_topic', None)
                st.rerun()

# Navigation
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("🏠 Back to Dashboard"):
        st.switch_page("pages/1_Dashboard.py")
with col2:
    if st.button("📊 View Analytics"):
        st.switch_page("pages/3_Analytics.py")
        
        # Calculate percentage
        percentage = (score / len(questions)) * 100
        st.balloons()
        st.markdown(f"### 🎯 Results: {score}/{len(questions)} ({percentage:.1f}%)")
        
        # --- STEP 8: RULE-BASED FEEDBACK SYSTEM ---
        st.markdown("---")
        st.subheader("📚 Personalized Learning Recommendations")
        
        if percentage < 60:
            # Low score: Recommend reviewing the entire topic
            st.error("📖 **Review Recommendation**")
            st.markdown(f"""
            Your score indicates you might benefit from reviewing **{st.session_state['quiz_topic']}** more thoroughly.
            
            **Suggested Action Plan:**
            1. 📺 Watch foundational videos on this topic
            2. 📄 Read comprehensive articles 
            3. 💡 Practice with simpler exercises
            4. 🔄 Retake this quiz after studying
            """)
            
            # General topic resources
            st.markdown("### 🎯 Recommended Resources:")
            topic_clean = st.session_state['quiz_topic'].replace(' ', '+')
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**📺 Video Tutorial:**")
                st.markdown(f"[YouTube: {st.session_state['quiz_topic']} Tutorial](https://www.youtube.com/results?search_query={topic_clean}+tutorial)")
            
            with col2:
                st.markdown(f"**📄 Article:**")
                st.markdown(f"[Google: {st.session_state['quiz_topic']} Guide](https://www.google.com/search?q={topic_clean}+comprehensive+guide)")
                
        else:
            # Good score: Provide targeted remediation for specific wrong answers
            st.success("🎉 **Great Job!** You passed the quiz!")
            
            if incorrect_tags:
                st.markdown("### 🎯 Targeted Improvement Areas:")
                st.info("Here are specific resources for the topics you missed:")
                
                # Remove duplicates from incorrect_tags
                unique_tags = list(set(incorrect_tags))
                
                for tag in unique_tags:
                    with st.expander(f"📚 Resources for: {tag.replace('_', ' ').title()}"):
                        
                        # Generate specific resources for this tag
                        tag_topic = f"{st.session_state['quiz_topic']} {tag.replace('_', ' ')}"
                        tag_clean = tag_topic.replace(' ', '+')
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**📺 Focused Video:**")
                            st.markdown(f"[YouTube: {tag_topic}](https://www.youtube.com/results?search_query={tag_clean}+explained)")
                        
                        with col2:
                            st.markdown("**📄 Detailed Article:**")
                            st.markdown(f"[Google: {tag_topic}](https://www.google.com/search?q={tag_clean}+detailed+explanation)")
                        
                        # Practical suggestion
                        st.markdown(f"💡 **Quick Tip:** Focus on understanding {tag.replace('_', ' ')} concepts before moving forward.")
            else:
                st.success("🌟 **Perfect!** You got all questions right! You're ready for more advanced topics.")
        
        # Show detailed review
        st.markdown("---")
        st.subheader("📋 Detailed Review:")
        for i, q in enumerate(questions):
            if user_answers[i] == q['correct_answer']:
                st.success(f"**Q{i+1}:** ✅ Correct! ({q['correct_answer']})")
            else:
                st.error(f"**Q{i+1}:** ❌ Your answer: {user_answers[i]}, Correct: {q['correct_answer']}")
                st.info(f"📝 **Topic:** {q.get('tag', 'general').replace('_', ' ').title()}")

# Navigation
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Dashboard"):
        st.session_state['page'] = 'dashboard'
        if 'current_quiz_topic' in st.session_state:
            del st.session_state['current_quiz_topic']
        st.switch_page("pages/1_Dashboard.py")

with col2:
    if st.button("🔄 New Quiz"):
        if 'current_quiz' in st.session_state:
            del st.session_state['current_quiz']
        if 'current_quiz_topic' in st.session_state:
            del st.session_state['current_quiz_topic']
        st.rerun()