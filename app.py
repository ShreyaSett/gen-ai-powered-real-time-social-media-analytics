import os
import streamlit as st
import requests
import json
import traceback
import time
import streamlit.components.v1 as components
import base64
from st_clickable_images import clickable_images
import boto3
from datetime import datetime
from datetime import datetime, timedelta
from botocore.config import Config

import boto3
from botocore.exceptions import ClientError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_fake_news_alert(fake_news_content):
    # Create SES client
    ses_client = boto3.client('ses', region_name='us-east-1')
    
    SENDER = "issett@amazon.com"
    RECIPIENT = "issett@amazon.com"
    SUBJECT = "⚠️ Fake News Alert Detected"
    
    # Create message
    BODY_TEXT = f"""
    Fake News Alert!
    
    The following potentially false information has been detected:
    
    {fake_news_content}
    
    Time Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
    
    Please review and take necessary actions.
    """
    
    BODY_HTML = f"""
    <html>
    <head></head>
    <body>
        <h1>Fake News Alert!</h1>
        <p>The following potentially false information has been detected:</p>
        <div style="
            background-color: #fff3f3;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin: 10px 0;
        ">
            {fake_news_content}
        </div>
        <p><strong>Time Detected:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p>Please review and take necessary actions.</p>
    </body>
    </html>
    """
    
    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER
    msg['To'] = RECIPIENT
    
    # Add text and HTML alternatives
    part1 = MIMEText(BODY_TEXT, 'plain')
    part2 = MIMEText(BODY_HTML, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        response = ses_client.send_raw_email(
            Source=SENDER,
            Destinations=[RECIPIENT],
            RawMessage={
                'Data': msg.as_string()
            }
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        return False

# Initialize the AWS Bedrock Runtime client
bedrock_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name='us-east-1'
)

# Initialize session states
if "current_tab" not in st.session_state:
    st.session_state.current_tab = None

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi!👋 How can I assist you today?"
        }
    ]

# Initialize separate agents for sentiment and trends
if 'sentiment_agent_id' not in st.session_state:
    st.session_state.sentiment_agent_id = 'A8BSKHTUM3'
if 'sentiment_agent_alias_id' not in st.session_state:
    st.session_state.sentiment_agent_alias_id = 'KCBJMSKST4'
if 'trend_agent_id' not in st.session_state:
    st.session_state.trend_agent_id = 'DFATP3HROZ'
if 'trend_agent_alias_id' not in st.session_state:
    st.session_state.trend_agent_alias_id = 'AFEKCI1EUC'  # Replace with your trend agent alias ID

# Initialize session states for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Dummy credentials
DUMMY_USER = "admin"
DUMMY_PASS = "password123"

# API endpoints
CHATBOT_API = "https://hng6z3kml8.execute-api.us-east-1.amazonaws.com/default/simple-streamlit-chatbot/embeddings"
QUICKSIGHT_API = "https://hng6z3kml8.execute-api.us-east-1.amazonaws.com/default/quicksight"

# Page configuration
st.set_page_config(
    page_title="AnyCompany Platform",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Function to encode images to base64
def get_image_base64(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data)
    return encoded.decode("utf-8")

def create_return_home_button():
    # Container for return home button with updated styling
    st.markdown("""
        <style>
        .floating-return-home {
            position: fixed;
            bottom: 80px;  /* Increased to avoid footer overlap */
            right: 20px;
            z-index: 9999;  /* Increased z-index */
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 10px 20px;
            color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        .floating-return-home:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([4,1,4])
    with col2:
        if st.button("Home", key=f"home_{st.session_state.current_tab}", 
                    help="Return to main menu",
                    use_container_width=True):
            st.session_state.current_tab = None
            st.rerun()

# Function for trend analysis
def analyze_trends():
    try:
        response = bedrock_runtime.invoke_agent(
            agentId=st.session_state.trend_agent_id,
            agentAliasId=st.session_state.trend_agent_alias_id,
            sessionId=str(datetime.now().timestamp()),
            inputText=(
                "Analyze the current social media posts and provide:\n"
                "1. Top 10 trending hashtags with their post counts (e.g., '#AIForGood (52 posts)')\n"
                "2. For each trending hashtag, provide:\n"
                "   - Key discussion points\n"
                "   - Main topics people are talking about\n"
                "   - Notable mentions or references\n"
                "3. Provide a quick summary of what people are discussing about these trending topics\n\n"
                "Format the response as:\n"
                "🔥 Top Trending Hashtags:\n"
                "1. #HashtagName (count posts)\n"
                "2. #HashtagName (count posts)\n"
                "... and so on\n\n"
                "📌 Associated Topics & Discussions:\n"
                "• #HashtagName: Brief summary of what people are discussing\n"
                "• #HashtagName: Brief summary of what people are discussing\n"
                "... and so on\n\n"
                "💡 Quick Summary:\n"
                "Brief overview of main conversation themes and notable discussions"
                "4. Identify any potential fake news or misinformation\n\n"  # Added this line
                "Format the response to include a specific section for fake news alerts:\n"
                "Fake News Alerts:\n"
                "- [Content of fake news]\n"
                "- Confidence: [percentage]\n"
            )
        )

        final_answer = None
        try:
            for event in response.get('completion'):
                if 'chunk' in event:
                    data = event['chunk']['bytes']
                    final_answer = data.decode('utf8')
                    print(f"Trends analysis ->\n{final_answer}")
                elif 'trace' in event:
                    print(json.dumps(event['trace'], indent=2))
                else: 
                    raise Exception("unexpected event.", event)

            return final_answer
        except Exception as e:
            raise Exception("unexpected event.",e)

    except Exception as e:
        return f"Error: {str(e)}"


# Function for sentiment analysis
def analyze_sentiment(text):
    try:
        response = bedrock_runtime.invoke_agent(
            agentId=st.session_state.sentiment_agent_id,
            agentAliasId=st.session_state.sentiment_agent_alias_id,
            sessionId=str(datetime.now().timestamp()),
            inputText=f"""Analyze the sentiment for the brand: {text}
            
            Please provide:
            1. Overall Distribution with percentages and trends
            2. Recent sentiment changes in the last hour
            3. Notable events that affected sentiment
            4. Top positive and negative words used in discussions
            5. Key observations about sentiment patterns
            
            Format as:
            Sentiment Analysis for {text} (Last 1 Hour):

            Overall Distribution:
            • Positive: X% (increasing/decreasing/stable)
            • Neutral: Y% (increasing/decreasing/stable)
            • Negative: Z% (increasing/decreasing/stable)

            Recent Trend:
            [Description of how sentiment has changed]

            Notable Events:
            - Event 1 (impact: +X% or -Y%)
            - Event 2 (impact: +X% or -Y%)

            Top Words:
            Positive Words: [word1, word2, word3, word4, word5]
            Negative Words: [word1, word2, word3, word4, word5]

            Key Observations:
            - [Observation 1]
            - [Observation 2]
            - [Observation 3]

            Data timeframe: [start] to [end] UTC
            Total posts analyzed: [number]"""
        )


        final_answer = ""
        try:
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk_data = event['chunk']['bytes'].decode('utf-8')
                    final_answer += chunk_data
                    
            if not final_answer:
                return "Error: No response received from the sentiment analysis."
                
            return final_answer.strip()
            
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            return f"Error processing response: {str(e)}"

    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        return f"Error: {str(e)}"
# Function for QuickSight embedding
def get_quicksight_q_embedding():
    try:
        response = requests.get(QUICKSIGHT_API)
        if response.status_code == 200:
            data = response.json()
            if 'body' in data:
                try:
                    body = json.loads(data['body'])
                    embed_url = body.get('embedUrl')
                    return embed_url if embed_url else None
                except json.JSONDecodeError:
                    return None
        return None
    except Exception:
        return None

# QuickSight embedding HTML template
def get_dashboard_html(embed_url):
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Dashboard Embedding</title>
            <script src="https://unpkg.com/amazon-quicksight-embedding-sdk@2.10.1/dist/quicksight-embedding-js-sdk.min.js"></script>
            <script type="text/javascript">
                const embedDashboard = async() => {{
                    const {{
                        createEmbeddingContext,
                    }} = QuickSightEmbedding;

                    const embeddingContext = await createEmbeddingContext({{
                        onChange: (changeEvent, metadata) => {{
                            console.log('Context received a change', changeEvent, metadata);
                        }},
                    }});

                    const frameOptions = {{
                        url: "{embed_url}",
                        container: '#experience-container',
                        height: "800px",
                        width: "100%",
                        onChange: (changeEvent, metadata) => {{
                            console.log('Frame received a change', changeEvent, metadata);
                        }},
                    }};

                    const contentOptions = {{
                        toolbarOptions: {{
                            export: true,
                            undoRedo: true,
                            reset: true,
                            executiveSummary: true
                        }}
                    }};
                    
                    try {{
                        const embeddedDashboardExperience = await embeddingContext.embedDashboard(frameOptions, contentOptions);
                        console.log("Dashboard embedded successfully");
                    }} catch (error) {{
                        console.error("Error embedding dashboard:", error);
                        document.getElementById('error-message').innerText = "Error embedding dashboard: " + error.message;
                    }}
                }};
            </script>
        </head>
        <body onload="embedDashboard()">
            <div id="experience-container" style="height: 800px;"></div>
            <div id="error-message" style="color: red;"></div>
        </body>
    </html>
    """

def show_login_page():
    st.markdown("""
        <style>
            .stApp {
                background: #301934 !important;
            }
            
            .login-container {
                max-width: 400px;
                margin: 0 auto;
                padding: 3rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
                margin-top: 50px;
                backdrop-filter: blur(10px);
            }
            
            .company-login-name {
                font-size: 3.5rem;
                font-weight: 700;
                color: white;
                font-family: 'Helvetica Neue', sans-serif;
                letter-spacing: 2px;
                margin-bottom: 1rem;
                text-align: center;
                padding: 2rem 0;
            }
            
            .login-subtitle {
                text-align: center;
                color: #cccccc;
                font-size: 1.2rem;
                margin-bottom: 3rem;
                font-weight: 300;
            }
            
            /* Updated input styling */
            .stTextInput > div > div {
                background-color: white !important;
                padding: 0.5rem;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: all 0.3s ease;
            }
            
            .stTextInput > div > div:hover {
                border-color: white;
            }
            
            .stTextInput > div > div > input {
                color: black !important;
                font-size: 1rem;
                padding: 0.5rem;
                background-color: white !important;
            }

            /* Style placeholder text */
            .stTextInput > div > div > input::placeholder {
                color: rgba(0, 0, 0, 0.6) !important;
            }
            
            .stButton > button {
                background: white;
                color: black;
                border-radius: 10px;
                padding: 0.8rem 1rem;
                font-size: 1.1rem;
                font-weight: 500;
                border: none;
                transition: all 0.3s ease;
                width: 100%;
                margin-top: 1rem;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(255, 255, 255, 0.2);
            }
            
            .login-footer {
                text-align: center;
                margin-top: 2rem;
                color: #cccccc;
                font-size: 0.9rem;
            }
            
            /* Hide Streamlit Components */
            #MainMenu {visibility: hidden;}  /* Hides hamburger menu */
            footer {visibility: hidden;}     /* Hides footer */
            header {visibility: hidden;}     /* Hides header */
            
            /* Custom Label Styling */
            .stTextInput label {
                color: white !important;
                font-weight: 500;
                font-size: 1rem;
            }
        </style>

    """, unsafe_allow_html=True)

    # Center logo and company name
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown(f"""
            <div style="text-align: center; padding: 2rem 0;">
                <img src="data:image/png;base64,{get_image_base64('anycompany_logo.png')}" 
                     style="max-width: 150px; margin-bottom: 1rem;">
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown('<div class="company-login-name">AnyCompany</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Welcome back! Please login to continue.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("Sign In"):
            if username == DUMMY_USER and password == DUMMY_PASS:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials! Try admin/password123")
        
        st.markdown("""
            <div class="login-footer">
                By logging in, you agree to our Terms of Service and Privacy Policy
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
# Main application CSS
st.markdown("""
<style>
    /* Main container and background */
    [data-testid="stAppViewContainer"] {
        background-color: #301934 !important;
        color: white !important;
    }
    
    .stApp {
        background: #301934 !important;
    }

    /* Input container background fix */
    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stPasswordInput > div > div {
        background-color: white !important;
    }

    /* Style input labels */
    [data-testid="stTextInput"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stPasswordInput"] label {
        color: white !important;
    }

    /* Style placeholder text */
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stNumberInput"] input::placeholder,
    [data-testid="stPasswordInput"] input::placeholder {
        color: rgba(0, 0, 0, 0.6) !important;
    }

    /* Chat input styling */
    [data-testid="stChatInput"] textarea {
        color: black !important;
        background-color: white !important;
        border: 1px solid rgba(0, 0, 0, 0.2) !important;
        -webkit-text-fill-color: black !important;
    }
    
    /* Ensure sidebar also has the same background */
    [data-testid="stSidebar"] {
        background-color: #301934 !important;
    }
    
    /* Login container background */
    .login-container {
        background: rgba(48, 25, 52, 0.1) !important;
    }
    
    /* Adjust other container backgrounds to match the theme */
    .custom-container {
        background: rgba(48, 25, 52, 0.1) !important;
    }
    
    .trend-card, .topic-card, .data-card {
        background: rgba(48, 25, 52, 0.2) !important;
    }
    
    /* Ensure text input backgrounds are visible */
    [data-testid="stTextInput"] input {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Style for markdown text */
    .stMarkdown {
        color: white !important;
    }
    
    /* Update any semi-transparent backgrounds */
    div[data-testid="stChatMessageContent"] {
        background-color: rgba(48, 25, 52, 0.2) !important;
    }
    
    .header-container {
        text-align: center;
        padding: 3rem 0;
        margin-bottom: 2rem;
    }
    
    .company-name {
        font-size: 4rem;
        font-weight: 700;
        color: white;
        font-family: 'Helvetica Neue', sans-serif;
        letter-spacing: 2px;
        margin-bottom: 1rem;
    }
    
    .welcome-text {
        font-size: 1.5rem;
        color: white;
        margin-top: 1rem;
        font-weight: 300;
    }
    
    /* Cards styling */
    .text-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        box-shadow: 0 4px 6px rgba(255, 255, 255, 0.1);
        padding: 2rem;
        width: 100%;
        text-align: center;
        margin-top: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Trend Cards */
    .trend-card {
        background: linear-gradient(135deg, rgba(29,161,242,0.1) 0%, rgba(29,161,242,0.05) 100%);
        border: 1px solid rgba(29,161,242,0.2);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .trend-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }

    .hashtag-card {
        text-align: center;
        padding: 15px;
        background: linear-gradient(135deg, rgba(29,161,242,0.1) 0%, rgba(29,161,242,0.05) 100%);
        border-radius: 10px;
        margin-bottom: 10px;
    }

    .topic-card {
        padding: 15px;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    /* Analysis Cards */
    .analysis-card {
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        text-align: center;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .data-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .data-card h4 {
        color: white;
        margin-top: 0;
        margin-bottom: 10px;
    }
    
    .data-card p {
        color: #cccccc;
        margin: 0;
    }
    
    /* Button styling */
    .stButton button {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        background-color: rgba(255, 255, 255, 0.2) !important;
        transform: translateY(-2px);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #111;
        padding: 2rem;
    }
    
    /* Text input styling */
    .stTextArea > div > div {
        background-color: rgba(255, 255, 255, 0.1);
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
    }
    
    .stTextArea textarea {
        color: white !important;
    }
    
    /* Status Indicators */
    .status-complete {
        background-color: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .status-processing {
        background-color: #ffc107;
        color: black;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .status-error {
        background-color: #dc3545;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
    }
            
    /* Chat interface styling */
    [data-testid="stChatInput"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    [data-testid="stChatInput"] > div > textarea {
        color: white !important;
        font-size: 1rem !important;
    }
    
    /* Login input styling */
    [data-testid="stTextInput"] input {
        color: white !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
    }

    [data-testid="stTextInput"] input::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
    }

    /* Password field specific styling */
    [data-testid="stTextInput"] [type="password"] {
        color: white !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    /* Chat message styling */
    [data-testid="stChatMessage"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    [data-testid="stChatMessage"] p {
        color: white !important;
        font-size: 1rem !important;
        line-height: 1.5 !important;
    }

    /* User message specific styling */
    [data-testid="stChatMessage"][data-testid="user"] {
        background-color: rgba(0, 120, 212, 0.1) !important;
        border: 1px solid rgba(0, 120, 212, 0.2) !important;
    }

    /* Assistant message specific styling */
    [data-testid="stChatMessage"][data-testid="assistant"] {
        background-color: rgba(40, 167, 69, 0.1) !important;
        border: 1px solid rgba(40, 167, 69, 0.2) !important;
    }

    /* Message content styling */
    .stMarkdown p {
        color: white !important;
    }

    /* Chat container styling */
    .element-container div[data-testid="stChatMessageContainer"] {
        background-color: transparent !important;
    }

    /* Input placeholder styling */
    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
    }
    
    /* Text card styling */
    .text-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 30px !important;  /* Matching the image border radius */
        box-shadow: 0 4px 6px rgba(255, 255, 255, 0.1);
        padding: 2rem;
        width: 100%;
        text-align: center;
        margin-top: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Card title and description styling */
    .card-title {
        color: white;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .card-description {
        color: rgba(255, 255, 255, 0.8);
        font-size: 0.9rem;
    }

    /* Hover effects for cards */
    .text-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(255, 255, 255, 0.15);
    }
    
    /* Login container styling */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 3rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 30px;  /* Matching other elements' border radius */
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
        margin-top: 50px;
        backdrop-filter: blur(10px);
    }

    /* Login input wrapper styling */
    .stTextInput > div {
        margin-bottom: 1rem;
    }

    /* Login input label styling */
    .stTextInput label {
        color: white !important;
        font-weight: 500;
        margin-bottom: 0.5rem;
        display: block;
    }

    /* Login button styling */
    .stButton > button {
        background: white !important;
        color: black !important;
        border-radius: 15px !important;
        padding: 0.8rem 1rem !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        border: none !important;
        width: 100% !important;
        margin-top: 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(255, 255, 255, 0.2) !important;
    }

    /* Video container styling */
    .stVideo {
        width: 100%;
        max-width: 720px;
        margin: 1rem auto;
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Video message styling */
    [data-testid="stChatMessage"] .stVideo {
        margin: 0.5rem 0;
    }
    
    /* Video loading indicator */
    .video-loading {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin: 1rem 0;
    }

    /* Specific styling for brand sentiment analysis input */
    #brand-input .stTextInput input {
        color: black !important;
        background-color: white !important;
        border: 1px solid rgba(0, 0, 0, 0.2);
        border-radius: 5px;
        padding: 0.5rem;
    }

    #brand-input .stTextInput input:focus {
        border-color: #301934;
        box-shadow: 0 0 0 1px #301934;
    }

    #brand-input .stTextInput label {
        color: white !important;
    }

    #brand-input .stTextInput input::placeholder {
        color: rgba(0, 0, 0, 0.5);
    }

    .home-button-container {
        margin: 1rem 0;
        text-align: left;
    }

    .home-button-container .stButton > button {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 5px !important;
        padding: 0.3rem 0.7rem !important;
        font-size: 0.8rem !important;
        font-weight: normal !important;
        width: auto !important;
        margin: 0 !important;
        transition: all 0.3s ease;
    }

    .home-button-container .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* Debug styles */
        #brand-input * {
            border: 1px solid red !important;
        }
        
        #brand-input input {
            opacity: 1 !important;
            visibility: visible !important;
        }
        
        /* Force text visibility */
        #brand-input .stTextInput > div > div > input {
            color: black !important;
            -webkit-text-fill-color: black !important;
            text-fill-color: black !important;
            background-color: white !important;
            opacity: 1 !important;
            mix-blend-mode: normal !important;
        }

</style>
""", unsafe_allow_html=True)

# Main application flow
if not st.session_state.logged_in:
    show_login_page()
else:
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        
        st.subheader("Sentiment Analysis Agent")
        st.session_state.sentiment_agent_id = st.text_input(
            "Sentiment Agent ID", 
            st.session_state.sentiment_agent_id
        )
        st.session_state.sentiment_agent_alias_id = st.text_input(
            "Sentiment Agent Alias ID", 
            st.session_state.sentiment_agent_alias_id
        )
        
        st.subheader("Trend Analysis Agent")
        st.session_state.trend_agent_id = st.text_input(
            "Trend Agent ID", 
            st.session_state.trend_agent_id
        )
        st.session_state.trend_agent_alias_id = st.text_input(
            "Trend Agent Alias ID", 
            st.session_state.trend_agent_alias_id
        )
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # Main content
    if st.session_state.current_tab is None:
        st.markdown(f"""
            <div class="header-container">
                <img src="data:image/png;base64,{get_image_base64('anycompany_logo.png')}" 
                     style="max-width: 200px; margin-bottom: 1rem;">
                <div class="company-name">AnyCompany</div>
                <div class="welcome-text">Welcome to AnyCompany portal</div>
            </div>
        """, unsafe_allow_html=True)
        # Main cards display
        col1, col2, col3, col4 = st.columns(4)
        
        cards = [
            {
                "image": "trending-svgrepo-com.png",
                "title": "Trend Board",
                "description": "Track Market Trends and Patterns",
                "tab": "Trends"
            },
            {
                "image": "quality-badge-ribbon-svgrepo-com.png",
                "title": "Senti-Meter",
                "description": "Brand Sentiment Analysis",
                "tab": "Brand Score"
            },
            {
                "image": "analysis-seo-graph-svgrepo-com.png",
                "title": "Executive Dashboards",
                "description": "Real-time Dashboards and Executive Summaries",
                "tab": "Data Analysis (Q)"
            },
            {
                "image": "dialogue-conversation-bubble-svgrepo-com.png",
                "title": "Assistant",
                "description": "Get insights and help",
                "tab": "Chat"
            }            
        ]
        
        for idx, (col, card) in enumerate(zip([col1, col2, col3, col4], cards)):
            with col:
                clicked = clickable_images(
                    [f"data:image/png;base64,{get_image_base64(card['image'])}"],
                    titles=[card["title"]],
                    div_style={
                        "display": "flex", 
                        "justify-content": "center", 
                        "padding": "1rem",
                        "margin-bottom": "1rem"
                    },
                    img_style={
                        "width": "200px", 
                        "height": "200px", 
                        "margin": "0", 
                        "padding": "1.5rem",
                        "border-radius": "30px",
                        "box-shadow": "0 4px 6px rgba(255, 255, 255, 0.1)",
                        "background": "rgba(255, 255, 255, 0.1)",
                        "transition": "transform 0.3s ease, box-shadow 0.3s ease",
                        "border": "1px solid rgba(255, 255, 255, 0.2)",
                        "overflow": "hidden"
                    }
                )
                
                st.markdown(f"""
                    <div class="text-card">
                        <div class="card-title">{card['title']}</div>
                        <div class="card-description">{card['description']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                if clicked == 0:
                    st.session_state.current_tab = card['tab']
                    st.rerun()

    elif st.session_state.current_tab == "Trends":
        st.markdown("<div class='custom-container'>", unsafe_allow_html=True)
        st.title("Trending Topics & Analysis")
        
        # Add refresh controls
        col1, col2 = st.columns([1,6])
        with col1:
            if st.button("🔄 Refresh"):
                st.rerun()
        with col2:
            auto_refresh = st.checkbox("Auto-refresh every 5 minutes", value=True)

        # Get trending topics
        with st.spinner("Analyzing current trends..."):
            response = analyze_trends()
            
            # In the Trends section of your Streamlit app:
            if response and not response.startswith("Error:"):
                try:
                    # Parse the response
                    sections = {
                        'trending_hashtags': [],
                        'associated_topics': {},
                        'quick_summary': []
                    }
                    current_section = None
                    current_hashtag = None
                    
                    for line in response.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                            
                        if "Top Trending Hashtags:" in line:
                            current_section = 'trending_hashtags'
                        elif "Associated Topics & Discussions:" in line:
                            current_section = 'associated_topics'
                        elif "Quick Summary:" in line:
                            current_section = 'quick_summary'
                        elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')) and current_section == 'trending_hashtags':
                            # Extract hashtag and count
                            hashtag_info = line.split('.', 1)[1].strip()
                            sections['trending_hashtags'].append(hashtag_info)
                        elif line.startswith('•') and current_section == 'associated_topics':
                            # Extract hashtag and discussion
                            parts = line.strip('• ').split(':', 1)
                            if len(parts) == 2:
                                hashtag = parts[0].strip()
                                discussion = parts[1].strip()
                                sections['associated_topics'][hashtag] = discussion
                        elif current_section == 'quick_summary':
                            sections['quick_summary'].append(line)

                    # Display Trending Hashtags
                    st.subheader("🔥 Top Trending Hashtags")
                    if sections['trending_hashtags']:
                        hashtag_cols = st.columns(3)
                        for idx, hashtag_info in enumerate(sections['trending_hashtags']):
                            with hashtag_cols[idx % 3]:
                                # Extract hashtag and count
                                parts = hashtag_info.split('(')
                                hashtag = parts[0].strip()
                                count = parts[1].strip(')') if len(parts) > 1 else ''
                                
                                st.markdown(f"""
                                    <div style="
                                        background: linear-gradient(145deg, rgba(29, 161, 242, 0.15), rgba(29, 161, 242, 0.25));
                                        border: 2px solid rgba(29, 161, 242, 0.5);
                                        border-radius: 15px;
                                        padding: 20px;
                                        margin-bottom: 15px;
                                        text-align: center;
                                        box-shadow: 0 4px 12px rgba(29, 161, 242, 0.2);
                                        backdrop-filter: blur(10px);
                                        transition: transform 0.3s ease, box-shadow 0.3s ease;
                                    ">
                                        <h3 style="
                                            color: #1DA1F2;
                                            margin: 0;
                                            font-size: 1.4rem;
                                            font-weight: bold;
                                            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                                        ">{hashtag}</h3>
                                        {f'<p style="color: #FFFFFF; margin: 10px 0 0 0; font-size: 1.1rem; font-weight: 500;">{count}</p>' if count else ''}
                                    </div>
                                """, unsafe_allow_html=True)

                    else:
                        st.info("No trending hashtags detected in the current time window.")

                    # Display Associated Topics & Discussions
                    st.subheader("📌 Topic Discussions")
                    if sections['associated_topics']:
                        for hashtag, discussion in sections['associated_topics'].items():
                            st.markdown(f"""
                                <div style="
                                    background: linear-gradient(145deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05));
                                    border: 2px solid rgba(29, 161, 242, 0.5);
                                    border-radius: 15px;
                                    padding: 20px;
                                    margin: 15px 0;
                                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                                    backdrop-filter: blur(10px);
                                ">
                                    <h4 style="
                                        color: #1DA1F2;
                                        margin: 0 0 10px 0;
                                        font-size: 1.3rem;
                                        font-weight: bold;
                                        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                                    ">{hashtag}</h4>
                                    <div style="
                                        background: rgba(255, 255, 255, 0.1);
                                        border-radius: 10px;
                                        padding: 15px;
                                        margin-top: 10px;
                                    ">
                                        <p style="
                                            color: white;
                                            margin: 0;
                                            font-size: 1.1rem;
                                            line-height: 1.5;
                                        ">{discussion}</p>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No topic discussions available.")

                    # Display Quick Summary
                    st.subheader("💡 Quick Summary")
                    if sections['quick_summary']:
                        summary_text = " ".join(sections['quick_summary'])
                        st.markdown(f"""
                            <div class="data-card" style="
                                background: linear-gradient(135deg, rgba(40,167,69,0.1) 0%, rgba(40,167,69,0.05) 100%);
                                border: 1px solid rgba(40,167,69,0.2);
                            ">
                                <p style="color: white;">{summary_text}</p>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No summary available.")
                    
                    st.subheader("🚨 Fake News Alerts")
                    if sections.get('fake_news_alerts'):
                        for alert in sections['fake_news_alerts']:
                            st.markdown(f"""
                                <div style="background: rgba(220, 53, 69, 0.05);
                                            border-radius: 5px;
                                            padding: 10px;
                                            margin: 5px 0;">
                                    <p style="color: white; margin: 0;">
                                        {alert['content']}
                                    </p>
                                    <p style="color: #dc3545; font-size: 0.9em; margin: 5px 0 0 0;">
                                        Confidence: {alert['confidence']}%
                                    </p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # Send email alert using SES
                            if not alert.get('notification_sent'):
                                if send_fake_news_alert(alert['content']):
                                    alert['notification_sent'] = True
                                    st.success("Fake news alert notification sent successfully!")
                                else:
                                    st.error("Failed to send fake news alert notification")
                    else:
                        st.markdown("""
                            <div style="background: rgba(40, 167, 69, 0.1);
                                        border: 2px solid #28a745;
                                        border-radius: 10px;
                                        padding: 20px;
                                        margin: 10px 0;">
                                <h4 style="color: #28a745; margin: 0;">✅ No Fake News Detected</h4>
                                <p style="color: white; margin: 10px 0 0 0;">
                                    All trending topics appear to be from legitimate sources.
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                    # Add metadata
                    st.markdown(f"""
                        <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.05); border-radius: 10px;">
                            <h4 style="color: #666; margin: 0;">Analysis Information</h4>
                            <p style="color: #666; margin: 5px 0; font-size: 0.9em;">
                                • Data from: Past hour
                                • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                • Auto-refresh: {'Enabled' if auto_refresh else 'Disabled'}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

                    # Debug information
                    with st.expander("Show Analysis Details"):
                        st.code(response)

                except Exception as e:
                    st.error(f"Error parsing trends: {str(e)}")
                    with st.expander("Show Raw Response"):
                        st.code(response)
            else:
                st.error(f"Analysis failed: {response}")
        st.markdown("""
            <div style="margin-top: 30px;">
                <hr style="border: 1px solid rgba(255, 255, 255, 0.1);">
            </div>
        """, unsafe_allow_html=True)
        
        create_return_home_button()
        if auto_refresh:
            time.sleep(300)  # 5 minutes
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.current_tab == "Chat":
        st.markdown("<div class='custom-container'>", unsafe_allow_html=True)
        
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name='us-east-1')

        def download_video_from_s3(bucket_name, video_key):
            """Downloads a video from S3 using the AWS SDK."""
            try:
                local_path = f"downloads/video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                s3_client.download_file(bucket_name, video_key, local_path)
                st.success(f"Video downloaded successfully to {local_path}")
                return local_path
            except ClientError as e:
                st.error(f"Error downloading video: {e}")
                return None

        def generate_presigned_url(bucket_name, video_key):
            """Generates a presigned URL for the video."""
            try:
                response = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': video_key
                    },
                    ExpiresIn=3600  # URL expires in 1 hour
                )
                return response
            except ClientError as e:
                st.error(f"Error generating presigned URL: {e}")
                return None

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if isinstance(message.get("content"), dict):
                    # Handle video responses
                    if message["content"].get("type") == "video":
                        # Display text response
                        st.write(message["content"].get("generated_response", ""))
                        
                        # Get invocation details
                        invocation = message["content"].get("invocation", {})
                        if invocation:
                            invocation_id = invocation.get('invocationArn', '').split('/')[-1]
                            if invocation_id:
                                # Construct video path
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                bucket_name = "bedrock-video-generation-us-east-1-t5sftd"
                                video_key = f"nova-videos/{timestamp}/{invocation_id}/output.mp4"
                                
                                try:
                                    # Check if video exists
                                    s3_client.head_object(Bucket=bucket_name, Key=video_key)
                                    
                                    # Generate presigned URL
                                    presigned_url = generate_presigned_url(bucket_name, video_key)
                                    if presigned_url:
                                        st.markdown(f"[Click here to view video]({presigned_url})")
                                    
                                    # Add download button
                                    if st.button("Download Video", key=f"download_{invocation_id}"):
                                        # Create downloads directory
                                        os.makedirs("downloads", exist_ok=True)
                                        
                                        # Download video
                                        local_path = download_video_from_s3(bucket_name, video_key)
                                        if local_path:
                                            with open(local_path, 'rb') as f:
                                                st.download_button(
                                                    label="Save Video",
                                                    data=f.read(),
                                                    file_name=f"brand_video_{timestamp}.mp4",
                                                    mime="video/mp4"
                                                )
                                            # Clean up
                                            os.remove(local_path)
                                    
                                    st.caption(f"Video location: s3://{bucket_name}/{video_key}")
                                
                                except s3_client.exceptions.ClientError:
                                    st.info("Video is still being generated. Please wait...")
                                    st.caption(f"Video will be available at: s3://{bucket_name}/{video_key}")
                                    if st.button("Check Video Status", key=f"refresh_{invocation_id}"):
                                        st.rerun()
                else:
                    st.write(message["content"])

        # Chat input
        if prompt := st.chat_input("Type your message here..."):
            # Display user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get AI response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.text("Processing your request...")
                
                try:
                    # Prepare the request payload
                    payload = {
                        "query": prompt,
                        "conversation_history": st.session_state.messages[-5:]
                    }
                    
                    # Make API call
                    response = requests.post(
                        CHATBOT_API,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            
                            # Handle video responses
                            if response_data.get('type') == 'video':
                                # Update placeholder with text response
                                message_placeholder.markdown(response_data['generated_response'])
                                
                                # Store in chat history
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": {
                                        "type": "video",
                                        "generated_response": response_data['generated_response'],
                                        "invocation": response_data.get('invocation')
                                    }
                                })
                                
                                # Show initial status
                                st.info("Video generation started. Please wait...")
                                if st.button("Check Video Status"):
                                    st.rerun()
                            
                            # Handle text responses
                            else:
                                message_placeholder.markdown(response_data['generated_response'])
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": response_data['generated_response']
                                })
                                
                                if 'citations' in response_data:
                                    with st.expander("Sources"):
                                        for citation in response_data['citations']:
                                            st.write(citation['text'])
                                
                        except Exception as e:
                            message_placeholder.error(f"Error processing response: {str(e)}")
                            st.error(f"Full error details: {traceback.format_exc()}")
                    else:
                        message_placeholder.error(f"Error: {response.status_code} - {response.text}")
                    
                except Exception as e:
                    message_placeholder.error(f"Error making API call: {str(e)}")
                    st.error(f"Full error details: {traceback.format_exc()}")
        create_return_home_button()
        st.markdown("</div>", unsafe_allow_html=True)
    elif st.session_state.current_tab == "Data Analysis (Q)":
        st.markdown("<div class='custom-container'>", unsafe_allow_html=True)
        st.title("Executive Dashboard")
        try:
            with st.spinner("Loading QuickSight Dashboard..."):
                embed_url = get_quicksight_q_embedding()
                if embed_url:
                    dashboard_html = get_dashboard_html(embed_url)
                    components.html(dashboard_html, height=800, scrolling=True)
                else:
                    st.error("Unable to load QuickSight Dashboard. Please try again.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.write("Detailed error:", traceback.format_exc())
        create_return_home_button()
        st.markdown("</div>", unsafe_allow_html=True)
    elif st.session_state.current_tab == "Brand Score":
        st.markdown("<div class='custom-container'>", unsafe_allow_html=True)
        st.title("Brand Sentiment Analysis")
        
        # Add this specific CSS to force text visibility
        st.markdown("""
            <style>
                /* Force text visibility in the input */
                .stTextInput input[type="text"] {
                    color: black !important;
                    -webkit-text-fill-color: black !important;
                    opacity: 1 !important;
                    background-color: white !important;
                }
                
                /* Additional overrides to ensure text visibility */
                .stTextInput > div > div > input {
                    color: black !important;
                    -webkit-text-fill-color: black !important;
                    opacity: 1 !important;
                    background-color: white !important;
                }
                
                /* Target the specific input element */
                [data-testid="stTextInput"] input {
                    color: black !important;
                    -webkit-text-fill-color: black !important;
                    opacity: 1 !important;
                    background-color: white !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Use a specific key for the text input
        brand_input = st.text_input(
            "Enter brand name:",
            key="visible_brand_input",
            help="Enter brand name"
        )
        
        if st.button("Analyze Brand Sentiment", key="analyze_button"):
            if brand_input:
                with st.spinner(f"Analyzing sentiment for {brand_input}..."):
                    try:
                        query = f"""Analyze the sentiment for the brand: {brand_input}
                        
                        Please provide:
                        1. Overall Distribution with percentages and trends
                        2. Recent sentiment changes in the last hour
                        3. Notable events that affected sentiment
                        4. Top hashtags and topics with sentiment alignment
                        5. Key observations about sentiment patterns
                        
                        Format as:
                        Sentiment Analysis for {brand_input} (Last 2 Hours):

                        Overall Distribution:
                        • Positive: X% (increasing/decreasing Y% from previous hour) (Z posts)
                        • Neutral: X% (increasing/decreasing Y% from previous hour) (Z posts)
                        • Negative: X% (increasing/decreasing Y% from previous hour) (Z posts)

                        Recent Trend:
                        [Description of sentiment changes]

                        Notable Events:
                        [List significant events with timestamps]

                        Top Associated Topics:
                        [List hashtags with sentiment percentages]

                        Key Observations:
                        [List key insights]

                        Data Quality:
                        • Reliability: [High/Medium/Low]
                        • Sample Size: [number] posts
                        • Time Range: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC to {(datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')} UTC
                        """
                        
                        response = analyze_sentiment(query)
                        
                        if response and not response.startswith("Error:"):
                            # Split the response into sections
                            sections = response.split('\n\n')
                            
                            # Distribution Section
                            st.subheader("📊 Sentiment Distribution")
                            distribution_data = next((s for s in sections if "Distribution:" in s), None)
                            if distribution_data:
                                # Create columns for each sentiment type
                                col1, col2, col3 = st.columns(3)
                                
                                # Extract sentiment data
                                sentiments = [line.strip() for line in distribution_data.split('\n') if '•' in line]
                                
                                # Update the sentiment colors to be more contrasting against #301934 background
                                sentiment_colors = {
                                    "Positive": "#00FF7F",  # Emerald Green
                                    "Neutral": "#FFA500",   # Golden Yellow
                                    "Negative": "#FF3333"   # Bright Red
                                }
                                
                                for col, sentiment in zip([col1, col2, col3], sentiments):
                                    with col:
                                        try:
                                            sentiment_type = next((k for k in sentiment_colors.keys() if k.lower() in sentiment.lower()), "Other")
                                            
                                            # Parse the sentiment text
                                            sentiment_text = sentiment.split('•')[1].strip()
                                            
                                            # Remove duplicate sentiment type
                                            sentiment_text = sentiment_text.replace(f"{sentiment_type}:", "").strip()

                                            # Extract main percentage
                                            main_parts = sentiment_text.split('%', 1)
                                            percentage = main_parts[0].strip()

                                            # Extract trend information and posts count
                                            remaining_text = sentiment_text.split('(')
                                            trend_info = ""
                                            posts_count = ""

                                            for part in remaining_text[1:]:
                                                part = part.strip().rstrip(')')
                                                if 'increasing' in part.lower() or 'decreasing' in part.lower():
                                                    trend_info = part
                                                elif 'posts' in part.lower():
                                                    posts_count = part.strip()  # Clean up any extra whitespace

                                            # Parse trend information
                                            trend_direction = ""
                                            trend_percentage = ""
                                            if trend_info:
                                                trend_direction = "increasing" if "increasing" in trend_info.lower() else "decreasing"
                                                trend_percentage = trend_info.split('%')[0].split()[-1]
                                                trend_color = "#50C878" if trend_direction == "increasing" else "#FF4444"
                                                trend_arrow = "↑" if trend_direction == "increasing" else "↓"

                                            # Update the card HTML
                                            st.markdown(f"""
                                                <div style="
                                                    background: linear-gradient(145deg, 
                                                        {sentiment_colors[sentiment_type]}15, 
                                                        {sentiment_colors[sentiment_type]}25
                                                    );
                                                    border: 2px solid {sentiment_colors[sentiment_type]};
                                                    border-radius: 15px;
                                                    padding: 20px;
                                                    text-align: center;
                                                    box-shadow: 0 4px 12px {sentiment_colors[sentiment_type]}15;
                                                    backdrop-filter: blur(10px);
                                                ">
                                                    <h3 style="
                                                        color: {sentiment_colors[sentiment_type]};
                                                        margin-bottom: 15px;
                                                        font-size: 1.5rem;
                                                        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                                                    ">
                                                        {sentiment_type}
                                                    </h3>
                                                    <div style="
                                                        font-size: 2.8rem;
                                                        font-weight: bold;
                                                        color: {sentiment_colors[sentiment_type]};
                                                        margin: 15px 0;
                                                        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                                                    ">
                                                        {percentage}%
                                                    </div>
                                                    <div style="
                                                        color: white;
                                                        margin: 15px 0;
                                                        display: flex;
                                                        align-items: center;
                                                        justify-content: center;
                                                        gap: 8px;
                                                        background: rgba(0,0,0,0.2);
                                                        padding: 10px;
                                                        border-radius: 10px;
                                                    ">
                                                        <span style="font-size: 1rem;">{trend_direction} by</span>
                                                        <span style="
                                                            font-size: 1.6rem;
                                                            font-weight: bold;
                                                            color: {trend_color};
                                                            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                                                        ">
                                                            {trend_arrow} {trend_percentage}%
                                                        </span>
                                                        <span style="font-size: 1rem;">from previous hour</span>
                                                    </div>
                                                    <div style="
                                                        color: white;
                                                        font-size: 1.2rem;
                                                        font-weight: bold;
                                                        margin-top: 15px;
                                                        background: rgba(0,0,0,0.2);
                                                        padding: 8px;
                                                        border-radius: 8px;
                                                    ">
                                                        {posts_count}
                                                    </div>
                                                </div>
                                            """, unsafe_allow_html=True)
                                        except Exception as e:
                                            st.error(f"Error processing sentiment data: {str(e)}")
                                            print(f"Error details: {str(e)}")
                                            print(f"Problematic sentiment text: {sentiment}")

                            # Recent Trend Section
                            st.subheader("📈 Sentiment Trend")
                            trend_data = next((s for s in sections if "Recent Trend:" in s), None)
                            if trend_data:
                                st.markdown(f"""
                                    <div style="
                                        background: rgba(255, 255, 255, 0.1);
                                        border-radius: 10px;
                                        padding: 20px;
                                        margin: 10px 0;
                                    ">
                                        {trend_data.replace('Recent Trend:', '').strip()}
                                    </div>
                                """, unsafe_allow_html=True)

                            # Notable Events Section
                            st.subheader("🔔 Notable Events")
                            events_data = next((s for s in sections if "Notable Events:" in s), None)
                            if events_data:
                                events = [e.strip().lstrip('- ') for e in events_data.split('\n') if e.strip() and 'Notable Events:' not in e]
                                for event in events:
                                    st.markdown(f"""
                                        <div style="
                                            background: rgba(255, 255, 255, 0.05);
                                            border-left: 4px solid #1DA1F2;
                                            padding: 15px;
                                            margin: 10px 0;
                                        ">
                                            {event}
                                        </div>
                                    """, unsafe_allow_html=True)

                            # Top Associated Topics Section
                            st.subheader("🏷️ Top Topics")
                            topics_data = next((s for s in sections if "Top Associated Topics:" in s), None)
                            if topics_data:
                                topics = [t.strip().lstrip('- ') for t in topics_data.split('\n') if t.strip() and 'Top Associated Topics:' not in t]
                                cols = st.columns(len(topics))
                                for col, topic in zip(cols, topics):
                                    with col:
                                        st.markdown(f"""
                                            <div style="
                                                background: rgba(29, 161, 242, 0.1);
                                                border: 1px solid rgba(29, 161, 242, 0.2);
                                                border-radius: 10px;
                                                padding: 15px;
                                                text-align: center;
                                            ">
                                                {topic}
                                            </div>
                                        """, unsafe_allow_html=True)

                            # Key Observations Section
                            st.subheader("💡 Key Insights")
                            observations_data = next((s for s in sections if "Key Observations:" in s), None)
                            if observations_data:
                                observations = [o.strip().lstrip('- ') for o in observations_data.split('\n') if o.strip() and 'Key Observations:' not in o]
                                for obs in observations:
                                    st.markdown(f"""
                                        <div style="
                                            background: rgba(255, 255, 255, 0.05);
                                            border-radius: 10px;
                                            padding: 15px;
                                            margin: 10px 0;
                                        ">
                                            {obs}
                                        </div>
                                    """, unsafe_allow_html=True)

                            # Data Quality Section
                            st.subheader("📋 Analysis Details")
                            quality_data = next((s for s in sections if "Data Quality:" in s), None)
                            if quality_data:
                                quality_lines = [line.strip() for line in quality_data.split('\n') if line.strip()]
                                formatted_quality_data = quality_data.replace('[start]', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                                formatted_quality_data = formatted_quality_data.replace('[end]', (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'))
                                st.markdown(f"""
                                    <div style="
                                        background: rgba(255, 255, 255, 0.05);
                                        border: 1px solid rgba(255, 255, 255, 0.1);
                                        border-radius: 10px;
                                        padding: 20px;
                                        margin-top: 20px;
                                    ">
                                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                                            {formatted_quality_data.replace('Data Quality:', '').replace('•', '')}
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)

                        else:
                            st.error(f"Analysis failed: {response}")
                            
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                
            else:
                st.warning("Please enter a brand name to analyze.")

        
        with st.expander("Analysis Information"):
            st.markdown("""
                This tool performs brand sentiment analysis using:
                - Brand mention tracking
                - Sentiment evaluation
                - Data aggregation
                - Trend analysis
                
                Common brands for analysis:
                ```
                Gucci, Nike, Apple, Tesla, Samsung, etc.
                ```
            """)
        create_return_home_button()
        st.markdown("</div>", unsafe_allow_html=True)
    
# Add custom footer
st.markdown("""
    <style>
    .custom-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem;
        background-color: rgba(48, 25, 52, 0.9);
        backdrop-filter: blur(10px);
        text-align: center;
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.8rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        z-index: 1000;
    }
    
    /* Add padding to main content to prevent footer overlap */
    [data-testid="stAppViewContainer"] {
        padding-bottom: 4rem;
    }
    </style>
    
    <div class="custom-footer">
        AnyCompany © 2025
    </div>
""", unsafe_allow_html=True)

