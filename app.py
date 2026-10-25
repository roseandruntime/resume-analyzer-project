import streamlit as st
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📄",
    layout="wide"
)

# -------------------- UI DESIGN --------------------

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(ellipse at 10% 5%,
            rgba(109,40,217,0.25), transparent 35%),
        radial-gradient(ellipse at 90% 25%,
            rgba(37,99,235,0.20), transparent 35%),
        linear-gradient(135deg,#0b1020,#15132d 55%,#101827);
    color: #f3f4f6;
}

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #f5f3ff !important;
}

p, label, .stMarkdown {
    color: #e5e7eb;
}

/* Text inputs and text areas */
.stApp input,
.stApp textarea {
    background-color: #ffffff !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    caret-color: #111827 !important;
}

.stApp input::placeholder,
.stApp textarea::placeholder {
    color: #6b7280 !important;
    -webkit-text-fill-color: #6b7280 !important;
    opacity: 1 !important;
}

/* Labels */
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p,
.stApp label {
    color: #f9fafb !important;
}

/* File uploader: readable instructions and button */
.stApp [data-testid="stFileUploader"] {
    color: #f9fafb !important;
}

.stApp [data-testid="stFileUploader"] section {
    background: rgba(255,255,255,0.06) !important;
    border: 1px dashed #a78bfa !important;
    border-radius: 14px !important;
}

.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploader"] section span,
.stApp [data-testid="stFileUploader"] section small,
.stApp [data-testid="stFileUploader"] section div {
    color: #f9fafb !important;
}

.stApp [data-testid="stFileUploader"] section button {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #d1d5db !important;
}

.stApp [data-testid="stFileUploader"] section button,
.stApp [data-testid="stFileUploader"] section button * {
    -webkit-text-fill-color: #111827 !important;
    color: #111827 !important;
}

/* Metrics */
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(196,181,253,0.25);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 8px 28px rgba(0,0,0,0.15);
}

div[data-testid="stMetricValue"] {
    color: #c4b5fd !important;
}

div[data-testid="stMetricLabel"] {
    color: #f9fafb !important;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button {
    border-radius: 12px;
    border: 1px solid #8b5cf6;
    background: linear-gradient(100deg,#6d28d9,#4338ca);
    color: #ffffff !important;
    font-weight: 600;
    min-height: 44px;
}

.stButton > button *,
.stDownloadButton > button * {
    color: #ffffff !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: #c4b5fd;
    box-shadow: 0 5px 20px rgba(139,92,246,0.25);
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

hr {
    border-color: rgba(196,181,253,0.2);
}

.hero {
    background: linear-gradient(120deg,
        rgba(109,40,217,0.32),
        rgba(37,99,235,0.18));
    border: 1px solid rgba(196,181,253,0.3);
    border-radius: 22px;
    padding: 28px;
    margin-bottom: 24px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.18);
}

.hero p {
    color: #ddd6fe !important;
}

.small-note {
    color: #c4b5fd !important;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>✨ Resume Analyzer</h1>
    <p>Smart keyword matching · Essential skill verification ·
    Resume improvement insights</p>
</div>
""", unsafe_allow_html=True)

st.caption("Academic Project Prototype | Resume Analysis Dashboard")
st.divider()

# -------------------- INPUTS --------------------

st.subheader("📂 Upload & Job Details")

col1, col2 = st.columns(2)

with col1:
    student_name = st.text_input("Candidate Name")
    job_title = st.text_input("Job Title")

with col2:
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF or DOCX)",
        type=["pdf", "docx"]
    )

job_description = st.text_area(
    "Required Job Skills (comma-separated)",
    placeholder="Python, SQL, Java, Communication"
)

essential_skills_input = st.text_input(
    "Essential / Must-Have Skills (comma-separated)",
    placeholder="Python, SQL"
)

st.caption(
    "Essential skills should also be included in Required Job Skills."
)

# -------------------- HELPER FUNCTIONS --------------------

def extract_resume_text(file):
    if file.name.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(file.getvalue()))
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if file.name.lower().endswith(".docx"):
        document = Document(BytesIO(file.getvalue()))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    return ""


def check_formatting(text):
    checks = []

    checks.append((
        "Sufficient text (at least 50 words)",
        len(text.split()) >= 50
    ))

    email_found = bool(re.search(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        text
    ))
    checks.append(("Email address found", email_found))

    phone_found = bool(re.search(
        r"(\+?\d[\d\s().-]{7,}\d)",
        text
    ))
    checks.append(("Possible phone number found", phone_found))

    headings = [
        "education", "experience", "skills",
        "projects", "summary", "certifications"
    ]

    found_headings = [
        heading for heading in headings
        if re.search(
            r"\b" + re.escape(heading) + r"\b",
            text,
            re.IGNORECASE
        )
    ]

    checks.append((
        "At least two common section headings found",
        len(found_headings) >= 2
    ))

    return checks, found_headings


def create_pdf_report(
    candidate, role, score, required, matched, missing,
    essential, essential_matched, essential_missing,
    checks, headings, suggestions
):
    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=19,
        leading=24,
        textColor=colors.HexColor("#4338CA"),
        spaceAfter=12
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4338CA"),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=5
    )

    def para(text):
        return Paragraph(escape(str(text)), body_style)

    def bullet_list(items):
        if not items:
            return [para("None")]
        return [para("- " + item) for item in items]

    story = [
        Paragraph("RESUME ANALYSIS REPORT", title_style),
        para("Automated Resume Keyword Matching and Formatting Verification"),
        para("Generated: " + datetime.now().strftime("%d %B %Y, %I:%M %p")),
        Spacer(1, 10),
        Paragraph("1. Candidate Details", heading_style)
    ]

    details = [
        ["Candidate", candidate or "Not provided"],
        ["Job Title", role or "Not provided"],
        ["Keyword Match Score", f"{score:.2f}%"]
    ]

    table = Table(
        [[escape(str(cell)) for cell in row] for row in details],
        colWidths=[2 * inch, 4.4 * inch]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDE9FE")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    story.append(table)

    story.append(Paragraph("2. Job Keyword Analysis", heading_style))
    story.append(para(
        f"Matched {len(matched)} of {len(required)} required keywords."
    ))

    story.append(Paragraph("Matched Keywords", styles["Heading3"]))
    story.extend(bullet_list(matched))

    story.append(Paragraph("Missing Keywords", styles["Heading3"]))
    story.extend(bullet_list(missing))

    story.append(Paragraph("3. Essential Skills Verification", heading_style))
    story.append(para(f"Essential skills identified: {len(essential)}"))

    story.append(Paragraph("Essential Skills Matched", styles["Heading3"]))
    story.extend(bullet_list(essential_matched))

    story.append(Paragraph("Missing Essential Skills", styles["Heading3"]))
    story.extend(bullet_list(essential_missing))

    if essential_missing:
        story.append(para(
            "Warning: One or more essential skills were not detected. "
            "Review the resume manually."
        ))
    elif essential:
        story.append(para("All entered essential skills were detected."))

    story.append(Paragraph("4. Formatting Verification", heading_style))

    passed = sum(1 for _, result in checks if result)
    story.append(para(f"Basic checks passed: {passed}/{len(checks)}"))

    for label, result in checks:
        story.append(para(
            ("PASS: " if result else "NEEDS REVIEW: ") + label
        ))

    story.append(Paragraph("Recognized Headings", styles["Heading3"]))
    story.extend(bullet_list(headings))

    story.append(Paragraph("5. Improvement Suggestions", heading_style))
    story.extend(bullet_list(suggestions))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Important Note", styles["Heading3"]))
    story.append(para(
        "This academic prototype uses basic text-based keyword matching. "
        "It does not verify actual skill proficiency or guarantee ATS "
        "compatibility. Results should be reviewed by a person."
    ))

    pdf.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# -------------------- ANALYSIS --------------------

if st.button("✨ Analyze Resume", type="primary", use_container_width=True):

    if uploaded_file is None:
        st.warning("Please upload a PDF or DOCX resume.")

    elif not job_description.strip():
        st.warning("Please enter the required job skills.")

    else:
        try:
            resume_text = extract_resume_text(uploaded_file)

            if not resume_text.strip():
                st.error(
                    "No readable text found. Scanned PDFs may require OCR."
                )

            else:
                resume_lower = resume_text.lower()

                required_keywords = {
                    skill.strip().lower()
                    for skill in job_description.split(",")
                    if skill.strip()
                }

                essential_keywords = {
                    skill.strip().lower()
                    for skill in essential_skills_input.split(",")
                    if skill.strip()
                }

                if not required_keywords:
                    st.warning("Please enter at least one job skill.")

                elif not essential_keywords.issubset(required_keywords):
                    st.warning(
                        "Every essential skill must also be included "
                        "in Required Job Skills."
                    )

                else:
                    matched = sorted(
                        skill for skill in required_keywords
                        if skill in resume_lower
                    )

                    missing = sorted(required_keywords - set(matched))

                    score = len(matched) / len(required_keywords) * 100

                    essential_matched = sorted(
                        skill for skill in essential_keywords
                        if skill in resume_lower
                    )

                    essential_missing = sorted(
                        essential_keywords - set(essential_matched)
                    )

                    checks, found_headings = check_formatting(resume_text)
                    passed = sum(1 for _, result in checks if result)

                    suggestions = []

                    if missing:
                        suggestions.append(
                            "Review missing job keywords and include them "
                            "only if they accurately reflect your skills."
                        )

                    if essential_missing:
                        suggestions.append(
                            "Review missing essential skills: "
                            + ", ".join(essential_missing)
                            + ". Include evidence only if accurate."
                        )

                    if not any(
                        heading in found_headings
                        for heading in ["skills", "projects"]
                    ):
                        suggestions.append(
                            "Consider adding relevant Skills and Projects sections."
                        )

                    if not any(
                        heading in found_headings
                        for heading in ["education", "experience"]
                    ):
                        suggestions.append(
                            "Consider including Education or Experience details."
                        )

                    if len(resume_text.split()) < 50:
                        suggestions.append(
                            "Check whether all resume pages contain readable text."
                        )

                    if "summary" not in found_headings:
                        suggestions.append(
                            "Consider adding a short professional summary if useful."
                        )

                    st.divider()
                    st.header("📊 Analysis Dashboard")

                    top1, top2, top3 = st.columns(3)

                    with top1:
                        st.metric("Keyword Match", f"{score:.1f}%")

                    with top2:
                        st.metric(
                            "Essential Skills",
                            f"{len(essential_matched)}/{len(essential_keywords)}"
                        )

                    with top3:
                        st.metric(
                            "Formatting Checks",
                            f"{passed}/{len(checks)}"
                        )

                    st.write("**Candidate:**", student_name or "Not provided")
                    st.write("**Job Title:**", job_title or "Not provided")

                    st.progress(int(round(score)))

                    st.divider()
                    st.subheader("🔍 Keyword Matching")

                    left, right = st.columns(2)

                    with left:
                        st.success("Matched Keywords")
                        st.write(", ".join(matched) if matched else "None")

                    with right:
                        st.error("Missing Keywords")
                        st.write(", ".join(missing) if missing else "None")

                    st.divider()
                    st.subheader("🎯 Essential Skills Verification")

                    if essential_matched:
                        st.success(
                            "Detected essential skills: "
                            + ", ".join(essential_matched)
                        )

                    if essential_missing:
                        st.error(
                            "Missing essential skills: "
                            + ", ".join(essential_missing)
                        )
                        st.warning(
                            "Review these results manually. This is "
                            "text-based keyword detection."
                        )
                    elif essential_keywords:
                        st.success("All entered essential keywords were detected.")
                    else:
                        st.info(
                            "No essential skills entered. Add them above "
                            "to use this check."
                        )

                    st.divider()
                    st.subheader("📝 Formatting Verification")

                    for label, result in checks:
                        if result:
                            st.success("✓ " + label)
                        else:
                            st.warning("Needs review: " + label)

                    st.write(
                        "**Recognized headings:**",
                        ", ".join(found_headings)
                        if found_headings else "None"
                    )

                    st.caption(
                        "These are basic text checks, not a complete "
                        "visual layout or ATS compatibility assessment."
                    )

                    st.divider()
                    st.subheader("💡 Improvement Suggestions")

                    if suggestions:
                        for index, suggestion in enumerate(suggestions, 1):
                            st.write(f"{index}. {suggestion}")
                    else:
                        st.success(
                            "No additional suggestions were triggered. "
                            "Manual review is still recommended."
                        )

                    st.divider()
                    st.subheader("📄 Download Your Report")

                    pdf_bytes = create_pdf_report(
                        student_name,
                        job_title,
                        score,
                        sorted(required_keywords),
                        matched,
                        missing,
                        sorted(essential_keywords),
                        essential_matched,
                        essential_missing,
                        checks,
                        found_headings,
                        suggestions
                    )

                    st.download_button(
                        "⬇️ Download Analysis Report (PDF)",
                        data=pdf_bytes,
                        file_name="resume_analysis_report.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                    st.caption(
                        "This report reflects the current analysis. "
                        "Keyword detection does not prove skill proficiency."
                    )

        except Exception as error:
            st.error(
                "Could not analyze this file. Check that it is a valid, "
                "readable PDF or DOCX file."
            )
            st.caption(f"Technical detail: {error}")

st.divider()
st.markdown(
    '<p class="small-note">Resume Analyzer | Academic Project Prototype</p>',
    unsafe_allow_html=True
)
