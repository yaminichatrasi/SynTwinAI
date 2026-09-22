# 🧠 SynTwin AI

### AI Digital Twin Creator for Synthetic User Behavior Simulation

**SynTwin AI** is an AI-powered synthetic user research platform that creates realistic **AI Digital Twins** based on specific research requirements.

Instead of repeatedly recruiting real users for early-stage research, SynTwin AI allows researchers to generate domain-specific synthetic personas and simulate their behavior through **Survey Mode** and **Interview Mode**.

## 🎯 What Problem Does SynTwin AI Solve?

Traditional user research can require significant time, cost, and effort to recruit participants and collect responses.

SynTwin AI provides a simulated research environment where users can:

* Define a research experiment
* Generate multiple AI Digital Twins
* Simulate survey responses
* Conduct persona-based interviews
* Maintain persona memory across interactions
* Extract research insights
* Generate a research report in PDF format

The goal is to support **early-stage product research, UX exploration, and behavioral analysis** using synthetic users.

---

## ✨ Key Features

### 🤖 AI Persona Generation

Generate multiple realistic synthetic users based on:

* Product / Service
* Target Audience
* Research Objective
* Research Domain
* Product Description
* Requested Persona Count

Each persona contains:

* Name
* Age
* Gender
* Background
* Goals
* Behaviors
* Preferences
* Pain Points
* Confidence Score

---

### 📊 Interactive Research Dashboard

View generated AI Digital Twins through an interactive dashboard.

Each persona is designed to remain consistent with the experiment's:

**Product + Domain + Target Audience + Research Objective**

---

### 📝 Survey Mode

Ask multiple research questions and receive responses from all generated personas.

The responses are generated using the stored persona characteristics so that different personas provide different perspectives.

**Example:**

> Would you use this banking application for your daily transactions?

Each synthetic user responds according to their individual needs, preferences, behaviors, and pain points.

---

### 💬 Interview Mode

Select an individual AI Digital Twin and conduct a conversational interview.

The system maintains interview history so the persona can remain consistent across multiple questions.

**Flow:**

```text
Select Persona
      ↓
Ask Question
      ↓
AI Digital Twin Responds
      ↓
Conversation Memory
      ↓
Continue Interview
```

---

### 🧠 Persona Memory

SynTwin AI stores persona information and interaction history so that synthetic users can maintain consistency during research.

Stored information includes:

* Persona details
* Survey history
* Interview history
* Experiment information
* Research context

---

### 🔍 Research Insights

The platform analyzes available synthetic research data to identify:

* Would-use-product score
* User segments
* Sentiment patterns
* Recurring themes
* Agreement patterns
* Behavioral trends
* Key research insights

This converts individual persona responses into a structured research summary.

---

### 📄 PDF Research Report

SynTwin AI can generate a structured research report containing:

* Experiment information
* Product details
* Research objective
* Synthetic persona overview
* Persona behavioral details
* Survey results
* Representative responses
* Research conclusion

---

## 🏗️ System Workflow

```text
                SYN TWIN AI
                    │
                    ▼
          Create Research Experiment
                    │
                    ▼
       Enter Product & Research Details
                    │
                    ▼
           OpenRouter LLM
                    │
                    ▼
       Generate AI Digital Twins
                    │
                    ▼
             Persona Memory
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
     Survey Mode        Interview Mode
          │                   │
          └─────────┬─────────┘
                    ▼
            Research Responses
                    │
                    ▼
            Insight Extraction
                    │
                    ▼
             Research Insights
                    │
                    ▼
             PDF Research Report
```

---

## 🛠️ Technology Stack

| Technology         | Purpose                      |
| ------------------ | ---------------------------- |
| **Python**         | Backend development          |
| **FastAPI**        | Web application framework    |
| **Jinja2**         | Dynamic HTML templates       |
| **HTML5**          | Frontend structure           |
| **CSS3**           | UI styling                   |
| **JavaScript**     | Frontend interactions        |
| **OpenRouter API** | LLM integration              |
| **JSON**           | Persona & interaction memory |
| **ReportLab**      | PDF report generation        |

---

## 📁 Project Structure

```text
synthetic-user-generation-platform/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── data/
    |__personas.csv
│   └── persona_memory.json
│
├── reports/
│   └── generated_reports.pdf
│
├── templates/
│   ├── experiment.html
│   ├── dashboard.html
│   ├── survey.html
│   ├── survey_results.html
│   └── insights.html
│
└── static/
    ├── style.css
    └── script.js
```

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/syntwinAI.git
```

### 2. Open the Project

```bash
cd syntwinAI
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

> Never upload your actual API key to GitHub.

### 5. Run the Application

```bash
uvicorn main:app --reload
```

### 6. Open in Browser

```text
http://127.0.0.1:8000
```

---

## 🔐 Environment Variables

| Variable             | Description                   |
| -------------------- | ----------------------------- |
| `OPENROUTER_API_KEY` | API key used for LLM requests |

For security, the `.env` file should be added to `.gitignore`.

---

## 🧪 Example Research Experiment

### Product

**Digital Banking Application**

### Target Audience

Young adults and working professionals who use digital banking services.

### Research Objective

Understand user expectations, pain points, and willingness to use an AI-powered banking application.

### Research Domain

**Banking & FinTech**

### Generated Synthetic Users

```text
Raj Sharma
Meera Patel
Ananya Desai
Vikram Singh
Sneha Gupta
Arjun Mehta
Ravi Verma
```

Each persona has different characteristics and can provide different research perspectives.

---

## 💡 Why Synthetic Users?

Synthetic users can be useful during the **early stages of product development** for:

* Rapid idea exploration
* Persona-based UX testing
* Early product feedback
* Hypothesis generation
* Scenario simulation
* Initial behavioral analysis

> Synthetic research should complement, not automatically replace, research with real users. AI-generated responses represent simulated behavior and may not accurately reflect real-world populations.

---

## 🔄 Research Modes

### Survey Mode

```text
Research Questions
       ↓
All AI Digital Twins
       ↓
Individual Responses
       ↓
Response Comparison
```

### Interview Mode

```text
Select Digital Twin
       ↓
Ask Questions
       ↓
Persona-Based Response
       ↓
Memory Maintained
       ↓
Continue Conversation
```

---

## 📊 Research Insights

SynTwin AI transforms generated responses into structured findings such as:

```text
Would Use Product
        ↓
Sentiment
        ↓
Recurring Themes
        ↓
Agreement Patterns
        ↓
Behavioral Trends
        ↓
Key Insights
```

---

## 📄 Report Generation

The platform provides a downloadable PDF research report containing the experiment setup, personas, behavioral details, survey results, representative responses, and conclusion.

---

## 🔮 Future Enhancements

* Real-user + synthetic-user comparison
* CSV export
* Advanced analytics dashboard
* More LLM provider support
* Multilingual synthetic personas
* Persona quality evaluation
* Statistical comparison of persona segments
* Improved long-term persona memory
* Real-time collaborative research
* Integration with research and survey platforms

---

## ⚠️ Current Limitations

* Synthetic responses are AI-generated and may not perfectly represent real users.
* Results depend on the quality of the research input and LLM response.
* OpenRouter/API availability can affect generation.
* Synthetic research findings should be validated with real-user research before making high-impact product decisions.

---

## 👩‍💻 Author

### Yamini Chatrasi

**B.Tech — Computer Science & Engineering**

**Project:** SynTwin AI
**Tagline:** *AI Digital Twin Creator for Synthetic User Behavior Simulation*

---

## ⭐ Project Highlights

```text
🤖 AI-Powered Persona Generation
🧠 Persona Memory
📊 Survey Simulation
💬 AI Interview Mode
🔍 Research Insight Extraction
📄 PDF Research Reports
🌐 Domain-Specific Synthetic Users
```

---

## 📜 License

This project is available under the **MIT License**.


## Author

Developed by Yamini Chatrasi
