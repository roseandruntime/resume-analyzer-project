"""Admin dashboard for Resume Analyzer. Place beside app.py."""
import streamlit as st
from database import get_connection
from datetime import datetime, timedelta
def _to_ist(value):
    if not value:
        return ""

    try:
        utc_time = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        ist_time = utc_time + timedelta(hours=5, minutes=30)
        return ist_time.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return value

def _count(connection, query):
    row = connection.execute(query).fetchone()
    return row[0] if row else 0

def render_admin_dashboard(user):
    st.title("🛡️ Admin Dashboard")
    st.caption(f"Welcome, {user['full_name']}. Manage users and monitor the system.")

    with get_connection() as con:
        total = _count(con, "SELECT COUNT(*) FROM users")
        students = _count(con, "SELECT COUNT(*) FROM users WHERE role='student'") 
        recruiters = _count(con, "SELECT COUNT(*) FROM users WHERE role='recruiter'")
        admins = _count(con, "SELECT COUNT(*) FROM users WHERE role='admin'")
        active = _count(con, "SELECT COUNT(*) FROM users WHERE is_active=1")
        analyses = _count(con, "SELECT COUNT(*) FROM analyses")
        reviews = _count(con, "SELECT COUNT(*) FROM recruiter_reviews")

    st.subheader("System overview")
    cols = st.columns(4)
    for col, label, value in zip(cols, ["Total users", "Students", "Recruiters", "Analyses"],
                                 [total, students, recruiters, analyses]):
        col.metric(label, value)
    cols = st.columns(3)
    for col, label, value in zip(cols, ["Admins", "Active accounts", "Recruiter reviews"],
                                 [admins, active, reviews]):
        col.metric(label, value)

    users_tab, analyses_tab, reviews_tab, settings_tab = st.tabs(
        ["👥 User management", "📊 Analysis records", "📝 Recruiter reviews", "⚙️ System settings"]
    )

    with users_tab:
        st.subheader("Registered accounts")
        with get_connection() as con:
            rows = con.execute(
                "SELECT user_id, full_name, email, role, is_active, created_at FROM users ORDER BY created_at DESC"
            ).fetchall()
        if not rows:
            st.info("No user accounts found.")
        for row in rows:
            with st.container(border=True):
                left, right = st.columns([3, 1])
                left.markdown(f"**{row['full_name']}** · {row['role'].title()}")
                left.caption(
    f"{row['email']} · User ID: {row['user_id']} · "
    f"Created: {_to_ist(row['created_at'])} (IST)"
)
                left.caption("Active" if row["is_active"] else "Inactive")
                if row["user_id"] == user["user_id"]:
                    right.caption("Current admin")
                elif right.button("Deactivate" if row["is_active"] else "Activate",
                                  key=f"toggle_user_{row['user_id']}", use_container_width=True):
                    new_status = 0 if row["is_active"] else 1
                    with get_connection() as con:
                        con.execute("UPDATE users SET is_active=? WHERE user_id=?",
                                    (new_status, row["user_id"]))
                    st.success("Account status updated.")
                    st.rerun() 

    with analyses_tab:
        st.subheader("Recent resume analyses") 
        with get_connection() as con:
            rows = con.execute(
               """SELECT a.analysis_id, a.match_score,
          datetime(a.analyzed_at, '+5 hours', '+30 minutes') AS analyzed_at_ist,
          r.original_filename,
                          u.full_name, u.email, j.job_title
                   FROM analyses a JOIN resumes r ON r.resume_id=a.resume_id
                   JOIN users u ON u.user_id=r.user_id
                   JOIN job_descriptions j ON j.job_id=a.job_id
                   ORDER BY a.analyzed_at DESC LIMIT 100"""
            ).fetchall()
        if rows:
            st.dataframe([{
                "Analysis ID": r["analysis_id"], "Candidate": r["full_name"],
                "Email": r["email"], "Resume": r["original_filename"],
                "Job title": r["job_title"], "Match score": f"{r['match_score']:.1f}%",
                "Analyzed at (IST)": r["analyzed_at_ist"]
            } for r in rows], use_container_width=True, hide_index=True)
        else:
            st.info("No analysis records found.")
        st.caption("This overview does not expose resume file downloads.")

    with reviews_tab:
        st.subheader("Recruiter review activity")

        with get_connection() as con:
            rows = con.execute("""
                SELECT
                    rr.review_id,
                    rr.review_status,
                    rr.review_comments,
                    datetime(
                        rr.reviewed_at,
                        '+5 hours',
                        '+30 minutes'
                    ) AS reviewed_at_ist,
                    recruiter.full_name AS recruiter_name,
                    candidate.full_name AS candidate_name,
                    a.analysis_id
                FROM recruiter_reviews rr
                JOIN users recruiter
                    ON recruiter.user_id = rr.recruiter_id
                JOIN analyses a
                    ON a.analysis_id = rr.analysis_id
                JOIN resumes r
                    ON r.resume_id = a.resume_id
                JOIN users candidate
                    ON candidate.user_id = r.user_id
                ORDER BY rr.reviewed_at DESC
                LIMIT 100
            """).fetchall()

        if rows:
            st.dataframe([
                {
                    "Review ID": r["review_id"],
                    "Recruiter": r["recruiter_name"],
                    "Candidate": r["candidate_name"],
                    "Analysis ID": r["analysis_id"],
                    "Status": r["review_status"],
                    "Comments": r["review_comments"],
                    "Reviewed at (IST)": r["reviewed_at_ist"]
                }
                for r in rows
            ], use_container_width=True, hide_index=True)
        else:
            st.info("No recruiter reviews have been submitted yet.")
    with settings_tab:
        st.subheader("System settings")
        with st.form("admin_setting_form"):
            name = st.text_input("Setting name", placeholder="e.g. support_email")
            value = st.text_area("Setting value")
            submitted = st.form_submit_button("Save setting", type="primary")
        if submitted:
            if not name.strip() or not value.strip():
                st.error("Both setting name and value are required.")
            else:
                with get_connection() as con:
                    con.execute(
                        """INSERT INTO system_settings (setting_name, setting_value, updated_by, updated_at)
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                           ON CONFLICT(setting_name) DO UPDATE SET
                           setting_value=excluded.setting_value, updated_by=excluded.updated_by,
                           updated_at=CURRENT_TIMESTAMP""",
                        (name.strip(), value.strip(), user["user_id"])
                    )
                st.success("Setting saved.")
                st.rerun()
        with get_connection() as con:
            rows = con.execute(
                """SELECT setting_name, setting_value,
          datetime(updated_at, '+5 hours', '+30 minutes') AS updated_at_ist
   FROM system_settings ORDER BY setting_name"""
            ).fetchall()
        if rows:
            st.dataframe(
                [
                    {
                        "Setting": r["setting_name"],
                        "Value": r["setting_value"],
                        "Updated at (IST)": r["updated_at_ist"]
                    }
                    for r in rows
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No system settings have been added yet.")

    st.divider()
    st.caption("Resume Analyzer · Administrative controls")
