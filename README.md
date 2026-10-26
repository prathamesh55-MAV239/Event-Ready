# 🎯 Event Ready

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://event-ready-y4aeacjb5acsw9nabdtkxu.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🔗 **Live Demo:** [event-ready.streamlit.app](https://event-ready-y4aeacjb5acsw9nabdtkxu.streamlit.app/)

**Your AI-powered event readiness assistant.**

Event Ready helps event organizers identify potential problems before an event begins. Powered by **Python and Ollama**, it analyzes event requirements, checks available resources, highlights missing information, and provides actionable findings to help organizers make better decisions.

## 🚀 Key Features

- 🤖 **Local AI Analysis** — Uses Ollama to analyze event plans.
- 📋 **Resource Validation** — Identifies potential shortages and resource gaps.
- ⚠️ **Risk Detection** — Highlights missing information and possible issues.
- 📊 **Readiness Assessment** — Classifies events as `READY`, `READY WITH WARNINGS`, or `NOT READY`.
- 💡 **Actionable Recommendations** — Helps organizers understand what needs attention before proceeding.

## 🛠️ Tech Stack

- **Python** — Core logic and validation
- **Ollama** — Local AI model integration
- **Streamlit** — User interface

## ⚙️ Getting Started

### Prerequisites

- Python 3.10 or later
- [Ollama](https://ollama.com/) installed and running
- A compatible Ollama model downloaded locally

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/prathamesh55-MAV239/Event-Ready.git
cd Event-Ready
```

**2. Create and activate a virtual environment (recommended)**

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Start Ollama**

Ensure the Ollama service is running and the model configured in `app.py` is available locally (`ollama run llama3.2:3b`).

**5. Launch the application**

```bash
streamlit run app.py
```

If your project uses a separate terminal entry point, follow the corresponding command in your current implementation:

```bash
python cli.py --example
```

## 📁 Project Structure

```text
Event-Ready/
├── app.py
├── tools.py
├── skill.md
├── requirements.txt
└── README.md
```

- `app.py` — Application entry point and user interface
- `tools.py` — Python tools and validation logic
- `skill.md` — Instructions guiding the AI workflow
- `requirements.txt` — Python dependencies
- `README.md` — Project documentation

## 💡 Why Event Ready?

Event planning involves coordinating resources, budgets, people, and logistics. Small oversights can create major problems on event day.

Event Ready aims to move event planning from **last-minute problem solving to proactive readiness assessment** by combining local AI reasoning with structured validation.

## 🔮 Future Scope

- Interactive what-if planning
- Dependency and failure-chain analysis
- Evidence-based readiness reports
- Improved resource and budget tracking
- Exportable assessment reports

## 🤝 Contributing

Suggestions, bug reports, and contributions are welcome. Feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the terms of the MIT license included in the repository.

---

**Built with Python, Streamlit, and Ollama.**
