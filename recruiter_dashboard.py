"""
Recruiter dashboard for Resume Analyzer.
Only student analyses explicitly shared with recruiters are visible.
"""
import json
from pathlib import Path
import streamlit as st
from database import get_connection


def _load_json(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def render_recruiter_dashboard(user):
    st.title("🧑‍💼 Recruiter Dashboard")
    st.caption("Review only the candidate analyses students have chosen to share.")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT a.analysis_id, a.match_score, a.analyzed_at,
                   a.matched_keywords, a.missing_keywords,
                   a.essential_skill_results, a.formatting_results,
                   a.suggestions, j.job_title,
                   u.full_name AS candidate_name,
                   rs.original_filename, rs.stored_file_path AS resume_path,
                   rp.stored_file_path AS report_path,
                   rr.review_status, rr.review_comments
            FROM analyses a
            JOIN resumes rs ON rs.resume_id = a.resume_id
            JOIN users u ON u.user_id = rs.user_id
            JOIN job_descriptions j ON j.job_id = a.job_id
            LEFT JOIN reports rp ON rp.analysis_id = a.analysis_id
            LEFT JOIN recruiter_reviews rr
                ON rr.analysis_id = a.analysis_id AND rr.recruiter_id = ?
            WHERE a.shared_with_recruiters = 1 AND u.role = 'student'
            ORDER BY a.analyzed_at DESC, a.analysis_id DESC
            """,
            (user["user_id"],),
        ).fetchall()

    if not rows:
        st.info(
            "No candidates have shared an analysis yet. "
            "Students control whether their analyses are visible to recruiters."
        )
        return

    st.metric("Shared candidate analyses", len(rows))
    for row in rows:
        title = (
            f"{row['candidate_name']} · {row['job_title']} "
            f"· {row['match_score']:.1f}%"
        )
        with st.expander(title):
            st.caption(
                f"Analysis #{row['analysis_id']} · {row['analyzed_at']} UTC"
            )
            left, right = st.columns(2)
            with left:
                st.write("**Matched skills**")
                matched = _load_json(row["matched_keywords"], [])
                st.write(", ".join(matched) if matched else "None")
            with right:
                st.write("**Missing skills**")
                missing = _load_json(row["missing_keywords"], [])
                st.write(", ".join(missing) if missing else "None")

            essential = _load_json(row["essential_skill_results"], {})
            formatting = _load_json(row["formatting_results"], {})
            st.write("**Essential skills**")
            st.json(essential)
            st.write("**Formatting checks**")
            st.json(formatting)

            resume_path = row["resume_path"]
            if resume_path and Path(resume_path).is_file():
                with open(resume_path, "rb") as resume_file:
                    st.download_button(
                        "Download shared resume",
                        data=resume_file.read(),
                        file_name=Path(row["original_filename"]).name,
                        key=f"resume_{row['analysis_id']}",
                    )
            report_path = row["report_path"]
            if report_path and Path(report_path).is_file():
                with open(report_path, "rb") as report_file:
                    st.download_button(
                        "Download analysis report",
                        data=report_file.read(),
                        file_name=f"analysis_{row['analysis_id']}.pdf",
                        mime="application/pdf",
                        key=f"report_{row['analysis_id']}",
                    )

            status_options = ["pending", "reviewed", "shortlisted", "rejected"]
            old_status = row["review_status"] or "pending"
            default_index = status_options.index(old_status) if old_status in status_options else 0
            with st.form(f"review_form_{row['analysis_id']}"):
                status = st.selectbox(
                    "Review status", status_options, index=default_index,
                    key=f"status_{row['analysis_id']}"
                )
                comments = st.text_area(
                    "Recruiter comments",
                    value=row["review_comments"] or "",
                    key=f"comments_{row['analysis_id']}"
                )
                submitted = st.form_submit_button("Save review")
            if submitted:
                with get_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO recruiter_reviews
                            (recruiter_id, analysis_id, review_comments, review_status)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(recruiter_id, analysis_id) DO UPDATE SET
                            review_comments = excluded.review_comments,
                            review_status = excluded.review_status,
                            reviewed_at = CURRENT_TIMESTAMP
                        """,
                        (user["user_id"], row["analysis_id"], comments.strip(), status),
                    )
                st.success("Review saved.")
                st.rerun()
