import os
import streamlit as st
import json
import requests
import re
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="CareerGuide AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
    }

    .title-gradient {
        background: -webkit-linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 3.5rem;
        padding-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #9ca3af;
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #1f2937 !important;
        border-radius: 16px !important;
        padding: 0.5rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        border: 1px solid #374151 !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease, border 0.3s ease !important;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 8px 30px rgba(139, 92, 246, 0.2) !important;
        border: 1px solid #6366f1 !important;
    }
    
    .skill-badge {
        background: rgba(99, 102, 241, 0.1);
        color: #a5b4fc;
        border: 1px solid #4f46e5;
        padding: 0.4rem 1rem;
        border-radius: 30px;
        display: inline-block;
        margin: 0.3rem 0.3rem 0.3rem 0;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .gap-badge {
        background: rgba(239, 68, 68, 0.1);
        color: #fca5a5;
        border: 1px solid #ef4444;
        padding: 0.4rem 1rem;
        border-radius: 30px;
        display: inline-block;
        margin: 0.3rem 0.3rem 0.3rem 0;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .timeline-item {
        border-left: 3px solid #6366f1;
        padding: 0 0 2rem 2rem;
        position: relative;
        margin-left: 1rem;
        color: #e5e7eb;
    }
    
    .timeline-item::before {
        content: '';
        position: absolute;
        left: -11px;
        top: 0;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #8b5cf6;
        border: 4px solid #0b0f19;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(139, 92, 246, 0.4) !important;
    }
    
    [data-testid="stSidebar"] {
        background: #0b0f19;
        border-right: 1px solid #1f2937;
    }
    
    * {
        color: #f3f4f6;
    }
</style>
""", unsafe_allow_html=True)

class GroqAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def chat_completion(self, messages, model="llama-3.3-70b-versatile", temperature=0.7, max_tokens=6000):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 1,
            "stream": False
        }
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=40)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"Network Error: {str(e)}")
            return None

@st.cache_resource
def init_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try: api_key = st.secrets["GROQ_API_KEY"]
        except: pass
    if not api_key:
        st.error("Groq API key not found.")
        return None
    return GroqAPIClient(api_key)

def init_session_state():
    defaults = {
        'user_data': {'interests': [], 'skills': [], 'favorite_subjects': [], 'career_goals': ''},
        'career_recommendations': None, 'skill_gap_analysis': None,
        'learning_roadmap': None, 'resume_suggestions': None,
        'interview_prep': None, 'projects': None, 'cover_letter': None,
        'current_tab': "User Input", 'chat_history': [], 'selected_career': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def get_career_recommendations_prompt(interests, skills, subjects, goals):
    return f"""Analyze this profile deeply and recommend 3 highly specific career paths:
Interests: {', '.join(interests)}
Skills: {', '.join(skills)}
Subjects: {', '.join(subjects)}
Goals: {goals}

Format exactly as JSON:
{{
    "careers": [
        {{
            "title": "Exact Job Title",
            "description": "A deep 3-sentence description of what this job actually does daily.",
            "match_percentage": 85,
            "required_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
            "salary_range": "$X - $Y",
            "growth_potential": "Detailed market outlook",
            "day_in_the_life": "What a typical Tuesday looks like in this role"
        }}
    ]
}}"""

def get_skill_gap_prompt(user_skills, career_requirements):
    return f"""Perform a comprehensive skill gap analysis:
User Skills: {', '.join(user_skills)}
Career Requirements: {', '.join(career_requirements)}

Format exactly as JSON:
{{
    "matching_skills": ["skill1"],
    "missing_skills": [
        {{"skill": "Name", "priority": "High", "estimated_time": "X weeks", "reason": "Why this is critical"}}
    ]
}}"""

def get_learning_roadmap_prompt(missing_skills, career_title):
    skills_list = [skill['skill'] if isinstance(skill, dict) else skill for skill in missing_skills]
    return f"""Create a highly detailed 6-month learning roadmap for a {career_title}.
Target skills: {', '.join(skills_list)}

Format exactly as JSON:
{{
    "roadmap": [
        {{
            "month": 1,
            "title": "Phase Title",
            "objectives": ["Deep obj 1", "Deep obj 2", "Deep obj 3"],
            "resources": ["Specific book/course 1", "Specific book/course 2"],
            "projects": ["Exact project to build"]
        }}
    ]
}}"""

def get_project_ideas_prompt(career_title, missing_skills):
    skills_list = [skill['skill'] if isinstance(skill, dict) else skill for skill in missing_skills]
    return f"""Create 3 portfolio project ideas for a {career_title} to practice these skills: {', '.join(skills_list)}.

Format exactly as JSON:
{{
    "projects": [
        {{
            "title": "Project Name",
            "difficulty": "Beginner/Intermediate/Advanced",
            "description": "Detailed explanation of what to build and why it looks good on a resume",
            "features": ["Feature 1", "Feature 2", "Feature 3"],
            "tech_stack": ["Tech 1", "Tech 2"]
        }}
    ]
}}"""

def get_interview_prep_prompt(career_title, required_skills):
    return f"""Create deep interview prep for a {career_title} position. Required: {', '.join(required_skills)}
Format exactly as JSON:
{{
    "technical_questions": [{{"question": "Complex Q1", "answer": "Detailed A1"}}],
    "behavioral_questions": [{{"question": "Situation Q", "answer": "STAR method A"}}],
    "tips": "Advanced interview strategies"
}}"""

def get_cover_letter_prompt(career_title, user_skills):
    return f"""Write a professional, modern cover letter for a {career_title} role using these skills: {', '.join(user_skills)}. Do not use placeholders for the user's name, just write the body.

Format exactly as JSON:
{{
    "cover_letter_body": "The full text of the cover letter separated by paragraphs."
}}"""

def call_groq_api(prompt, response_format="json"):
    client = init_groq_client()
    if not client: return None
    
    sys_msg = "You are an expert career counselor. Always respond with valid JSON." if response_format == "json" else "You are an expert career counselor. Reply in simple, conversational plain text. Do not use JSON."
    
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": prompt}
    ]
    response = client.chat_completion(messages)
    if not response: return None
    
    content = response['choices'][0]['message']['content'].strip()
    if response_format == "json":
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        try: return json.loads(content)
        except:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try: return json.loads(match.group())
                except: pass
            return {"raw_response": content}
    return content

def sidebar_navigation():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px; padding-top: 20px;">
            <h1 style="font-size: 2rem; margin-bottom: 5px; color: #a78bfa;">🎯 CareerGuide</h1>
            <p style="color: #9ca3af; font-size: 0.9rem; letter-spacing: 1px;">AI NAVIGATOR</p>
        </div>
        """, unsafe_allow_html=True)
        
        nav_options = {
            "📝 Profile Setup": "User Input",
            "💼 Career Paths": "Career Recommendations",
            "🔍 Skill Analysis": "Skill Gap Analysis",
            "🗺️ Journey Map": "Learning Roadmap",
            "🛠️ Project Ideas": "Project Ideas",
            "📄 Cover Letter": "Cover Letter",
            "🎤 Interview Prep": "Interview Prep",
            "💬 AI Mentor": "AI Chat Assistant"
        }
        
        for display, key in nav_options.items():
            if st.button(display, key=key):
                st.session_state.current_tab = key

def user_input_section():
    st.markdown('<h1 class="title-gradient">Design Your Future</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Tell us about yourself, and let AI map out your perfect career trajectory.</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.markdown("### 🧩 Your DNA")
            interests = st.text_area("Passions & Interests", placeholder="e.g., Coding, design, writing, data analysis...")
            skills = st.text_area("Current Toolkit", placeholder="e.g., Python, Figma, Project Management...")
    with col2:
        with st.container(border=True):
            st.markdown("### 🚀 Your Trajectory")
            subjects = st.text_area("Academic Strengths", placeholder="e.g., Mathematics, Psychology, Computer Science...")
            goals = st.text_area("Career Ambitions", placeholder="Where do you see yourself in 5 years?")
    
    col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 2, 1])
    with col_btn_2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✨ Discover My Path"):
            with st.spinner("🧠 Analyzing your unique profile..."):
                st.session_state.user_data = {
                    'interests': [i.strip() for i in interests.split(',')] if interests else [],
                    'skills': [s.strip() for s in skills.split(',')] if skills else [],
                    'favorite_subjects': [sub.strip() for sub in subjects.split(',')] if subjects else [],
                    'career_goals': goals
                }
                prompt = get_career_recommendations_prompt(
                    st.session_state.user_data['interests'],
                    st.session_state.user_data['skills'],
                    st.session_state.user_data['favorite_subjects'],
                    st.session_state.user_data['career_goals']
                )
                res = call_groq_api(prompt)
                if res and 'careers' in res:
                    st.session_state.career_recommendations = res
                    st.session_state.current_tab = "Career Recommendations"
                    st.rerun()

def career_recommendations_section():
    if not st.session_state.career_recommendations:
        st.warning("Please complete your Profile Setup first.")
        return
        
    st.markdown('<h1 class="title-gradient">Top Career Matches</h1>', unsafe_allow_html=True)
    
    careers = st.session_state.career_recommendations.get('careers', [])
    for idx, career in enumerate(careers):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"🎯 {career.get('title', 'Unknown Role')}")
                st.markdown(f"*{career.get('description', '')}*")
            with col2:
                st.markdown(f"**Match Compatibility: {career.get('match_percentage', 0)}%**")
                st.progress(int(career.get('match_percentage', 0)) / 100)
                
            st.markdown("---")
            st.markdown(f"**☕ Day in the Life:** {career.get('day_in_the_life', 'Information not available')}")
            st.markdown("---")
            
            scol1, scol2, scol3 = st.columns(3)
            with scol1:
                st.markdown("**💰 Salary Range**")
                st.info(career.get('salary_range', 'Varies'))
            with scol2:
                st.markdown("**📈 Market Outlook**")
                st.info(career.get('growth_potential', 'Varies'))
            with scol3:
                st.markdown("**🛠️ Key Requirements**")
                for skill in career.get('required_skills', [])[:4]:
                    st.markdown(f'<span class="skill-badge">{skill}</span>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"Generate Core Action Plan", key=f"btn_{idx}"):
                st.session_state.selected_career = career
                # Reset these so they generate fresh for a new career
                st.session_state.projects = None
                st.session_state.cover_letter = None
                st.session_state.interview_prep = None
                
                with st.status("🏗️ Building your core action plan...", expanded=True) as status:
                    st.write("Analyzing skill gaps...")
                    gap = call_groq_api(get_skill_gap_prompt(st.session_state.user_data['skills'], career.get('required_skills', [])))
                    st.session_state.skill_gap_analysis = {'career_title': career['title'], 'analysis': gap}
                    
                    missing = gap.get('missing_skills', []) if isinstance(gap, dict) else []
                    st.write("Plotting timeline...")
                    st.session_state.learning_roadmap = call_groq_api(get_learning_roadmap_prompt(missing, career['title']))
                    
                    status.update(label="Core Plan Complete! 🎉", state="complete", expanded=False)
                    
                st.session_state.current_tab = "Skill Gap Analysis"
                st.rerun()

def skill_gap_analysis_section():
    if not st.session_state.skill_gap_analysis:
        st.warning("Please select a career to analyze first.")
        return
        
    analysis = st.session_state.skill_gap_analysis
    st.markdown('<h1 class="title-gradient">Skill Gap Analysis</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">Target Role: <strong>{analysis.get("career_title")}</strong></p>', unsafe_allow_html=True)
    
    data = analysis.get('analysis', {})
    if not isinstance(data, dict): return
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown('### ✅ Strengths to Leverage')
            for skill in data.get('matching_skills', []):
                st.markdown(f'<span class="skill-badge">✓ {skill}</span>', unsafe_allow_html=True)
        
    with col2:
        with st.container(border=True):
            st.markdown('### 🚀 Skills to Acquire')
            for missing in data.get('missing_skills', []):
                if isinstance(missing, dict):
                    st.markdown(f"**{missing.get('skill', '')}** (Priority: {missing.get('priority', '')})")
                    st.markdown(f"*{missing.get('reason', '')}*")
                    st.markdown("---")

def learning_roadmap_section():
    if not st.session_state.learning_roadmap:
        st.warning("Please generate a roadmap from the Career Paths tab.")
        return
        
    st.markdown('<h1 class="title-gradient">Your Journey Map</h1>', unsafe_allow_html=True)
    
    data = st.session_state.learning_roadmap
    
    # 1. Fallback for conversational/broken JSON
    if isinstance(data, dict) and 'raw_response' in data:
        with st.container(border=True):
            st.markdown(data['raw_response'])
        return
    
    # 2. Check for both 'roadmap' and 'actionPlan' naming conventions
    items = []
    if isinstance(data, dict):
        items = data.get('roadmap', data.get('actionPlan', []))
        
    # 3. Fallback if the data structure is completely unrecognizable
    if not items:
        with st.container(border=True):
            st.info("The AI generated a roadmap, but in an unusual format. Here is the raw output:")
            st.write(data)
        return
    
    # 4. Standard Display
    with st.container(border=True):
        for milestone in items:
            # Handle AI naming variations (month vs step, title vs task)
            phase_num = milestone.get('month', milestone.get('step', ''))
            phase_title = milestone.get('title', milestone.get('task', 'Milestone'))
            
            st.markdown(f"""
            <div class="timeline-item">
                <h3 style="margin-top:0; color:#a78bfa;">Phase {phase_num}: {phase_title}</h3>
            """, unsafe_allow_html=True)
            
            cols = st.columns(3)
            with cols[0]:
                st.markdown("**🎯 Objectives**")
                # Fallback to 'description' if 'objectives' doesn't exist
                objectives = milestone.get('objectives', [milestone.get('description', '')])
                for obj in objectives: 
                    if obj: st.markdown(f"- {obj}")
            with cols[1]:
                st.markdown("**📚 Resources**")
                for res in milestone.get('resources', ["Search for relevant online courses"]): st.markdown(f"- {res}")
            with cols[2]:
                st.markdown("**🛠️ Execution**")
                for proj in milestone.get('projects', ["Practice core concepts"]): st.markdown(f"- {proj}")
            st.markdown("</div>", unsafe_allow_html=True)

def project_ideas_section():
    if not st.session_state.selected_career:
        st.warning("Please select a career path first.")
        return
        
    st.markdown('<h1 class="title-gradient">Portfolio Builder</h1>', unsafe_allow_html=True)
    
    # Generate on demand
    if not st.session_state.projects:
        if st.button("🚀 Generate Project Ideas"):
            with st.spinner("Brainstorming projects..."):
                career_title = st.session_state.selected_career['title']
                missing = st.session_state.skill_gap_analysis.get('analysis', {}).get('missing_skills', []) if st.session_state.skill_gap_analysis else []
                st.session_state.projects = call_groq_api(get_project_ideas_prompt(career_title, missing))
                st.rerun()
        return

    data = st.session_state.projects
    if isinstance(data, dict) and 'raw_response' in data:
        with st.container(border=True):
            st.markdown(data['raw_response'])
        return
        
    projects = data.get('projects', []) if isinstance(data, dict) else []
    for proj in projects:
        with st.container(border=True):
            st.subheader(f"🛠️ {proj.get('title', '')} ({proj.get('difficulty', '')})")
            st.markdown(proj.get('description', ''))
            st.markdown("**Core Features:**")
            for feat in proj.get('features', []):
                st.markdown(f"- {feat}")
            st.markdown("**Tech Stack:**")
            for tech in proj.get('tech_stack', []):
                st.markdown(f'<span class="skill-badge">{tech}</span>', unsafe_allow_html=True)

def cover_letter_section():
    if not st.session_state.selected_career:
        st.warning("Please select a career path first.")
        return
        
    st.markdown('<h1 class="title-gradient">Cover Letter Draft</h1>', unsafe_allow_html=True)
    
    # Generate on demand
    if not st.session_state.cover_letter:
        if st.button("📝 Draft My Cover Letter"):
            with st.spinner("Writing professional cover letter..."):
                career_title = st.session_state.selected_career['title']
                st.session_state.cover_letter = call_groq_api(get_cover_letter_prompt(career_title, st.session_state.user_data['skills']))
                st.rerun()
        return

    with st.container(border=True):
        data = st.session_state.cover_letter
        if isinstance(data, dict) and 'raw_response' in data:
            st.markdown(data['raw_response'])
        else:
            content = data.get('cover_letter_body', '') if isinstance(data, dict) else str(data)
            st.markdown(content)

def interview_prep_section():
    if not st.session_state.selected_career:
        st.warning("Please select a career path first.")
        return
        
    st.markdown('<h1 class="title-gradient">Interview Prep</h1>', unsafe_allow_html=True)
    
    # Generate on demand
    if not st.session_state.interview_prep:
        if st.button("🎤 Generate Interview Guide"):
            with st.spinner("Preparing interview materials..."):
                career_title = st.session_state.selected_career['title']
                req_skills = st.session_state.selected_career.get('required_skills', [])
                st.session_state.interview_prep = call_groq_api(get_interview_prep_prompt(career_title, req_skills))
                st.rerun()
        return

    data = st.session_state.interview_prep if isinstance(st.session_state.interview_prep, dict) else {}
    
    with st.container(border=True):
        if 'raw_response' in data:
            st.markdown(data['raw_response'])
        else:
            st.markdown("### 💡 Expert Strategy Tips")
            st.info(data.get('tips', ''))
            
            st.markdown("### 💻 Technical Questions")
            for q in data.get('technical_questions', []):
                with st.expander(q.get('question', '')):
                    st.markdown(q.get('answer', ''))
                    
            st.markdown("### 🤝 Behavioral Questions")
            for q in data.get('behavioral_questions', []):
                with st.expander(q.get('question', '')):
                    st.markdown(q.get('answer', ''))

def ai_chat_assistant():
    st.markdown('<h1 class="title-gradient">AI Career Mentor</h1>', unsafe_allow_html=True)
    with st.container(border=True):
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if len(st.session_state.chat_history) == 0:
            st.info("Ask me anything about your career path!")
            
    if prompt := st.chat_input("Type your question here..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.rerun()

def main():
    init_session_state()
    sidebar_navigation()
    
    if st.session_state.current_tab == "AI Chat Assistant" and len(st.session_state.chat_history) > 0 and st.session_state.chat_history[-1]["role"] == "user":
        prompt = st.session_state.chat_history[-1]["content"]
        with st.spinner("Thinking..."):
            ctx = f"Profile: {st.session_state.user_data}. Q: {prompt}"
            res = call_groq_api(ctx, response_format="text")
            if isinstance(res, str) and res.strip().startswith("{"):
                try:
                    parsed = json.loads(res)
                    res = parsed.get("response", parsed.get("message", res))
                except: pass
            elif isinstance(res, dict):
                res = res.get('raw_response', res.get('response', str(res)))
            
            st.session_state.chat_history.append({"role": "assistant", "content": str(res)})
            st.rerun()

    tabs = {
        "User Input": user_input_section,
        "Career Recommendations": career_recommendations_section,
        "Skill Gap Analysis": skill_gap_analysis_section,
        "Learning Roadmap": learning_roadmap_section,
        "Project Ideas": project_ideas_section,
        "Cover Letter": cover_letter_section,
        "Interview Prep": interview_prep_section,
        "AI Chat Assistant": ai_chat_assistant
    }
    
    if st.session_state.current_tab in tabs:
        tabs[st.session_state.current_tab]()

if __name__ == "__main__":
    main()
