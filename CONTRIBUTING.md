# Contributing to Self‑Healing Localization (SHL)

Thank you for your interest in contributing! 
SHLL aims to become a simple, automatic, and self‑maintaining localization layer for Python projects. 
All contributions — code, documentation, ideas, and bug reports — are welcome.

---

## 🧩 How to Contribute

### 1. Fork the repository
Create your own fork and clone it locally:

```bash
git clone https://codeberg.org/lahtis/Self_Healing_Localization
```

2. Create a feature branch
Use a descriptive branch name:

```bash
git checkout -b feature/add-swedish-support
```

3. Make your changes
Follow the existing code style:

Keep modules small and focused

Avoid external dependencies

Maintain the self‑healing philosophy

Write clear, readable code

4. Add or update tests (if applicable)
Tests should be placed under:

```bash
tests/
```

5. Run the test suite
If tests exist:

```bash
pytest
```

6. Submit a Pull Request
Push your branch and open a PR:

* Describe what you changed
* Explain why the change is needed
* Reference related issues if applicable
* We review PRs with a focus on clarity, maintainability, and alignment with SHLL’s design goals


# 🐞 Reporting Issues
If you find a bug, please open an issue and include:
* A clear description
* Steps to reproduce
* Expected vs. actual behavior
* Python version and OS
* Relevant logs or stack traces

# 🌍 Adding New Languages
To contribute new language files:
* Run the engine to auto‑generate missing files
* Fill in translations in locales/lang_<code>.json
* Fill in template translations in prompts/<code>.json
* Submit a PR with the new language pack

# 🧪 Coding Standards
* Python 3.8+
* No external dependencies
* Keep modules pure and deterministic
* Prefer small, composable functions
* Document public methods

# ❤️ Thank You
Your contributions help SHLL grow into a universal, self‑maintaining localization system.
We appreciate your time, ideas, and creativity.


---

# 📁 **docs/ Folder Structure**

Here’s a future‑proof documentation structure that scales as the project grows.

You can create this as:

```bash

docs/
│
├─ index.md
├─ installation.md
├─ quickstart.md
├─ concepts/
│   ├─ overview.md
│   ├─ self_healing.md
│   ├─ localization_engine.md
│   └─ file_structure.md
│
├─ guides/
│   ├─ adding_languages.md
│   ├─ syncing_languages.md
│   ├─ ui_texts.md
│   └─ templates.md
│
├─ api/
│   ├─ engine.md
│   ├─ localizer.md
│   ├─ template_localizer.md
│   └─ ai_translation.md   # reserved for v0.2
│
├─ examples/
│   ├─ basic_ui.md
│   ├─ basic_templates.md
│   ├─ sync.md
│   └─ full_demo.md
│
└─ roadmap.md
```

---

# 📘 **docs/index.md (starter content)**

```markdown
# Self‑Healing Localization Layer — Documentation

Welcome to the official documentation for SHLL.

This site covers:

- Installation  
- Quick start  
- Core concepts  
- API reference  
- Guides and examples  
- Roadmap and future plans  

SHLL is designed to eliminate missing translations forever by automatically creating missing files and keys, keeping your project fully localized with zero manual maintenance.




