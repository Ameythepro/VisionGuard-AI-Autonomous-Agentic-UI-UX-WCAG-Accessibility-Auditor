# VisionGuard AI 🛡️
**Autonomous Agentic UI/UX & WCAG Accessibility Auditor**

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.1-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.26.0-FF4B4B.svg)
![Playwright](https://img.shields.io/badge/Playwright-1.38.0-2EAD33.svg)

> **Academic Project:** 5th Semester CSE Evaluation | Indian Institute of Information Technology (IIIT), Kottayam

---

## 📌 Project Overview
Modern web applications frequently suffer from visual layout regressions across diverse viewports and strict WCAG 2.1 accessibility violations. **VisionGuard AI** is an autonomous DevSecOps quality assurance agent designed to solve this. 

Instead of manual QA testing, VisionGuard uses an asynchronous **Playwright** engine to capture multi-viewport states, a deterministic **Python math engine** to calculate accessibility compliance, and a **Multimodal VLM (Claude 3.5 / Gemini 1.5)** to detect spatial UI bugs. Finally, it generates surgical CSS patches and verifies them in a closed-loop sandbox.

## 🏗️ System Architecture 
This repository follows a strict microservices architecture:
* `ai_engine/`: Manages the Agentic Tool Calling and Closed-Loop Reflection framework.
* `browser_automation/`: Handles headless multi-viewport rendering and CSS sandbox injection.
* `dom_accessibility/`: Parses Abstract Syntax Trees (AST) and runs deterministic WCAG 2.1 Color Contrast mathematics.
* `api_backend/`: Asynchronous FastAPI gateway with Redis caching for sub-second responses.
* `frontend_ui/`: Streamlit dashboard featuring an interactive before/after visual diff slider.

## 🚀 Quick Start (Local Development)
To run this project locally:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Ameythepro/VisionGuard-AI-Autonomous-Agentic-UI-UX-WCAG-Accessibility-Auditor.git](https://github.com/Ameythepro/VisionGuard-AI-Autonomous-Agentic-UI-UX-WCAG-Accessibility-Auditor.git)
   cd VisionGuard-AI
   ```
