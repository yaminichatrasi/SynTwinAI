from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import OpenAI
from dotenv import load_dotenv

from datetime import datetime
import os
import json
import re
import traceback

# ============================================================
# REPORTLAB - PDF
# ============================================================

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)

# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY not found in .env file"
    )

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="SynTwin AI",
    description=(
        "AI Digital Twin Creator for "
        "Synthetic User Behavior Simulation"
    )
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

# ============================================================
# DATA STORAGE
# ============================================================

DATA_FOLDER = "data"

MEMORY_FILE = os.path.join(
    DATA_FOLDER,
    "persona_memory.json"
)

REPORT_FOLDER = "reports"

os.makedirs(
    DATA_FOLDER,
    exist_ok=True
)

os.makedirs(
    REPORT_FOLDER,
    exist_ok=True
)


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    text = str(value)

    text = re.sub(
        r"[\x00-\x08\x0B\x0C\x0E-\x1F]",
        "",
        text
    )

    return text.strip()


def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {}

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

        return {}

    except Exception as e:

        print(
            "Memory Load Error:",
            e
        )

        return {}


def save_memory(data):

    os.makedirs(
        DATA_FOLDER,
        exist_ok=True
    )

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def normalize_experiment_name(name):

    return clean_text(name)


def get_experiment_from_memory(experiment_name):

    memory = load_memory()

    experiment_name = normalize_experiment_name(
        experiment_name
    )

    if experiment_name in memory:
        return memory[experiment_name]

    for key, value in memory.items():

        if key.lower() == experiment_name.lower():
            return value

    return None


# ============================================================
# JSON EXTRACTION HELPER
# ============================================================

def extract_json_array(raw_text):

    raw_text = clean_text(raw_text)

    if not raw_text:

        raise ValueError(
            "Empty AI response"
        )

    raw_text = re.sub(
        r"```json",
        "",
        raw_text,
        flags=re.IGNORECASE
    )

    raw_text = re.sub(
        r"```",
        "",
        raw_text
    )

    raw_text = raw_text.strip()

    start = raw_text.find("[")
    end = raw_text.rfind("]")

    if start == -1 or end == -1:

        raise ValueError(
            "No JSON array found"
        )

    json_text = raw_text[
        start:end + 1
    ]

    try:

        return json.loads(
            json_text
        )

    except json.JSONDecodeError as e:

        print(
            "Persona JSON parsing failed:",
            e
        )

        json_text = re.sub(
            r"[\x00-\x1F]+",
            " ",
            json_text
        )

        return json.loads(
            json_text
        )


def extract_json_object(raw_text):

    raw_text = clean_text(raw_text)

    if not raw_text:

        raise ValueError(
            "Empty AI response"
        )

    raw_text = re.sub(
        r"```json",
        "",
        raw_text,
        flags=re.IGNORECASE
    )

    raw_text = re.sub(
        r"```",
        "",
        raw_text
    )

    raw_text = raw_text.strip()

    start = raw_text.find("{")
    end = raw_text.rfind("}")

    if start == -1 or end == -1:

        raise ValueError(
            "No JSON object found"
        )

    json_text = raw_text[
        start:end + 1
    ]

    try:

        return json.loads(
            json_text
        )

    except json.JSONDecodeError as e:

        print(
            "Insights JSON parsing failed:",
            e
        )

        json_text = re.sub(
            r"[\x00-\x1F]+",
            " ",
            json_text
        )

        return json.loads(
            json_text
        )


# ============================================================
# SAVE PERSONA MEMORY
# ============================================================

def save_persona_memory(
    experiment_name,
    product_name,
    description,
    audience,
    objective,
    domain,
    personas,
    survey_questions="",
    survey_responses=None
):

    memory = load_memory()

    experiment_name = normalize_experiment_name(
        experiment_name
    )

    if survey_responses is None:
        survey_responses = []

    existing = memory.get(
        experiment_name,
        {}
    )

    if not isinstance(
        existing,
        dict
    ):
        existing = {}

    experiment_data = {

        "experiment_name":
            experiment_name,

        "product_name":
            product_name,

        "description":
            description,

        "audience":
            audience,

        "objective":
            objective,

        "domain":
            domain,

        "personas":
            personas,

        "survey_history":
            existing.get(
                "survey_history",
                []
            ),

        "interview_history":
            existing.get(
                "interview_history",
                {}
            ),

        "created_at":
            existing.get(
                "created_at",
                datetime.now().isoformat()
            ),

        "updated_at":
            datetime.now().isoformat()
    }

    if survey_questions and survey_responses:

        experiment_data[
            "survey_history"
        ].append({

            "questions":
                survey_questions,

            "responses":
                survey_responses,

            "created_at":
                datetime.now().isoformat()
        })

    memory[
        experiment_name
    ] = experiment_data

    save_memory(memory)

    return experiment_data


# ============================================================
# FALLBACK PERSONA
# ============================================================

def create_fallback_persona(
    name,
    gender,
    age,
    product,
    domain,
    audience,
    objective,
    index
):

    return {

        "name":
            name,

        "age":
            age,

        "gender":
            gender,

        "background":
            (
                f"{name} is a {age}-year-old "
                f"{gender.lower()} belonging to the "
                f"target audience for {product}. "
                f"Their experiences are relevant to the "
                f"{domain} domain and their needs are "
                f"influenced by the research objective."
            ),

        "goals":
            (
                f"Wants to use {product} to solve "
                f"relevant problems efficiently, save "
                f"time and achieve practical outcomes. "
                f"Their main goal is aligned with the "
                f"research objective: {objective}."
            ),

        "behaviors":
            (
                f"Usually evaluates different options "
                f"before making decisions. Considers "
                f"usability, reliability, convenience, "
                f"cost and practical value when using "
                f"solutions related to {domain}."
            ),

        "preferences":
            (
                "Prefers simple interfaces, clear "
                "information, reliable performance, "
                "useful features, convenience and "
                "transparent pricing."
            ),

        "pain_points":
            (
                "May become frustrated by complicated "
                "processes, unclear information, high "
                "costs, poor usability, unreliable "
                "features or solutions that do not "
                "match their needs."
            ),

        "confidence":
            90 + (index % 10)
    }


# ============================================================
# PERSONA GENERATION
# ============================================================

def generate_personas(
    domain,
    product,
    description,
    audience,
    objective,
    count
):

    prompt = f"""
You are an expert UX researcher and synthetic
user persona generator.

Create EXACTLY {count} UNIQUE AI Digital Twin personas.

RESEARCH DOMAIN:
{domain}

PRODUCT / SERVICE:
{product}

PRODUCT DESCRIPTION:
{description}

TARGET AUDIENCE:
{audience}

RESEARCH OBJECTIVE:
{objective}

IMPORTANT:

1. Generate exactly {count} personas.
2. Every persona must be unique.
3. Use realistic Indian names.
4. Age must be between 18 and 60.
5. Gender must be Male or Female.
6. Do not include a job field.
7. Every persona must be strongly related to the domain.
8. Every persona must be strongly related to the product.
9. Target audience must influence the persona.
10. Research objective must influence the persona.
11. Background must be domain-specific.
12. Goals must be product-specific.
13. Behaviors must explain decision-making.
14. Preferences must describe usability, price,
    convenience, features and experience.
15. Pain points must be realistic.
16. Confidence must be between 90 and 99.
17. No null values.
18. No empty strings.
19. No N/A values.
20. Return ONLY valid JSON.
21. Do not return markdown.
22. Do not return explanations.

FORMAT:

[
    {{
        "name": "Indian Name",
        "age": 25,
        "gender": "Female",
        "background": "Detailed background",
        "goals": "Detailed goals",
        "behaviors": "Detailed behaviors",
        "preferences": "Detailed preferences",
        "pain_points": "Detailed pain points",
        "confidence": 95
    }}
]
"""

    try:

        response = client.chat.completions.create(

            model="openrouter/free",

            messages=[

                {
                    "role": "system",
                    "content": (
                        "You are a professional UX "
                        "research persona generator. "
                        "Return valid JSON only."
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.8
        )

        # ====================================================
        # ONLY CHANGE: SHOW RAW OPENROUTER RESPONSE
        # ====================================================

        raw_response = response.choices[0].message.content

        if not raw_response:
            raise ValueError(
                "Empty response received from OpenRouter"
            )

        print(
            "\n========== PERSONA AI RESPONSE =========="
        )

        print(raw_response)

        print(
            "=========================================\n"
        )

        raw_response = raw_response.strip()

        personas = extract_json_array(
            raw_response
        )

        if not isinstance(
            personas,
            list
        ):

            raise ValueError(
                "AI response is not a list"
            )

        cleaned_personas = []
        used_names = set()

        for persona in personas:

            if not isinstance(
                persona,
                dict
            ):
                continue

            name = clean_text(
                persona.get("name")
            )

            if not name:
                continue

            name_key = name.lower()

            if name_key in used_names:
                continue

            used_names.add(
                name_key
            )

            try:

                age = int(
                    persona.get(
                        "age",
                        25
                    )
                )

            except Exception:

                age = 25

            age = max(
                18,
                min(60, age)
            )

            gender = clean_text(
                persona.get(
                    "gender",
                    "Female"
                )
            )

            if gender.lower() == "male":

                gender = "Male"

            else:

                gender = "Female"

            background = clean_text(
                persona.get(
                    "background"
                )
            )

            goals = clean_text(
                persona.get(
                    "goals"
                )
            )

            behaviors = clean_text(
                persona.get(
                    "behaviors"
                )
            )

            preferences = clean_text(
                persona.get(
                    "preferences"
                )
            )

            pain_points = clean_text(
                persona.get(
                    "pain_points"
                )
            )

            if not background:

                background = (
                    f"{name} belongs to the "
                    f"target audience for {product} "
                    f"and has experiences relevant "
                    f"to the {domain} domain."
                )

            if not goals:

                goals = (
                    f"Wants to use {product} to "
                    f"solve relevant problems and "
                    f"achieve practical outcomes."
                )

            if not behaviors:

                behaviors = (
                    "Compares available options "
                    "before making decisions and "
                    "focuses on practical usefulness."
                )

            if not preferences:

                preferences = (
                    "Prefers simple interfaces, "
                    "clear information, convenience "
                    "and reliable features."
                )

            if not pain_points:

                pain_points = (
                    "May dislike complicated processes, "
                    "unclear information, high costs "
                    "and poor usability."
                )

            try:

                confidence = int(
                    persona.get(
                        "confidence",
                        95
                    )
                )

            except Exception:

                confidence = 95

            confidence = max(
                90,
                min(99, confidence)
            )

            cleaned_personas.append({

                "name":
                    name,

                "age":
                    age,

                "gender":
                    gender,

                "background":
                    background,

                "goals":
                    goals,

                "behaviors":
                    behaviors,

                "preferences":
                    preferences,

                "pain_points":
                    pain_points,

                "confidence":
                    confidence
            })

        fallback_names = [

            ("Arjun Kumar", "Male", 24),
            ("Priya Sharma", "Female", 27),
            ("Rahul Reddy", "Male", 31),
            ("Sneha Patel", "Female", 25),
            ("Kiran Rao", "Male", 29),
            ("Ananya Singh", "Female", 23),
            ("Vikram Kumar", "Male", 34),
            ("Divya Reddy", "Female", 30),
            ("Suresh Naidu", "Male", 38),
            ("Meena Devi", "Female", 35),
            ("Rohit Verma", "Male", 28),
            ("Kavya Rao", "Female", 26),
            ("Nikhil Reddy", "Male", 33),
            ("Pooja Sharma", "Female", 29),
            ("Aditya Kumar", "Male", 36)
        ]

        fallback_index = 0

        while len(cleaned_personas) < count:

            name, gender, age = fallback_names[
                fallback_index % len(
                    fallback_names
                )
            ]

            fallback_index += 1

            unique_name = name

            if unique_name.lower() in used_names:

                unique_name = (
                    f"{name} {fallback_index}"
                )

            used_names.add(
                unique_name.lower()
            )

            cleaned_personas.append(
                create_fallback_persona(
                    unique_name,
                    gender,
                    age,
                    product,
                    domain,
                    audience,
                    objective,
                    fallback_index
                )
            )

        return cleaned_personas[:count]

    except Exception as e:

        print(
            "Persona Generation Error:",
            e
        )

        traceback.print_exc()

        fallback_names = [

            ("Arjun Kumar", "Male", 24),
            ("Priya Sharma", "Female", 27),
            ("Rahul Reddy", "Male", 31),
            ("Sneha Patel", "Female", 25),
            ("Kiran Rao", "Male", 29),
            ("Ananya Singh", "Female", 23),
            ("Vikram Kumar", "Male", 34),
            ("Divya Reddy", "Female", 30),
            ("Suresh Naidu", "Male", 38),
            ("Meena Devi", "Female", 35),
            ("Rohit Verma", "Male", 28),
            ("Kavya Rao", "Female", 26),
            ("Nikhil Reddy", "Male", 33),
            ("Pooja Sharma", "Female", 29),
            ("Aditya Kumar", "Male", 36)
        ]

        fallback_personas = []

        for i in range(count):

            name, gender, age = fallback_names[
                i % len(
                    fallback_names
                )
            ]

            if i >= len(fallback_names):

                name = (
                    f"{name} {i + 1}"
                )

            fallback_personas.append(
                create_fallback_persona(
                    name,
                    gender,
                    age,
                    product,
                    domain,
                    audience,
                    objective,
                    i
                )
            )

        return fallback_personas


# ============================================================
# SURVEY RESPONSE GENERATION
# ============================================================

def generate_survey_responses(
    experiment,
    survey_questions
):

    personas = experiment.get(
        "personas",
        []
    )

    product = experiment.get(
        "product_name",
        ""
    )

    domain = experiment.get(
        "domain",
        ""
    )

    objective = experiment.get(
        "objective",
        ""
    )

    results = []

    for persona in personas:

        prompt = f"""
You are simulating an AI Digital Twin.

Answer completely as this persona.

NAME:
{persona.get("name")}

AGE:
{persona.get("age")}

GENDER:
{persona.get("gender")}

BACKGROUND:
{persona.get("background")}

GOALS:
{persona.get("goals")}

BEHAVIORS:
{persona.get("behaviors")}

PREFERENCES:
{persona.get("preferences")}

PAIN POINTS:
{persona.get("pain_points")}

PRODUCT:
{product}

DOMAIN:
{domain}

RESEARCH OBJECTIVE:
{objective}

SURVEY QUESTIONS:
{survey_questions}

RULES:

1. Stay completely in character.
2. Answer based on the stored persona.
3. Do not answer as an AI.
4. Do not mention synthetic users.
5. Keep answers realistic.
6. Keep answers consistent with persona memory.
7. Answer every question.
8. Return numbered answers.
"""

        try:

            response = client.chat.completions.create(

                model="openrouter/free",

                messages=[

                    {
                        "role": "system",
                        "content": (
                            "You are a realistic "
                            "synthetic research participant."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.7
            )

            answer = (
                response.choices[0]
                .message.content
                .strip()
            )

        except Exception as e:

            print(
                "Survey Response Error:",
                e
            )

            answer = (
                "AI response is temporarily "
                "unavailable. Please try again "
                "after the model limit resets."
            )

        results.append({

            "persona_name":
                persona.get(
                    "name",
                    "Unknown"
                ),

            "response":
                answer
        })

    return results


# ============================================================
# INTERVIEW RESPONSE
# ============================================================

def generate_interview_response(
    experiment,
    persona_index,
    message,
    history
):

    personas = experiment.get(
        "personas",
        []
    )

    if (
        persona_index < 0
        or persona_index >= len(personas)
    ):

        return "Persona not found."

    persona = personas[
        persona_index
    ]

    history_text = ""

    for item in history[-10:]:

        role = item.get(
            "role",
            ""
        )

        content = item.get(
            "content",
            ""
        )

        history_text += (
            f"{role}: {content}\n"
        )

    prompt = f"""
You are an AI Digital Twin participating
in a user interview.

Stay completely in character.

PERSONA:

Name: {persona.get("name")}
Age: {persona.get("age")}
Gender: {persona.get("gender")}

Background:
{persona.get("background")}

Goals:
{persona.get("goals")}

Behaviors:
{persona.get("behaviors")}

Preferences:
{persona.get("preferences")}

Pain Points:
{persona.get("pain_points")}

Product:
{experiment.get("product_name")}

Domain:
{experiment.get("domain")}

Research Objective:
{experiment.get("objective")}

PREVIOUS INTERVIEW:

{history_text}

INTERVIEWER QUESTION:

{message}

RULES:

1. Answer naturally as the persona.
2. Do not say you are an AI.
3. Do not mention persona generation.
4. Stay consistent with stored persona memory.
5. Give realistic opinions.
6. Connect product answers to persona goals,
   preferences and pain points.
7. Do not invent unrelated information.
8. Respond conversationally.
"""

    try:

        response = client.chat.completions.create(

            model="openrouter/free",

            messages=[

                {
                    "role": "system",
                    "content": (
                        "You are conducting a realistic "
                        "synthetic user interview."
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.7
        )

        return (
            response.choices[0]
            .message.content
            .strip()
        )

    except Exception as e:

        print(
            "Interview Response Error:",
            e
        )

        return (
            "AI interview response is temporarily "
            "unavailable. Please try again after "
            "the model limit resets."
        )


# ============================================================
# DEFAULT INSIGHTS
# ============================================================

def default_research_insights():

    return {

        "would_use_product": {

            "score": 0,

            "segments": []
        },

        "sentiment": {

            "positive": 0,

            "neutral": 0,

            "negative": 0
        },

        "recurring_themes": [],

        "agreement_patterns": [],

        "behavioral_trends": [],

        "key_insights": []
    }


# ============================================================
# RESEARCH INSIGHTS
# ============================================================

def generate_research_insights(
    experiment
):

    default = default_research_insights()

    personas = experiment.get(
        "personas",
        []
    )

    survey_history = experiment.get(
        "survey_history",
        []
    )

    interview_history = experiment.get(
        "interview_history",
        {}
    )

    product = clean_text(
        experiment.get(
            "product_name",
            ""
        )
    )

    domain = clean_text(
        experiment.get(
            "domain",
            ""
        )
    )

    objective = clean_text(
        experiment.get(
            "objective",
            ""
        )
    )

    audience = clean_text(
        experiment.get(
            "audience",
            ""
        )
    )

    # --------------------------------------------------------
    # PERSONA DATA
    # --------------------------------------------------------

    persona_text = ""

    for index, persona in enumerate(
        personas,
        start=1
    ):

        persona_text += f"""
PERSONA {index}

Name:
{persona.get("name", "")}

Age:
{persona.get("age", "")}

Gender:
{persona.get("gender", "")}

Background:
{persona.get("background", "")}

Goals:
{persona.get("goals", "")}

Behaviors:
{persona.get("behaviors", "")}

Preferences:
{persona.get("preferences", "")}

Pain Points:
{persona.get("pain_points", "")}

Confidence:
{persona.get("confidence", "")}

--------------------------------
"""

    # --------------------------------------------------------
    # SURVEY DATA
    # --------------------------------------------------------

    survey_text = ""

    for index, survey in enumerate(
        survey_history,
        start=1
    ):

        questions = clean_text(
            survey.get(
                "questions",
                ""
            )
        )

        responses = survey.get(
            "responses",
            []
        )

        survey_text += f"""
SURVEY SESSION {index}

QUESTIONS:
{questions}

RESPONSES:
{json.dumps(
    responses,
    ensure_ascii=False,
    indent=2
)}

--------------------------------
"""

    # --------------------------------------------------------
    # INTERVIEW DATA
    # --------------------------------------------------------

    interview_text = ""

    if isinstance(
        interview_history,
        dict
    ):

        for persona_index, history in interview_history.items():

            interview_text += (
                f"\nINTERVIEW WITH PERSONA "
                f"{persona_index}\n"
            )

            if isinstance(
                history,
                list
            ):

                for item in history:

                    role = clean_text(
                        item.get(
                            "role",
                            ""
                        )
                    )

                    content = clean_text(
                        item.get(
                            "content",
                            ""
                        )
                    )

                    if content:

                        interview_text += (
                            f"{role.upper()}: "
                            f"{content}\n"
                        )

            interview_text += (
                "--------------------------------\n"
            )

    # --------------------------------------------------------
    # CHECK DATA
    # --------------------------------------------------------

    if (
        not personas
        and not survey_history
        and not interview_history
    ):

        return default

    # --------------------------------------------------------
    # AI PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are an expert UX research analyst working
inside SynTwin AI.

Analyze the available synthetic user research.

EXPERIMENT INFORMATION

Product:
{product}

Research Domain:
{domain}

Target Audience:
{audience}

Research Objective:
{objective}


PERSONA DATA

{persona_text}


SURVEY DATA

{survey_text}


INTERVIEW DATA

{interview_text}


IMPORTANT ANALYSIS RULES:

1. Use ONLY information available in the
   persona, survey and interview data.

2. Do not invent specific user opinions that
   are not supported by the available data.

3. If survey responses exist, analyze them.

4. If interview responses exist, analyze them.

5. If survey/interview data is limited, use the
   available persona information and clearly keep
   the findings at persona-analysis level.

6. Every section MUST contain useful information.

7. Do NOT return empty arrays.

8. Keep findings specific to the product,
   domain, target audience and objective.

9. Use actual persona names whenever possible.

10. Generate multiple findings where enough
    information exists.

11. Do not use generic unrelated research findings.

12. Do not return markdown.

13. Return ONLY valid JSON.


RETURN EXACTLY THIS JSON STRUCTURE:

{{
    "would_use_product": {{
        "score": 75,
        "segments": [
            {{
                "group": "Interested users",
                "personas": [
                    "Persona Name"
                ],
                "reasoning": "Detailed reasoning based on the available research."
            }}
        ]
    }},

    "sentiment": {{
        "positive": 60,
        "neutral": 25,
        "negative": 15
    }},

    "recurring_themes": [
        {{
            "theme": "Usability",
            "description": "Detailed description of the recurring theme.",
            "frequency": "High"
        }},
        {{
            "theme": "Convenience",
            "description": "Detailed description of the recurring theme.",
            "frequency": "Medium"
        }},
        {{
            "theme": "Practical Value",
            "description": "Detailed description of the recurring theme.",
            "frequency": "Medium"
        }}
    ],

    "agreement_patterns": [
        "Detailed agreement pattern 1.",
        "Detailed agreement pattern 2."
    ],

    "behavioral_trends": [
        "Detailed behavioral trend 1.",
        "Detailed behavioral trend 2."
    ],

    "key_insights": [
        "Detailed key research insight 1.",
        "Detailed key research insight 2.",
        "Detailed key research insight 3."
    ]
}}

RULES:

1. would_use_product.score must be between 0 and 100.

2. Sentiment values must be between 0 and 100.

3. If response data exists, positive + neutral +
   negative should approximately equal 100.

4. Use actual persona names in segments.

5. Recurring themes should contain at least
   3 useful findings.

6. Agreement patterns should contain at least
   2 useful findings.

7. Behavioral trends should contain at least
   2 useful findings.

8. Key insights should contain at least
   3 useful findings.

9. Do not return empty strings.

10. Do not return null values.

11. Do not return markdown.

12. Do not add explanations outside JSON.
"""

    # --------------------------------------------------------
    # AI CALL
    # --------------------------------------------------------

    try:

        response = client.chat.completions.create(

            model="openrouter/free",

            messages=[

                {
                    "role": "system",
                    "content": (
                        "You are a professional UX "
                        "research insight extraction agent. "
                        "Analyze the research data carefully "
                        "and return valid JSON only."
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.3
        )

        raw = (
            response.choices[0]
            .message.content
            .strip()
        )

        print(
            "\n========== RESEARCH INSIGHTS AI RESPONSE =========="
        )

        print(raw)

        print(
            "====================================================\n"
        )

        insights = extract_json_object(
            raw
        )

        if not isinstance(
            insights,
            dict
        ):

            raise ValueError(
                "Insights response is not an object"
            )

        # ----------------------------------------------------
        # WOULD USE PRODUCT
        # ----------------------------------------------------

        would_use = insights.get(
            "would_use_product"
        )

        if not isinstance(
            would_use,
            dict
        ):

            would_use = {}

        try:

            score = int(
                would_use.get(
                    "score",
                    0
                )
            )

        except Exception:

            score = 0

        score = max(
            0,
            min(100, score)
        )

        segments = would_use.get(
            "segments",
            []
        )

        if not isinstance(
            segments,
            list
        ):

            segments = []

        clean_segments = []

        for segment in segments:

            if not isinstance(
                segment,
                dict
            ):
                continue

            group = clean_text(
                segment.get(
                    "group",
                    ""
                )
            )

            personas_list = segment.get(
                "personas",
                []
            )

            if not isinstance(
                personas_list,
                list
            ):

                personas_list = []

            clean_personas = []

            for persona_name in personas_list:

                persona_name = clean_text(
                    persona_name
                )

                if persona_name:

                    clean_personas.append(
                        persona_name
                    )

            reasoning = clean_text(
                segment.get(
                    "reasoning",
                    ""
                )
            )

            if not group:

                group = "Research Segment"

            if not reasoning:

                reasoning = (
                    "This segment is based on "
                    "similarities observed in the "
                    "available research data."
                )

            clean_segments.append({

                "group":
                    group,

                "personas":
                    clean_personas,

                "reasoning":
                    reasoning
            })

        if not clean_segments and personas:

            persona_names = [

                clean_text(
                    p.get(
                        "name",
                        ""
                    )
                )

                for p in personas

                if clean_text(
                    p.get(
                        "name",
                        ""
                    )
                )
            ]

            if persona_names:

                clean_segments.append({

                    "group":
                        "Primary Target Audience",

                    "personas":
                        persona_names,

                    "reasoning":
                        (
                            f"These synthetic personas "
                            f"represent the defined target "
                            f"audience for {product} in the "
                            f"{domain} domain."
                        )
                })

        insights[
            "would_use_product"
        ] = {

            "score":
                score,

            "segments":
                clean_segments
        }

        # ----------------------------------------------------
        # SENTIMENT
        # ----------------------------------------------------

        sentiment = insights.get(
            "sentiment"
        )

        if not isinstance(
            sentiment,
            dict
        ):

            sentiment = {}

        clean_sentiment = {}

        for key in [
            "positive",
            "neutral",
            "negative"
        ]:

            try:

                value = int(
                    sentiment.get(
                        key,
                        0
                    )
                )

            except Exception:

                value = 0

            clean_sentiment[
                key
            ] = max(
                0,
                min(100, value)
            )

        if (
            clean_sentiment["positive"] == 0
            and clean_sentiment["neutral"] == 0
            and clean_sentiment["negative"] == 0
        ):

            clean_sentiment = {

                "positive":
                    50,

                "neutral":
                    30,

                "negative":
                    20
            }

        insights[
            "sentiment"
        ] = clean_sentiment

        # ----------------------------------------------------
        # RECURRING THEMES
        # ----------------------------------------------------

        recurring_themes = insights.get(
            "recurring_themes",
            []
        )

        if not isinstance(
            recurring_themes,
            list
        ):

            recurring_themes = []

        clean_themes = []

        for theme in recurring_themes:

            if not isinstance(
                theme,
                dict
            ):
                continue

            theme_name = clean_text(
                theme.get(
                    "theme",
                    ""
                )
            )

            description_text = clean_text(
                theme.get(
                    "description",
                    ""
                )
            )

            frequency = clean_text(
                theme.get(
                    "frequency",
                    "Medium"
                )
            )

            if theme_name:

                if not description_text:

                    description_text = (
                        f"{theme_name} appears as a "
                        "recurring consideration in "
                        "the available research."
                    )

                clean_themes.append({

                    "theme":
                        theme_name,

                    "description":
                        description_text,

                    "frequency":
                        frequency
                })

        if not clean_themes:

            clean_themes = [

                {
                    "theme":
                        "Usability",

                    "description":
                        (
                            "Personas show an interest "
                            "in simple, understandable "
                            "and easy-to-use experiences."
                        ),

                    "frequency":
                        "High"
                },

                {
                    "theme":
                        "Convenience",

                    "description":
                        (
                            "Convenience and reduced "
                            "effort are important "
                            "considerations for the "
                            "synthetic users."
                        ),

                    "frequency":
                        "Medium"
                },

                {
                    "theme":
                        "Practical Value",

                    "description":
                        (
                            f"Personas evaluate whether "
                            f"{product} can provide "
                            "practical value for their "
                            "needs."
                        ),

                    "frequency":
                        "Medium"
                }
            ]

        insights[
            "recurring_themes"
        ] = clean_themes

        # ----------------------------------------------------
        # AGREEMENT PATTERNS
        # ----------------------------------------------------

        agreement_patterns = insights.get(
            "agreement_patterns",
            []
        )

        if not isinstance(
            agreement_patterns,
            list
        ):

            agreement_patterns = []

        clean_agreements = [

            clean_text(item)

            for item in agreement_patterns

            if clean_text(item)
        ]

        if not clean_agreements:

            clean_agreements = [

                (
                    "Multiple personas value "
                    "clear and easy-to-understand "
                    "product experiences."
                ),

                (
                    "Personas generally consider "
                    "convenience and practical "
                    "usefulness when evaluating "
                    "solutions."
                )
            ]

        insights[
            "agreement_patterns"
        ] = clean_agreements

        # ----------------------------------------------------
        # BEHAVIORAL TRENDS
        # ----------------------------------------------------

        behavioral_trends = insights.get(
            "behavioral_trends",
            []
        )

        if not isinstance(
            behavioral_trends,
            list
        ):

            behavioral_trends = []

        clean_behaviors = [

            clean_text(item)

            for item in behavioral_trends

            if clean_text(item)
        ]

        if not clean_behaviors:

            clean_behaviors = [

                (
                    "Users tend to compare available "
                    "options before making decisions."
                ),

                (
                    "Users consider usability, "
                    "reliability and convenience "
                    "when evaluating solutions."
                )
            ]

        insights[
            "behavioral_trends"
        ] = clean_behaviors

        # ----------------------------------------------------
        # KEY INSIGHTS
        # ----------------------------------------------------

        key_insights = insights.get(
            "key_insights",
            []
        )

        if not isinstance(
            key_insights,
            list
        ):

            key_insights = []

        clean_key_insights = [

            clean_text(item)

            for item in key_insights

            if clean_text(item)
        ]

        if not clean_key_insights:

            clean_key_insights = [

                (
                    f"The synthetic personas indicate "
                    f"that {product} should provide "
                    "clear practical value to the "
                    "target audience."
                ),

                (
                    f"Usability and convenience are "
                    f"important considerations within "
                    f"the {domain} research context."
                ),

                (
                    f"The findings should be interpreted "
                    f"against the research objective: "
                    f"{objective}"
                )
            ]

        insights[
            "key_insights"
        ] = clean_key_insights

        return insights

    except Exception as e:

        print(
            "\n========== INSIGHTS ERROR =========="
        )

        print(
            str(e)
        )

        traceback.print_exc()

        print(
            "====================================\n"
        )

        persona_names = [

            clean_text(
                persona.get(
                    "name",
                    ""
                )
            )

            for persona in personas

            if clean_text(
                persona.get(
                    "name",
                    ""
                )
            )
        ]

        fallback_segments = []

        if persona_names:

            fallback_segments.append({

                "group":
                    "Synthetic Target Users",

                "personas":
                    persona_names,

                "reasoning":
                    (
                        f"The generated personas represent "
                        f"the defined target audience for "
                        f"{product} in the {domain} domain."
                    )
            })

        return {

            "would_use_product": {

                "score":
                    0,

                "segments":
                    fallback_segments
            },

            "sentiment": {

                "positive":
                    50,

                "neutral":
                    30,

                "negative":
                    20
            },

            "recurring_themes": [

                {
                    "theme":
                        "Usability",

                    "description":
                        (
                            "Personas generally prefer "
                            "simple and easy-to-use "
                            "experiences."
                        ),

                    "frequency":
                        "High"
                },

                {
                    "theme":
                        "Convenience",

                    "description":
                        (
                            "Convenience and reduced "
                            "effort are common "
                            "considerations."
                        ),

                    "frequency":
                        "Medium"
                },

                {
                    "theme":
                        "Practical Value",

                    "description":
                        (
                            f"Users evaluate whether "
                            f"{product} can provide "
                            "practical value for their "
                            "needs."
                        ),

                    "frequency":
                        "Medium"
                }
            ],

            "agreement_patterns": [

                (
                    "Multiple personas value "
                    "simple and understandable "
                    "product experiences."
                ),

                (
                    "Personas consider convenience "
                    "and practical usefulness when "
                    "evaluating solutions."
                )
            ],

            "behavioral_trends": [

                (
                    "Users tend to compare options "
                    "before making decisions."
                ),

                (
                    "Users consider usability, "
                    "reliability and convenience "
                    "during evaluation."
                )
            ],

            "key_insights": [

                (
                    f"{product} should provide clear "
                    f"practical value for the defined "
                    f"target audience."
                ),

                (
                    f"Usability and convenience are "
                    f"important considerations in the "
                    f"{domain} domain."
                ),

                (
                    f"Further survey and interview "
                    f"responses can provide stronger "
                    f"evidence for the research objective."
                )
            ]
        }


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def home(
    request: Request
):

    return templates.TemplateResponse(
        "experiment.html",
        {
            "request": request
        }
    )


# ============================================================
# CREATE EXPERIMENT
# ============================================================

@app.post("/dashboard")
async def create_experiment(
    request: Request,
    experiment_name: str = Form(...),
    product_name: str = Form(...),
    description: str = Form(...),
    audience: str = Form(...),
    objective: str = Form(...),
    personas: int = Form(...),
    simulation: str = Form(...)
):

    experiment_name = clean_text(
        experiment_name
    )

    product_name = clean_text(
        product_name
    )

    description = clean_text(
        description
    )

    audience = clean_text(
        audience
    )

    objective = clean_text(
        objective
    )

    simulation = clean_text(
        simulation
    )

    personas = max(
        1,
        min(50, personas)
    )

    generated_personas = generate_personas(
        domain=simulation,
        product=product_name,
        description=description,
        audience=audience,
        objective=objective,
        count=personas
    )

    experiment_data = save_persona_memory(
        experiment_name=experiment_name,
        product_name=product_name,
        description=description,
        audience=audience,
        objective=objective,
        domain=simulation,
        personas=generated_personas
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request":
                request,

            "experiment":
                experiment_name,

            "product":
                product_name,

            "description":
                description,

            "audience":
                audience,

            "objective":
                objective,

            "simulation":
                simulation,

            "personas":
                generated_personas,

            "survey_history":
                experiment_data.get(
                    "survey_history",
                    []
                )
        }
    )


# ============================================================
# LOAD PREVIOUS EXPERIMENT
# ============================================================

@app.get("/load-experiment")
async def load_experiment(
    request: Request,
    experiment_name: str
):

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return templates.TemplateResponse(
            "experiment.html",
            {
                "request":
                    request,

                "error":
                    "Experiment not found."
            }
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {

            "request":
                request,

            "experiment":
                experiment.get(
                    "experiment_name",
                    experiment_name
                ),

            "product":
                experiment.get(
                    "product_name",
                    ""
                ),

            "description":
                experiment.get(
                    "description",
                    ""
                ),

            "audience":
                experiment.get(
                    "audience",
                    ""
                ),

            "objective":
                experiment.get(
                    "objective",
                    ""
                ),

            "simulation":
                experiment.get(
                    "domain",
                    ""
                ),

            "personas":
                experiment.get(
                    "personas",
                    []
                ),

            "survey_history":
                experiment.get(
                    "survey_history",
                    []
                )
        }
    )


# ============================================================
# SURVEY
# ============================================================

@app.post("/survey")
async def survey(
    request: Request,
    experiment_name: str = Form(...),
    survey_questions: str = Form(...)
):

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return {

            "status":
                "error",

            "message":
                "Experiment not found."
        }

    survey_questions = clean_text(
        survey_questions
    )

    responses = generate_survey_responses(
        experiment,
        survey_questions
    )

    memory = load_memory()

    key = experiment.get(
        "experiment_name",
        experiment_name
    )

    if key not in memory:

        memory[key] = experiment

    memory[key].setdefault(
        "survey_history",
        []
    )

    memory[key][
        "survey_history"
    ].append({

        "questions":
            survey_questions,

        "responses":
            responses,

        "created_at":
            datetime.now().isoformat()
    })

    memory[key][
        "updated_at"
    ] = datetime.now().isoformat()

    save_memory(memory)

    return templates.TemplateResponse(
        "survey_results.html",
        {

            "request":
                request,

            "experiment":
                experiment_name,

            "survey_questions":
                survey_questions,

            "responses":
                responses
        }
    )


# ============================================================
# INTERVIEW
# ============================================================

@app.post("/interview")
async def interview(
    request: Request
):

    data = await request.json()

    experiment_name = clean_text(
        data.get(
            "experiment_name",
            ""
        )
    )

    persona_index = data.get(
        "persona_index"
    )

    message = clean_text(
        data.get(
            "message",
            ""
        )
    )

    try:

        persona_index = int(
            persona_index
        )

    except Exception:

        persona_index = -1

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return {

            "status":
                "error",

            "message":
                "Experiment not found."
        }

    if (
        persona_index < 0
        or persona_index >= len(
            experiment.get(
                "personas",
                []
            )
        )
    ):

        return {

            "status":
                "error",

            "message":
                "Persona not found."
        }

    memory = load_memory()

    key = experiment.get(
        "experiment_name",
        experiment_name
    )

    memory[key].setdefault(
        "interview_history",
        {}
    )

    history_key = str(
        persona_index
    )

    history = memory[key][
        "interview_history"
    ].setdefault(
        history_key,
        []
    )

    response = generate_interview_response(
        experiment,
        persona_index,
        message,
        history
    )

    history.append({

        "role":
            "user",

        "content":
            message,

        "timestamp":
            datetime.now().isoformat()
    })

    history.append({

        "role":
            "assistant",

        "content":
            response,

        "timestamp":
            datetime.now().isoformat()
    })

    memory[key][
        "updated_at"
    ] = datetime.now().isoformat()

    save_memory(memory)

    return {

        "status":
            "success",

        "response":
            response
    }


# ============================================================
# INTERVIEW HISTORY
# ============================================================

@app.get("/interview/history")
async def interview_history(
    experiment_name: str,
    persona_index: int
):

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return {

            "status":
                "error",

            "history":
                []
        }

    history = experiment.get(
        "interview_history",
        {}
    ).get(
        str(persona_index),
        []
    )

    return {

        "status":
            "success",

        "history":
            history
    }


# ============================================================
# CLEAR INTERVIEW
# ============================================================

@app.post("/interview/clear")
async def clear_interview(
    request: Request
):

    data = await request.json()

    experiment_name = clean_text(
        data.get(
            "experiment_name",
            ""
        )
    )

    try:

        persona_index = int(
            data.get(
                "persona_index",
                -1
            )
        )

    except Exception:

        persona_index = -1

    memory = load_memory()

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return {

            "status":
                "error",

            "message":
                "Experiment not found."
        }

    key = experiment.get(
        "experiment_name",
        experiment_name
    )

    if key in memory:

        memory[key].setdefault(
            "interview_history",
            {}
        )

        memory[key][
            "interview_history"
        ][str(persona_index)] = []

        memory[key][
            "updated_at"
        ] = datetime.now().isoformat()

        save_memory(memory)

    return {

        "status":
            "success"
    }


# ============================================================
# INSIGHTS
# ============================================================

@app.get("/insights")
async def insights_page(
    request: Request,
    experiment_name: str
):

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return templates.TemplateResponse(
            "insights.html",
            {

                "request":
                    request,

                "experiment":
                    {
                        "experiment_name":
                            experiment_name
                    },

                "insights":
                    default_research_insights(),

                "error":
                    "Experiment not found."
            }
        )

    insights = generate_research_insights(
        experiment
    )

    return templates.TemplateResponse(
        "insights.html",
        {

            "request":
                request,

            "experiment":
                experiment,

            "insights":
                insights
        }
    )


# ============================================================
# PERSONA MEMORY API
# ============================================================

@app.get("/persona-memory")
async def persona_memory():

    return load_memory()


@app.get(
    "/persona-memory/{experiment_name}"
)
async def persona_memory_experiment(
    experiment_name: str
):

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return {

            "status":
                "error",

            "message":
                "Experiment not found."
        }

    return experiment


# ============================================================
# PDF HELPERS
# ============================================================

def pdf_paragraph(
    text,
    style
):

    return Paragraph(
        clean_text(text).replace(
            "\n",
            "<br/>"
        ),
        style
    )


def list_to_text(value):

    if isinstance(
        value,
        list
    ):

        return "; ".join(
            clean_text(item)
            for item in value
        )

    return clean_text(value)


# ============================================================
# BUILD PDF REPORT
# ============================================================

def build_pdf_report(
    experiment,
    output_path
):

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        alignment=TA_CENTER,
        textColor=colors.HexColor(
            "#00B8D4"
        ),
        spaceAfter=15
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=15,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor(
            "#444444"
        ),
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading1"],
        fontSize=19,
        leading=24,
        textColor=colors.HexColor(
            "#18202A"
        ),
        spaceBefore=10,
        spaceAfter=12
    )

    subheading_style = ParagraphStyle(
        "ReportSubHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor(
            "#008CA3"
        ),
        spaceBefore=8,
        spaceAfter=7
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor(
            "#333333"
        ),
        spaceAfter=7
    )

    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor(
            "#555555"
        )
    )

    quote_style = ParagraphStyle(
        "ReportQuote",
        parent=body_style,
        leftIndent=12,
        rightIndent=12,
        fontSize=9,
        leading=14,
        textColor=colors.HexColor(
            "#444444"
        )
    )

    document = SimpleDocTemplate(

        output_path,

        pagesize=A4,

        rightMargin=18 * mm,

        leftMargin=18 * mm,

        topMargin=18 * mm,

        bottomMargin=18 * mm
    )

    story = []

    experiment_name = experiment.get(
        "experiment_name",
        "Untitled Experiment"
    )

    product = experiment.get(
        "product_name",
        ""
    )

    description = experiment.get(
        "description",
        ""
    )

    audience = experiment.get(
        "audience",
        ""
    )

    objective = experiment.get(
        "objective",
        ""
    )

    domain = experiment.get(
        "domain",
        ""
    )

    personas = experiment.get(
        "personas",
        []
    )

    survey_history = experiment.get(
        "survey_history",
        []
    )

    # ========================================================
    # COVER
    # ========================================================

    story.append(
        Spacer(
            1,
            45 * mm
        )
    )

    story.append(
        Paragraph(
            "SynTwin AI",
            title_style
        )
    )

    story.append(
        Paragraph(
            "AI Digital Twin Research Report",
            subtitle_style
        )
    )

    story.append(
        Spacer(
            1,
            12 * mm
        )
    )

    cover_data = [

        [
            Paragraph(
                "<b>Experiment</b>",
                body_style
            ),

            Paragraph(
                clean_text(experiment_name),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Product / Service</b>",
                body_style
            ),

            Paragraph(
                clean_text(product),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Research Domain</b>",
                body_style
            ),

            Paragraph(
                clean_text(domain),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>AI Digital Twins</b>",
                body_style
            ),

            Paragraph(
                str(len(personas)),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Survey Sessions</b>",
                body_style
            ),

            Paragraph(
                str(len(survey_history)),
                body_style
            )
        ]
    ]

    cover_table = Table(
        cover_data,
        colWidths=[
            50 * mm,
            105 * mm
        ]
    )

    cover_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#E8F8FA"
                )
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#C7D8DD"
                )
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                9
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                9
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )

    story.append(
        cover_table
    )

    story.append(
        Spacer(
            1,
            20 * mm
        )
    )

    story.append(
        Paragraph(
            "Generated by SynTwin AI",
            small_style
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================

    story.append(
        Paragraph(
            "1. Executive Summary",
            heading_style
        )
    )

    summary = (
        f"This research report presents synthetic user "
        f"research conducted for "
        f"<b>{clean_text(product)}</b> in the "
        f"<b>{clean_text(domain)}</b> domain. "
        f"SynTwin AI generated {len(personas)} "
        f"AI Digital Twins based on the defined "
        f"target audience and research objective."
    )

    story.append(
        Paragraph(
            summary,
            body_style
        )
    )

    if objective:

        story.append(
            Paragraph(
                f"<b>Research Objective:</b> "
                f"{clean_text(objective)}",
                body_style
            )
        )

    # ========================================================
    # PRODUCT & RESEARCH SETUP
    # ========================================================

    story.append(
        Paragraph(
            "2. Product & Research Setup",
            heading_style
        )
    )

    setup_data = [

        [
            Paragraph(
                "<b>Product / Service</b>",
                body_style
            ),

            Paragraph(
                clean_text(product),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Description</b>",
                body_style
            ),

            Paragraph(
                clean_text(description),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Target Audience</b>",
                body_style
            ),

            Paragraph(
                clean_text(audience),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Research Objective</b>",
                body_style
            ),

            Paragraph(
                clean_text(objective),
                body_style
            )
        ],

        [
            Paragraph(
                "<b>Research Domain</b>",
                body_style
            ),

            Paragraph(
                clean_text(domain),
                body_style
            )
        ]
    ]

    setup_table = Table(
        setup_data,
        colWidths=[
            48 * mm,
            107 * mm
        ]
    )

    setup_table.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D0D7DE"
                )
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#F2F7F8"
                )
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(
        setup_table
    )

    # ========================================================
    # PERSONA OVERVIEW
    # ========================================================

    story.append(
        Paragraph(
            "3. Synthetic Persona Overview",
            heading_style
        )
    )

    persona_table_data = [[

        Paragraph(
            "<b>Name</b>",
            small_style
        ),

        Paragraph(
            "<b>Age</b>",
            small_style
        ),

        Paragraph(
            "<b>Gender</b>",
            small_style
        ),

        Paragraph(
            "<b>Confidence</b>",
            small_style
        )
    ]]

    for persona in personas:

        persona_table_data.append([

            Paragraph(
                clean_text(
                    persona.get("name")
                ),
                small_style
            ),

            Paragraph(
                str(
                    persona.get(
                        "age",
                        ""
                    )
                ),
                small_style
            ),

            Paragraph(
                clean_text(
                    persona.get(
                        "gender"
                    )
                ),
                small_style
            ),

            Paragraph(
                f"{persona.get('confidence', 0)}%",
                small_style
            )
        ])

    persona_table = Table(
        persona_table_data,
        colWidths=[
            65 * mm,
            25 * mm,
            30 * mm,
            35 * mm
        ],
        repeatRows=1
    )

    persona_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#DDF6F8"
                )
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#CBD5DB"
                )
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    story.append(
        persona_table
    )

    # ========================================================
    # PERSONA DETAILS
    # ========================================================

    story.append(
        Paragraph(
            "4. Persona Behavioural Details",
            heading_style
        )
    )

    for index, persona in enumerate(
        personas,
        start=1
    ):

        story.append(
            Paragraph(
                f"{index}. "
                f"{clean_text(persona.get('name'))}",
                subheading_style
            )
        )

        details = [

            (
                "Background",
                persona.get("background")
            ),

            (
                "Goals",
                persona.get("goals")
            ),

            (
                "Behaviors",
                persona.get("behaviors")
            ),

            (
                "Preferences",
                persona.get("preferences")
            ),

            (
                "Pain Points",
                persona.get("pain_points")
            )
        ]

        for label, value in details:

            story.append(
                Paragraph(
                    f"<b>{label}:</b> "
                    f"{clean_text(value)}",
                    body_style
                )
            )

    # ========================================================
    # SURVEY RESULTS
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "5. Survey Results",
            heading_style
        )
    )

    if survey_history:

        latest_survey = survey_history[-1]

        questions = latest_survey.get(
            "questions",
            ""
        )

        responses = latest_survey.get(
            "responses",
            []
        )

        story.append(
            Paragraph(
                "<b>Survey Questions</b>",
                subheading_style
            )
        )

        story.append(
            Paragraph(
                clean_text(
                    questions
                ).replace(
                    "\n",
                    "<br/>"
                ),
                body_style
            )
        )

        story.append(
            Paragraph(
                "<b>Persona Responses</b>",
                subheading_style
            )
        )

        for response in responses:

            name = response.get(
                "persona_name",
                "Persona"
            )

            answer = response.get(
                "response",
                ""
            )

            story.append(
                KeepTogether([

                    Paragraph(
                        clean_text(name),
                        subheading_style
                    ),

                    Paragraph(
                        clean_text(
                            answer
                        ).replace(
                            "\n",
                            "<br/>"
                        ),
                        body_style
                    ),

                    Spacer(
                        1,
                        4 * mm
                    )
                ])
            )

    else:

        story.append(
            Paragraph(
                "No survey has been conducted yet.",
                body_style
            )
        )

    # ========================================================
    # REPRESENTATIVE QUOTES
    # ========================================================

    story.append(
        Paragraph(
            "6. Representative Persona Quotes",
            heading_style
        )
    )

    if survey_history:

        responses = survey_history[
            -1
        ].get(
            "responses",
            []
        )

        for response in responses:

            name = clean_text(
                response.get(
                    "persona_name",
                    "Persona"
                )
            )

            answer = clean_text(
                response.get(
                    "response",
                    ""
                )
            )

            quote = answer.split(
                "\n"
            )[0].strip()

            if len(quote) > 250:

                quote = (
                    quote[:250] +
                    "..."
                )

            story.append(
                Paragraph(
                    f'<b>{name}:</b> '
                    f'"{quote}"',
                    quote_style
                )
            )

            story.append(
                Spacer(
                    1,
                    3 * mm
                )
            )

    else:

        story.append(
            Paragraph(
                "Representative quotes will appear "
                "after survey research is conducted.",
                body_style
            )
        )

    # ========================================================
    # CONCLUSION
    # ========================================================

    story.append(
        Paragraph(
            "7. Conclusion",
            heading_style
        )
    )

    conclusion = (
        f"SynTwin AI created {len(personas)} "
        f"synthetic digital twins for the research "
        f"experiment <b>{clean_text(experiment_name)}</b>. "
        f"The personas were generated using the product, "
        f"research domain, target audience and research "
        f"objective to support consistent synthetic "
        f"user research."
    )

    story.append(
        Paragraph(
            conclusion,
            body_style
        )
    )

    story.append(
        Spacer(
            1,
            8 * mm
        )
    )

    story.append(
        Paragraph(
            "This report is generated using synthetic AI "
            "personas and should be interpreted as simulated "
            "research rather than direct evidence from real users.",
            small_style
        )
    )

    # ========================================================
    # PAGE NUMBER
    # ========================================================

    def add_page_number(
        canvas,
        doc
    ):

        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            8
        )

        canvas.setFillColor(
            colors.HexColor(
                "#777777"
            )
        )

        canvas.drawCentredString(
            A4[0] / 2,
            10 * mm,
            f"SynTwin AI • Page {doc.page}"
        )

        canvas.restoreState()

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )


# ============================================================
# PDF DOWNLOAD
# ============================================================

@app.get(
    "/download-report/{experiment_name}"
)
async def download_report(
    experiment_name: str
):

    experiment = get_experiment_from_memory(
        experiment_name
    )

    if experiment is None:

        return {

            "status":
                "error",

            "message":
                "Experiment not found."
        }

    os.makedirs(
        REPORT_FOLDER,
        exist_ok=True
    )

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        experiment_name
    )

    pdf_path = os.path.join(
        REPORT_FOLDER,
        f"SynTwin_AI_{safe_name}_Research_Report.pdf"
    )

    try:

        build_pdf_report(
            experiment,
            pdf_path
        )

    except Exception as e:

        print(
            "PDF Generation Error:",
            e
        )

        traceback.print_exc()

        return {

            "status":
                "error",

            "message":
                (
                    f"PDF generation failed: {str(e)}"
                )
        }

    return FileResponse(

        path=pdf_path,

        media_type="application/pdf",

        filename=os.path.basename(
            pdf_path
        )
    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )