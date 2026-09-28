import json
import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

# 1. Load environment variables from the local .env file securely
load_dotenv()

# 2. Verify the environment variable is loaded before initializing the client
api_key = os.environ.get("SARVAM_API_KEY")

if not api_key:
    raise ValueError("CRITICAL ERROR: SARVAM_API_KEY not found. Please check your .env file setup.")

# 3. Pass the loaded key directly into the SarvamAI client constructor
client = SarvamAI(api_subscription_key=api_key)


def analyze_resume(resume_text, user_goal):
    """
    Analyzes a given resume text using Sarvam AI based on a specified user career goal.
    Extracts relevant skills, identifies gaps, builds a custom roadmap, and provides 
    tailored interview questions in a strict JSON schema.
    """
    prompt = f"""
Evaluate the resume based on the user's goal.

User goal: "{user_goal}"

STRICT RULES:
1. Extract only relevant skills for this goal.
2. REMOVE completely irrelevant tools [e.g. excel for backend, etc.].
3. Identify real engineering gaps.
4. Generate actionable roadmap points only for missing fields.
5. Make output distinct based on the career goal.

RESPONSE FORMAT:
You MUST reply with a single, valid JSON object. Do NOT wrap it in ```json ``` codeblocks. Do NOT add any introductory or concluding conversational text.

Expected JSON Structure:
{{
    "skills": ["skill1", "skill2"],
    "missing_skills": ["skill3", "skill4"],
    "roadmap": ["step1", "step2"],
    "interview_questions": ["q1", "q2"]
}}

Resume to analyze:
{resume_text}
"""
    try:
        # Call Sarvam AI Chat Completion API
        response = client.chat.completions(
            model="sarvam-105b",
            temperature=0.1,  # Lowered temperature makes output more deterministic/adherent to rules
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict technical hiring manager. You only communicate using valid, raw JSON objects matching the user's requested schema. Never output markdown block markers or friendly chat."
                },
                {"role": "user", "content": prompt}
            ]
        )

        # Retrieve string content from Sarvam response payload
        if not response.choices or len(response.choices) == 0:
            raise ValueError("No response choices returned from AI model")
        
        message = response.choices[0].message
        if not message or not message.content:
            raise ValueError("No message content in AI response")
            
        content = message.content.strip()

        # Clean off markdown syntax backticks if the model ignores system rules
        if content.startswith("```"):
            # Split off line breaks to drop '```json' or '```'
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        # Isolate the definitive JSON outer boundaries
        start = content.find("{")
        end = content.rfind("}") + 1
        
        if start == -1 or end == 0:
            raise ValueError(f"The AI model did not return a valid JSON block. Raw Response: {content}")

        # Parse the extracted string block into a native Python dictionary
        return json.loads(content[start:end])
        
    except Exception as e:
        # Fallback dictionary tracking the error exception safely
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": str(e)
        }


# --- Test Execution Block ---
if __name__ == "__main__":
    # Test Data Setup
    sample_resume = """
    John Doe
    Backend Developer Intern
    Skills: Python, Django, postgreSQL, Git, Microsoft Excel, HTML, CSS.
    Experience: Built 3 REST APIs using Django REST Framework. Managed user tables in postgres.
    """
    
    sample_goal = "Transition into a specialized Backend Engineer focusing heavily on high-throughput system architecture and cloud deployments."
    
    print("Sending payload data securely to Sarvam AI...")
    # Fixed typo in test execution function name
    analysis_result = analyze_resume(sample_resume, sample_goal)
    
    print("\n=== PROJECT ANALYSIS OUTPUT (PARSED JSON) ===")
    print(json.dumps(analysis_result, indent=4))