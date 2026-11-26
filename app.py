from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import random
import smtplib

app = Flask(__name__)
app.secret_key = "campus-innovate-hub-secret-key"

SENDER_EMAIL = "narayanjhanvi1@gmail.com"
SENDER_APP_PASSWORD = "hcsv jjnq kfdu kmjt"


# ---------------- DB CONNECTION HELPER ----------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="campus_innovate_hub"
    )


# ---------------- RULE-BASED INNOVATION SCORING ----------------
def calculate_innovation_score(title, description, category, required_skills):
    score = 20

    words = len(description.split())
    if words >= 40:
        score += 30
    elif words >= 20:
        score += 20
    elif words >= 10:
        score += 10

    if len(title.strip()) >= 10:
        score += 5

    impact_keywords = [
        "ai", "automation", "smart", "sustainable", "campus", "real-time",
        "scalable", "accessible", "efficiency", "solve", "analytics", "ml"
    ]
    desc_lower = (title + " " + description).lower()
    matched_keywords = sum(1 for kw in impact_keywords if kw in desc_lower)
    score += min(matched_keywords * 5, 25)

    skills_list = [s.strip() for s in required_skills.split(",") if s.strip()]
    score += min(len(skills_list) * 5, 15)

    if category in ["Technology", "Healthcare", "Environment", "Education"]:
        score += 5

    return min(score, 100)


# ---------------- SKILL MATCHING HELPER ----------------
def calculate_skill_match(user_skills_str, required_skills_str):
    if not user_skills_str or not required_skills_str:
        return 0
    user_skills = {s.strip().lower() for s in user_skills_str.split(",") if s.strip()}
    req_skills = {s.strip().lower() for s in required_skills_str.split(",") if s.strip()}
    if not req_skills:
        return 0
    matched = user_skills.intersection(req_skills)
    return int((len(matched) / len(req_skills)) * 100)


# ---------------- EMAIL OTP HELPER ----------------
def send_otp_email(recipient_email, otp, purpose="Registration"):
    message = (
        f"Subject: Campus Innovate Hub - {purpose} OTP\n\n"
        f"Your 6-digit OTP for {purpose} is: {otp}\n\n"
        f"Do not share this code with anyone."
    )
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, message)


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER & OTP ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        role = request.form["role"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        cursor.close()
        db.close()

        if existing_user:
            flash("This email is already registered.", "error")
            return render_template("register.html")

        otp = str(random.randint(100000, 999999))
        session["pending_user"] = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "role": role,
            "otp": otp
        }

        try:
            send_otp_email(email, otp, "Account Verification")
            flash(f"A 6-digit OTP has been sent to {email}.", "success")
            return redirect(url_for("verify_otp"))
        except Exception as e:
            flash(f"Failed to send OTP email: {e}", "error")

    return render_template("register.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    pending = session.get("pending_user")
    if not pending:
        return redirect(url_for("register"))

    if request.method == "POST":
        entered_otp = request.form["otp"].strip()

        if entered_otp == pending["otp"]:
            db = get_db()
            cursor = db.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                    (pending["name"], pending["email"], pending["password"], pending["role"])
                )
                user_id = cursor.lastrowid

                if pending["role"] == "student":
                    cursor.execute(
                        "INSERT INTO student_profile (user_id, skills, interests, bio) VALUES (%s, %s, %s, %s)",
                        (user_id, "", "", "")
                    )
                elif pending["role"] == "mentor":
                    cursor.execute(
                        "INSERT INTO mentors (user_id, expertise, experience, availability, bio) VALUES (%s, %s, %s, %s, %s)",
                        (user_id, "General Tech & Project Guidance", "2+ Years", "Weekends", "Mentor ready to guide student builders.")
                    )

                db.commit()
                session.pop("pending_user", None)
                flash("Email verified! Account created successfully. Please log in.", "success")
                return redirect(url_for("login"))
            finally:
                cursor.close()
                db.close()
        else:
            flash("Invalid OTP. Please check your email and try again.", "error")

    return render_template("verify_otp.html", email=pending["email"])


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# ---------------- FORGOT & RESET PASSWORD VIA EMAIL OTP ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if not user:
            flash("No account found with this email address.", "error")
            return render_template("forgot_password.html")

        otp = str(random.randint(100000, 999999))
        session["reset_pw"] = {
            "email": email,
            "otp": otp
        }

        try:
            send_otp_email(email, otp, "Password Reset")
            flash(f"A 6-digit password reset OTP has been sent to {email}.", "success")
            return redirect(url_for("reset_password"))
        except Exception as e:
            flash(f"Could not send reset OTP: {e}", "error")

    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    reset_data = session.get("reset_pw")
    if not reset_data:
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        entered_otp = request.form["otp"].strip()
        new_password = request.form["new_password"]

        if entered_otp != reset_data["otp"]:
            flash("Invalid OTP. Please check your email and try again.", "error")
            return render_template("reset_password.html", email=reset_data["email"])

        hashed_pw = generate_password_hash(new_password)
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_pw, reset_data["email"]))
        db.commit()
        cursor.close()
        db.close()

        session.pop("reset_pw", None)
        flash("Password reset successful! You can now log in with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", email=reset_data["email"])


# ---------------- DASHBOARD (WITH REAL-TIME DB STATS) ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(DISTINCT ideas.id) AS count
        FROM ideas
        LEFT JOIN teams ON teams.idea_id = ideas.id
        LEFT JOIN team_members ON team_members.team_id = teams.id
        WHERE ideas.user_id = %s OR team_members.student_id = %s
    """, (session["user_id"], session["user_id"]))
    my_ideas_count = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(DISTINCT ideas.id) AS count
        FROM project_progress pp
        JOIN ideas ON pp.idea_id = ideas.id
        LEFT JOIN teams ON teams.idea_id = ideas.id
        LEFT JOIN team_members ON team_members.team_id = teams.id
        WHERE (ideas.user_id = %s OR team_members.student_id = %s) AND pp.current_stage = 4
    """, (session["user_id"], session["user_id"]))
    is_launched = cursor.fetchone()["count"] > 0

    cursor.execute("SELECT COUNT(*) AS total_ideas, COALESCE(ROUND(AVG(innovation_score)), 0) AS avg_score FROM ideas")
    idea_stats = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS total_teams FROM teams")
    total_teams = cursor.fetchone()["total_teams"]

    cursor.execute("SELECT COUNT(*) AS total_mentors FROM mentors")
    total_mentors = cursor.fetchone()["total_mentors"]

    stats = {
        "total_ideas": idea_stats["total_ideas"],
        "avg_score": idea_stats["avg_score"],
        "total_teams": total_teams,
        "total_mentors": total_mentors
    }

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        name=session["name"],
        role=session["role"],
        has_idea=my_ideas_count > 0,
        is_launched=is_launched,
        stats=stats
    )


# ---------------- PROFILE ----------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        if session["role"] == "student":
            course = request.form.get("course", "")
            college = request.form.get("college", "")
            skills = request.form.get("skills", "")
            interests = request.form.get("interests", "")
            bio = request.form.get("bio", "")
            cursor.execute("""
                UPDATE student_profile
                SET course=%s, college=%s, skills=%s, interests=%s, bio=%s
                WHERE user_id=%s
            """, (course, college, skills, interests, bio, session["user_id"]))
        elif session["role"] == "mentor":
            expertise = request.form.get("expertise", "")
            experience = request.form.get("experience", "")
            availability = request.form.get("availability", "")
            bio = request.form.get("bio", "")
            cursor.execute("""
                UPDATE mentors
                SET expertise=%s, experience=%s, availability=%s, bio=%s
                WHERE user_id=%s
            """, (expertise, experience, availability, bio, session["user_id"]))

        db.commit()
        flash("Profile updated successfully!", "success")
        cursor.close()
        db.close()
        return redirect(url_for("profile"))

    if session["role"] == "student":
        cursor.execute("SELECT * FROM student_profile WHERE user_id = %s", (session["user_id"],))
    else:
        cursor.execute("SELECT * FROM mentors WHERE user_id = %s", (session["user_id"],))

    profile_data = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template("profile.html", profile=profile_data, role=session["role"], name=session["name"])


# ---------------- IDEAS (SUBMIT + SEARCH + FILTER + EDIT + DELETE) ----------------
@app.route("/ideas", methods=["GET", "POST"])
def ideas():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action", "create")

        if action == "delete":
            idea_id = request.form["idea_id"]
            cursor.execute("DELETE FROM ideas WHERE id = %s AND user_id = %s", (idea_id, session["user_id"]))
            db.commit()
            cursor.close()
            db.close()
            flash("Idea deleted successfully.", "success")
            return redirect(url_for("ideas"))

        title = request.form["title"].strip()
        description = request.form["description"].strip()
        category = request.form["category"]
        required_skills = request.form.get("required_skills", "").strip()

        score = calculate_innovation_score(title, description, category, required_skills)

        cursor.execute("""
            INSERT INTO ideas (user_id, title, description, category, required_skills, innovation_score)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session["user_id"], title, description, category, required_skills, score))
        idea_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO project_progress (idea_id, current_stage, stage_name) VALUES (%s, 1, 'Idea & Validation')",
            (idea_id,)
        )
        cursor.execute(
            "INSERT INTO teams (idea_id, team_name) VALUES (%s, %s)",
            (idea_id, f"{title} Team")
        )
        team_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO team_members (team_id, student_id) VALUES (%s, %s)",
            (team_id, session["user_id"])
        )

        db.commit()
        cursor.close()
        db.close()
        flash(f"Idea submitted! Rule-Based Innovation Score: {score}/100", "success")
        return redirect(url_for("ideas"))

    search_q = request.args.get("q", "").strip()
    cat_filter = request.args.get("category", "").strip()

    cursor.execute("SELECT skills FROM student_profile WHERE user_id = %s", (session["user_id"],))
    student_row = cursor.fetchone()
    user_skills = student_row["skills"] if student_row else ""

    query = """
        SELECT ideas.*, users.name AS author, teams.id AS team_id
        FROM ideas
        JOIN users ON ideas.user_id = users.id
        LEFT JOIN teams ON teams.idea_id = ideas.id
        WHERE 1=1
    """
    params = []

    if search_q:
        query += " AND (ideas.title LIKE %s OR ideas.description LIKE %s OR ideas.required_skills LIKE %s)"
        like_q = f"%{search_q}%"
        params.extend([like_q, like_q, like_q])

    if cat_filter:
        query += " AND ideas.category = %s"
        params.append(cat_filter)

    query += " ORDER BY ideas.innovation_score DESC, ideas.created_at DESC"
    cursor.execute(query, tuple(params))
    all_ideas = cursor.fetchall()

    for idea in all_ideas:
        idea["skill_match"] = calculate_skill_match(user_skills, idea["required_skills"])

    cursor.close()
    db.close()
    return render_template(
        "ideas.html",
        ideas=all_ideas,
        user_skills=user_skills,
        search_q=search_q,
        cat_filter=cat_filter,
        current_user_id=session["user_id"]
    )


# ---------------- EDIT IDEA (WITH SCORE RE-CALCULATION) ----------------
@app.route("/edit-idea/<int:idea_id>", methods=["GET", "POST"])
def edit_idea(idea_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ideas WHERE id = %s AND user_id = %s", (idea_id, session["user_id"]))
    idea = cursor.fetchone()

    if not idea:
        cursor.close()
        db.close()
        flash("Idea not found or you do not have permission to edit it.", "error")
        return redirect(url_for("ideas"))

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        category = request.form["category"]
        required_skills = request.form.get("required_skills", "").strip()
        new_score = calculate_innovation_score(title, description, category, required_skills)

        cursor.execute("""
            UPDATE ideas
            SET title = %s, description = %s, category = %s, required_skills = %s, innovation_score = %s
            WHERE id = %s AND user_id = %s
        """, (title, description, category, required_skills, new_score, idea_id, session["user_id"]))

        cursor.execute("UPDATE teams SET team_name = %s WHERE idea_id = %s", (f"{title} Team", idea_id))
        db.commit()
        cursor.close()
        db.close()
        flash(f"Idea updated! Recalculated Innovation Score: {new_score}/100", "success")
        return redirect(url_for("ideas"))

    cursor.close()
    db.close()
    return render_template("edit_idea.html", idea=idea)


# ---------------- TEAMS (JOIN WITH 4-MEMBER CAP & LEAVE TEAM) ----------------
@app.route("/teams", methods=["GET", "POST"])
def teams():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        team_id = request.form["team_id"]
        action = request.form.get("action", "join")

        if action == "leave":
            cursor.execute("""
                SELECT ideas.user_id AS lead_id
                FROM teams JOIN ideas ON teams.idea_id = ideas.id
                WHERE teams.id = %s
            """, (team_id,))
            row = cursor.fetchone()
            if row and row["lead_id"] == session["user_id"]:
                flash("Project Lead cannot leave their own team. You can manage or delete the idea from Ideas.", "info")
            else:
                cursor.execute(
                    "DELETE FROM team_members WHERE team_id = %s AND student_id = %s",
                    (team_id, session["user_id"])
                )
                db.commit()
                flash("You have left the project team.", "success")
        else:
            cursor.execute(
                "SELECT id FROM team_members WHERE team_id = %s AND student_id = %s",
                (team_id, session["user_id"])
            )
            if cursor.fetchone():
                flash("You are already a member of this team.", "info")
            else:
                cursor.execute("SELECT COUNT(*) AS cnt FROM team_members WHERE team_id = %s", (team_id,))
                if cursor.fetchone()["cnt"] >= 4:
                    flash("This team has reached its maximum capacity of 4 members.", "error")
                else:
                    cursor.execute(
                        "INSERT INTO team_members (team_id, student_id) VALUES (%s, %s)",
                        (team_id, session["user_id"])
                    )
                    db.commit()
                    flash("You joined the project team! Open Project Workspace to chat and track milestones.", "success")

    cursor.execute("""
        SELECT teams.id AS team_id, teams.team_name, ideas.id AS idea_id,
               ideas.user_id AS lead_id, ideas.title AS idea_title,
               ideas.description AS idea_description,
               ideas.required_skills, users.name AS lead_name
        FROM teams
        JOIN ideas ON teams.idea_id = ideas.id
        JOIN users ON ideas.user_id = users.id
    """)
    all_teams = cursor.fetchall()

    for team in all_teams:
        cursor.execute("""
            SELECT users.id, users.name, users.email, student_profile.skills
            FROM team_members
            JOIN users ON team_members.student_id = users.id
            LEFT JOIN student_profile ON users.id = student_profile.user_id
            WHERE team_members.team_id = %s
        """, (team["team_id"],))
        members = cursor.fetchall()
        team["members"] = members
        team["is_member"] = any(m["id"] == session["user_id"] for m in members)
        team["is_lead"] = (team["lead_id"] == session["user_id"])

    cursor.close()
    db.close()
    return render_template("teams.html", teams=all_teams)


# ---------------- SHARED PROJECT WORKSPACE, MILESTONES & TEAM/MENTOR CHAT ----------------
@app.route("/progress", methods=["GET", "POST"])
def progress():
    if "user_id" not in session:
        return redirect(url_for("login"))

    stages = {
        1: "Idea & Validation",
        2: "Prototype Development",
        3: "Testing & Mentor Review",
        4: "Final Launch"
    }

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action", "update_stage")
        idea_id = request.form["idea_id"]

        if action == "send_message":
            channel = request.form.get("channel", "team")
            msg_text = request.form.get("message", "").strip()
            if msg_text:
                cursor.execute("""
                    INSERT INTO project_messages (idea_id, sender_id, sender_role, channel, message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (idea_id, session["user_id"], session["role"], channel, msg_text))
                db.commit()
                flash("Message posted!", "success")
        else:
            new_stage = int(request.form["current_stage"])
            stage_name = stages.get(new_stage, "Idea & Validation")

            cursor.execute("""
                UPDATE project_progress
                SET current_stage = %s, stage_name = %s
                WHERE idea_id = %s
            """, (new_stage, stage_name, idea_id))

            cursor.execute(
                "UPDATE ideas SET status = %s WHERE id = %s",
                (stage_name, idea_id)
            )
            db.commit()
            flash("Project milestone updated!", "success")

    cursor.execute("""
        SELECT DISTINCT ideas.id AS idea_id, ideas.title, ideas.description,
               ideas.category, ideas.required_skills, ideas.innovation_score,
               ideas.created_at, owner.name AS lead_name,
               COALESCE(project_progress.current_stage, 1) AS current_stage,
               COALESCE(project_progress.stage_name, 'Idea & Validation') AS stage_name
        FROM ideas
        JOIN users owner ON ideas.user_id = owner.id
        LEFT JOIN teams ON teams.idea_id = ideas.id
        LEFT JOIN team_members ON team_members.team_id = teams.id
        LEFT JOIN mentor_requests ON mentor_requests.idea_id = ideas.id
        LEFT JOIN mentors ON mentor_requests.mentor_id = mentors.id
        LEFT JOIN project_progress ON ideas.id = project_progress.idea_id
        WHERE ideas.user_id = %s
           OR team_members.student_id = %s
           OR (mentors.user_id = %s AND mentor_requests.status = 'Accepted')
        ORDER BY ideas.created_at DESC
    """, (session["user_id"], session["user_id"], session["user_id"]))
    my_projects = cursor.fetchall()

    for proj in my_projects:
        cursor.execute("""
            SELECT users.name, users.email, student_profile.skills
            FROM teams
            JOIN team_members ON team_members.team_id = teams.id
            JOIN users ON team_members.student_id = users.id
            LEFT JOIN student_profile ON users.id = student_profile.user_id
            WHERE teams.idea_id = %s
        """, (proj["idea_id"],))
        proj["team_members"] = cursor.fetchall()

        cursor.execute("""
            SELECT users.name AS mentor_name, mentor_requests.status
            FROM mentor_requests
            JOIN mentors ON mentor_requests.mentor_id = mentors.id
            JOIN users ON mentors.user_id = users.id
            WHERE mentor_requests.idea_id = %s
            ORDER BY mentor_requests.created_at DESC LIMIT 1
        """, (proj["idea_id"],))
        proj["mentor_info"] = cursor.fetchone()

        cursor.execute("""
            SELECT pm.*, users.name AS sender_name
            FROM project_messages pm
            JOIN users ON pm.sender_id = users.id
            WHERE pm.idea_id = %s
            ORDER BY pm.created_at ASC
        """, (proj["idea_id"],))
        all_msgs = cursor.fetchall()
        proj["team_chat"] = [m for m in all_msgs if m["channel"] == "team"]
        proj["mentor_chat"] = [m for m in all_msgs if m["channel"] == "mentor"]

    cursor.close()
    db.close()
    return render_template("progress.html", projects=my_projects, stages=stages)


# ---------------- MENTOR MODULE ----------------
@app.route("/mentor", methods=["GET", "POST"])
def mentor():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action", "send_request")

        if action == "respond_request" and session["role"] == "mentor":
            req_id = request.form["request_id"]
            decision = request.form["decision"]
            cursor.execute(
                "UPDATE mentor_requests SET status = %s WHERE id = %s",
                (decision, req_id)
            )
            db.commit()
            flash(f"Mentorship request marked as {decision}.", "success")
            cursor.close()
            db.close()
            return redirect(url_for("mentor"))

        mentor_id = request.form["mentor_id"]
        idea_id = request.form.get("idea_id") or None
        message = request.form.get("message", "Looking for mentorship on my project.")

        cursor.execute("""
            SELECT id FROM mentor_requests
            WHERE student_id = %s AND mentor_id = %s AND status = 'Pending'
        """, (session["user_id"], mentor_id))
        if cursor.fetchone():
            flash("You already have a pending mentorship request with this mentor.", "info")
            cursor.close()
            db.close()
            return redirect(url_for("mentor"))

        cursor.execute("""
            INSERT INTO mentor_requests (student_id, mentor_id, idea_id, message, status)
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (session["user_id"], mentor_id, idea_id, message))
        db.commit()
        flash("Mentorship request sent!", "success")
        cursor.close()
        db.close()
        return redirect(url_for("mentor"))

    cursor.execute("""
        SELECT mentors.id, mentors.user_id, mentors.expertise,
               mentors.experience, mentors.availability, mentors.bio, users.name, users.email
        FROM mentors
        JOIN users ON mentors.user_id = users.id
    """)
    mentors = cursor.fetchall()

    cursor.execute("SELECT id, title FROM ideas WHERE user_id = %s", (session["user_id"],))
    my_ideas = cursor.fetchall()

    cursor.execute("""
        SELECT mentor_requests.*, users.name AS mentor_name, users.email AS mentor_email,
               ideas.title AS idea_title
        FROM mentor_requests
        JOIN mentors ON mentor_requests.mentor_id = mentors.id
        JOIN users ON mentors.user_id = users.id
        LEFT JOIN ideas ON mentor_requests.idea_id = ideas.id
        WHERE mentor_requests.student_id = %s
        ORDER BY mentor_requests.created_at DESC
    """, (session["user_id"],))
    sent_requests = cursor.fetchall()

    incoming_requests = []
    if session["role"] == "mentor":
        cursor.execute("""
            SELECT mentor_requests.*, users.name AS student_name, users.email AS student_email,
                   ideas.title AS idea_title
            FROM mentor_requests
            JOIN mentors ON mentor_requests.mentor_id = mentors.id
            JOIN users ON mentor_requests.student_id = users.id
            LEFT JOIN ideas ON mentor_requests.idea_id = ideas.id
            WHERE mentors.user_id = %s
            ORDER BY mentor_requests.created_at DESC
        """, (session["user_id"],))
        incoming_requests = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template(
        "mentor.html",
        mentors=mentors,
        my_ideas=my_ideas,
        sent_requests=sent_requests,
        incoming_requests=incoming_requests,
        role=session["role"]
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)