"""
Text and styling shared by both web UIs (app.py for Gradio, streamlit_app.py for Streamlit).
Program facts come from Data/handbook.txt, section 3.
"""

EXAMPLES = [
    "What will I learn in the Computational Thinking course?",
    "Tell me about the foundational level subjects",
    "What are the eligibility rules to write the end term exam?",
    "What is the difference between MLF and MLT?",
]

# (level, credits, details)
PROGRAM_LEVELS = [
    ("Foundation", "32 credits", "8 courses: English, Maths, Stats, CT, Python"),
    ("Diploma", "54 credits", "Diploma in Programming + Diploma in Data Science"),
    ("BSc degree", "114 credits", "Total credits to graduate with a BSc"),
    ("BS degree", "142 credits", "Total credits to graduate with a BS"),
]

TIPS = [
    'Name the course for detailed answers, e.g. <em>"What is taught in PDSA?"</em>',
    'Ask follow-ups naturally, e.g. <em>"How is it graded?"</em>',
    "Compare up to 3 courses at once.",
]

DISCLAIMER = (
    "Answers are generated only from the student handbook and course documents and may be incomplete "
    "or out of date. Always check official IITM BS announcements before making decisions. "
    "Not affiliated with or endorsed by IIT Madras."
)


HEADER_HTML = """
<div class="iitm-header">
  <div class="iitm-badge">BS</div>
  <div class="iitm-heading">
    <div class="iitm-kicker">IIT Madras &middot; BS in Data Science and Applications</div>
    <h1>Degree Assistant</h1>
    <p>Ask about courses, levels, exams, eligibility and fees. Answers come from the student handbook and course documents.</p>
  </div>
  <span class="iitm-pill">Unofficial student project</span>
</div>
"""

WELCOME_HTML = """
<div class="iitm-welcome">
  <h2>Hi! How can I help you today?</h2>
  <p>I can answer questions about the IITM BS program using the official handbook and course documents.</p>
</div>
"""

FOOTER_HTML = f'<div class="iitm-footer">{DISCLAIMER}</div>'


def program_card_html() -> str:
    items = "".join(
        f'<li><span class="lvl">{level}</span><span class="cr">{credits}</span><small>{details}</small></li>'
        for level, credits, details in PROGRAM_LEVELS
    )
    return f'<div class="iitm-card"><h3>Program at a glance</h3><ul class="iitm-levels">{items}</ul></div>'


def tips_card_html() -> str:
    items = "".join(f"<li>{tip}</li>" for tip in TIPS)
    return f'<div class="iitm-card"><h3>Tips</h3><ul class="iitm-tips">{items}</ul></div>'


# Colors use Gradio's theme variables when present, with fallbacks for Streamlit.
BRAND_CSS = """
/* Header banner */
.iitm-header {
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  padding: 22px 26px; border-radius: 14px; color: #FFFFFF;
  background: linear-gradient(120deg, #6E1616 0%, #8B1E1E 55%, #A83232 100%);
  border-bottom: 4px solid #E0B84C;
}
.iitm-badge {
  flex: none; width: 58px; height: 58px; border-radius: 50%;
  display: grid; place-items: center;
  background: #FFFFFF; color: #8B1E1E; border: 3px solid #E0B84C;
  font: 700 22px Georgia, "Times New Roman", serif;
}
.iitm-heading { flex: 1; min-width: 220px; }
.iitm-kicker { font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: #F3D98B; }
.iitm-header h1 { margin: 2px 0 4px; padding: 0; font-size: 28px; color: #FFFFFF; }
.iitm-header p { margin: 0; font-size: 14px; color: #F5E9E9; }
.iitm-pill {
  font-size: 12px; padding: 5px 12px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,.55); color: #FFFFFF; white-space: nowrap;
}

/* Info cards */
.iitm-card {
  padding: 16px 18px; margin-bottom: 14px; border-radius: 12px;
  background: var(--block-background-fill, #FFFFFF); border: 1px solid var(--border-color-primary, #E7DFD5);
  border-top: 3px solid #8B1E1E;
}
.iitm-card h3 { margin: 0 0 10px; padding: 0; font-size: 15px; color: var(--body-text-color, #2B2B2B); }
.iitm-levels, .iitm-tips { list-style: none; margin: 0; padding: 0; }
.iitm-levels li {
  display: grid; grid-template-columns: 1fr auto; gap: 2px 8px; margin: 0;
  padding: 8px 0; border-bottom: 1px dashed var(--border-color-primary, #E7DFD5);
}
.iitm-levels li:last-child { border-bottom: none; }
.iitm-levels .lvl { font-weight: 600; color: var(--body-text-color, #2B2B2B); }
.iitm-levels .cr { font-size: 12px; font-weight: 600; color: #8B1E1E; background: #F8ECEC; padding: 1px 8px; border-radius: 999px; }
.iitm-levels small { grid-column: 1 / -1; color: var(--body-text-color-subdued, #6F6A64); }
.iitm-tips li { margin: 0; padding: 6px 0; font-size: 13px; color: var(--body-text-color-subdued, #6F6A64); }

/* Welcome message and footer */
.iitm-welcome { text-align: center; padding: 10px 20px; }
.iitm-welcome h2 { margin: 0 0 6px; padding: 0; color: #8B1E1E; }
.iitm-welcome p { margin: 0; color: var(--body-text-color-subdued, #6F6A64); }
.iitm-footer {
  margin-top: 8px; padding: 12px 16px; font-size: 12px; text-align: center;
  color: var(--body-text-color-subdued, #6F6A64); border-top: 1px solid var(--border-color-primary, #E7DFD5);
}

@media (max-width: 640px) {
  .iitm-header { padding: 16px; }
  .iitm-header h1 { font-size: 22px; }
}
"""
