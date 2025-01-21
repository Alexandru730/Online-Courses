from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import pyodbc
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'

def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=OnlineCoursesDB;'
        'Encrypt=no;'
        'Trusted_Connection=yes;'
    )
    return conn


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['Email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE Email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user.Parola, password):
            session['user_id'] = user.UserID  # Salveaza ID-ul utilizatorului in sesiune
            session['role'] = user.Rol  # Salveaza rolul utilizatorului in sesiune
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['Email']
        password = request.form['password']
        role = request.form['role']
        phone = request.form.get('phone', '')

        # Validare pentru email si telefon deja existente
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificam daca email-ul exista deja
        cursor.execute("SELECT * FROM Users WHERE Email = ?", (email,))
        existing_user_email = cursor.fetchone()

        # Verificam daca numarul de telefon exista deja
        cursor.execute("SELECT * FROM Users WHERE Telefon = ?", (phone,))
        existing_user_phone = cursor.fetchone()

        if existing_user_email:
            flash('Email-ul introdus este deja inregistrat. Te rugam sa folosesti alt email.', 'danger')
            conn.close()
            return redirect(url_for('register'))

        if existing_user_phone:
            flash('Numarul de telefon introdus este deja inregistrat. Te rugam sa folosesti alt numar.', 'danger')
            conn.close()
            return redirect(url_for('register'))

        # Cream parola hash-uita
        hashed_password = generate_password_hash(password)

        try:
            # Introducem noul utilizator in baza de date
            cursor.execute(
                "INSERT INTO Users (Nume, Email, Parola, Rol, Telefon) VALUES (?, ?, ?, ?, ?)",
                (name, email, hashed_password, role, phone)
            )
            conn.commit()
            conn.close()

            flash('Inregistrare reusita! Poti acum sa te autentifici.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Eroare la inregistrare: {str(e)}', 'danger')
            conn.close()

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    user_role = session.get('role')

    if not user_role:
        flash('Access denied. Please log in.', 'danger')
        return redirect(url_for('login'))

    # Redirectionam utilizatorii pe baza rolului
    if user_role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user_role == 'instructor':
        return redirect(url_for('instructor_dashboard'))
    elif user_role == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        flash('Invalid role!', 'danger')
        return redirect(url_for('login'))


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    # Daca utilizatorul a selectat o optiune (studenti, profesori, cursuri pendinte), il redirectionam
    if request.method == 'POST':
        option = request.form['option']
        if option == 'students':
            return redirect(url_for('students_list'))
        elif option == 'professors':
            return redirect(url_for('instructors_list'))
        elif option == 'pending_courses':
            return redirect(url_for('pending_courses'))

    # Pagina de selectie
    return render_template('admin_dashboard.html')

@app.route('/students_list')
def students_list():
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT UserID, Nume, Email, Telefon FROM Users WHERE Rol = 'student'")

    students = cursor.fetchall()
    conn.close()

    return render_template('students_list.html', students=students)

@app.route('/instructors_list')
def instructors_list():
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT UserID, Nume, Email, Telefon FROM Users WHERE Rol = 'instructor'")

    instructors = cursor.fetchall()
    conn.close()

    return render_template('instructors_list.html', instructors=instructors)

@app.route('/pending_courses')
def pending_courses():
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Selectam informatiile relevante despre cursuri si asociem cu instructorul
    cursor.execute("""
       SELECT 
    pc.Pending_courseID, 
    pc.Nume_curs, 
    pc.Descriere, 
    -- Obtinem primul material asociat (folosind TOP 1 pentru SQL Server)
    (
        SELECT TOP 1 cm.Nume_fisier
        FROM Course_Materials cm
        WHERE cm.CourseID = pc.Pending_courseID
    ) AS Nume_fisier,
    (
        SELECT TOP 1 cm.Tip_material
        FROM Course_Materials cm
        WHERE cm.CourseID = pc.Pending_courseID
    ) AS Tip_material,
    (
        SELECT TOP 1 cm.Url_fisier
        FROM Course_Materials cm
        WHERE cm.CourseID = pc.Pending_courseID
    ) AS Url_fisier,
    (
        SELECT u.Nume
        FROM Users u
        WHERE u.UserID = pc.InstructorID
    ) AS Nume_profesor,
    (
        SELECT u.Email
        FROM Users u
        WHERE u.UserID = pc.InstructorID
    ) AS Email_profesor,
    (
        SELECT u.Telefon
        FROM Users u
        WHERE u.UserID = pc.InstructorID
    ) AS Telefon_profesor
FROM 
    Pending_Courses pc
WHERE 
    pc.Status_curs = 'pending'

    """)

    pending_courses = cursor.fetchall()
    conn.close()

    return render_template('pending_courses.html', courses=pending_courses)


@app.route('/delete_student/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    
    cursor.execute("DELETE FROM Users WHERE UserID = ?", (user_id,))
    conn.commit()

    conn.close()
    flash('Studentul a fost sters cu succes!', 'success')
    return redirect(url_for('students_list'))

@app.route('/delete_instructor/<int:instructor_id>', methods=['POST'])
def delete_instructor(instructor_id):
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Users WHERE UserID = ?", (instructor_id,))
    conn.commit()
    conn.close()

    flash('Instructorul a fost sters!', 'success')
    return redirect(url_for('instructors_list'))


@app.route('/approve_course/<int:pending_course_id>', methods=['POST'])
def approve_course(pending_course_id):
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtinem detaliile cursului din Pending_Courses
    cursor.execute("""
        SELECT Nume_curs, Descriere, InstructorID
        FROM Pending_Courses
        WHERE Pending_courseID = ?
    """, (pending_course_id,))
    pending_course = cursor.fetchone()

    if not pending_course:
        conn.close()
        flash('Course not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Mutam cursul in tabela Courses (IDENTITY va genera automat ID-ul)
    cursor.execute("""
        INSERT INTO Courses (Nume_curs, Descriere, InstructorID)
        VALUES (?, ?, ?)
    """, (pending_course.Nume_curs, pending_course.Descriere, pending_course.InstructorID))
    conn.commit()

    # Asociem cursul aprobat cu categoriile selectate
    categories = session.pop('pending_categories', [])
    if categories:
        # Nu mai este nevoie de SCOPE_IDENTITY() pentru a obtine ID-ul, deoarece este generat automat
        cursor.execute("SELECT @@IDENTITY AS NewCourseID")
        new_course_id = cursor.fetchone().NewCourseID
        for category_id in categories:
            cursor.execute("""
                INSERT INTO Course_Category_Association (CourseID, CategoryID)
                VALUES (?, ?)
            """, (new_course_id, category_id))
        conn.commit()
    else:
        flash('No categories selected. The course was approved without category association.', 'warning')

    # Stergem cursul din Pending_Courses
    cursor.execute("DELETE FROM Pending_Courses WHERE Pending_courseID = ?", (pending_course_id,))
    conn.commit()

    conn.close()
    flash('Course approved and added to the catalog!', 'success')
    return redirect(url_for('pending_courses'))


@app.route('/top_courses')
def top_courses():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Executa interogarea SQL pentru a obtine top 5 cursuri pe baza recenziilor
    cursor.execute("""
        SELECT TOP 5
            c.CourseID,
            c.Nume_curs,
            c.Descriere,
            (
                SELECT AVG(r.Rating)
                FROM Course_Reviews r
                WHERE r.CourseID = c.CourseID
            ) AS AverageRating
        FROM 
            Courses c
        WHERE EXISTS (
            SELECT 1
            FROM Course_Reviews r
            WHERE r.CourseID = c.CourseID
        )
        ORDER BY AverageRating DESC;
    """)

    top_courses = cursor.fetchall()
    conn.close()

    return render_template('top_courses_by_reviews.html', courses=top_courses)





@app.route('/reject_course/<int:course_id>', methods=['POST'])
def reject_course(course_id):
    if session.get('role') != 'admin':
        flash('Access denied. Admins only!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Actualizeaza statusul cursului la 'rejected'
    cursor.execute("""
        UPDATE Pending_Courses
        SET Status_curs = 'rejected'
        WHERE Pending_courseID = ?
    """, (course_id,))
    

    conn.commit()
    conn.close()

    flash('Course rejected and removed from pending list!', 'danger')
    return redirect(url_for('pending_courses'))

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        flash('Access denied. Students only!', 'danger')
        return redirect(url_for('index'))

    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Cursuri la care studentul este inscris
    cursor.execute("""
        SELECT CourseID, Nume_curs, Descriere
        FROM Courses
        WHERE CourseID IN (
            SELECT CourseID
            FROM Enrollments
            WHERE UserID = ?
        )
    """, (student_id,))
    enrolled_courses = cursor.fetchall()

    # Cursuri disponibile (la care studentul NU este inscris)
    cursor.execute("""
        SELECT CourseID, Nume_curs, Descriere
        FROM Courses
        WHERE CourseID NOT IN (
            SELECT CourseID
            FROM Enrollments
            WHERE UserID = ?
        )
    """, (student_id,))
    available_courses = cursor.fetchall()

    conn.close()

    return render_template(
        'student_dashboard.html',
        enrolled_courses=enrolled_courses,
        available_courses=available_courses
    )


@app.route('/enroll/<int:course_id>', methods=['POST'])
def enroll(course_id):
    if session.get('role') != 'student':
        flash('Access denied. Students only!', 'danger')
        return redirect(url_for('index'))

    student_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificam daca studentul este deja inscris
    cursor.execute("""
        SELECT COUNT(*)
        FROM Enrollments
        WHERE UserID = ? AND CourseID = ?
    """, (student_id, course_id))
    already_enrolled = cursor.fetchone()[0]

    if already_enrolled:
        flash('Sunteti deja inscris la acest curs!', 'warning')
    else:
        # Inscriem studentul la curs
        cursor.execute("""
            INSERT INTO Enrollments (UserID, CourseID)
            VALUES (?, ?)
        """, (student_id, course_id))
        conn.commit()
        flash('V-ati inscris cu succes la curs!', 'success')

    conn.close()
    return redirect(url_for('student_dashboard'))


@app.route('/course/<int:course_id>', methods=['GET', 'POST'])
def view_course(course_id):
    # Verificam daca utilizatorul este logat si are rolul de student
    if session.get('role') != 'student':
        flash('Access denied. Students only!', 'danger')
        return redirect(url_for('index'))

    # Conectam la baza de date
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtinem informatiile cursului
    cursor.execute("SELECT CourseID, Nume_curs, Descriere FROM Courses WHERE CourseID = ?", (course_id,))
    course = cursor.fetchone()

    if not course:
        conn.close()
        flash('Cursul nu exista!', 'danger')
        return redirect(url_for('student_dashboard'))

    # Daca se face un POST, adaugam recenzia
    if request.method == 'POST':
        rating = request.form['rating']
        review = request.form['review']
        user_id = session.get('user_id')  # ID-ul utilizatorului conectat

        # Verificam daca utilizatorul a dat deja o recenzie la acest curs
        cursor.execute("""
            SELECT * FROM Course_Reviews WHERE UserID = ? AND CourseID = ?
        """, (user_id, course_id))
        existing_review = cursor.fetchone()

        if existing_review:
            flash('Ai deja o recenzie pentru acest curs!', 'warning')
        else:
            # Adaugam recenzia in baza de date
            cursor.execute("""
                INSERT INTO Course_Reviews (UserID, CourseID, Rating, Comentariu, Data_review)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, course_id, rating, review, datetime.now()))

            conn.commit()
            flash('Recenzia ta a fost adaugata cu succes!', 'success')

        # Redirectionam pentru a actualiza pagina si a nu trimite formularul de mai multe ori
        return redirect(url_for('view_course', course_id=course_id))

    # Obtinem recenziile cursului
    cursor.execute("""
        SELECT r.Rating, r.Comentariu, u.Nume
        FROM Course_Reviews r
        JOIN Users u ON r.UserID = u.UserID
        WHERE r.CourseID = ?
    """, (course_id,))
    reviews = cursor.fetchall()

    conn.close()

    return render_template(
        'view_course.html',
        course={
            'CourseID': course[0],
            'Nume_curs': course[1],
            'Descriere': course[2],
        },
        reviews=reviews
    )


@app.route('/view_material/<material_id>')
def view_material(material_id):
    if not session.get('user_id'):  # Verifica daca utilizatorul este autentificat
        flash("Trebuie sa fii autentificat pentru a accesa acest material.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT Url_fisier FROM Course_Materials WHERE MaterialID = ?", (material_id,))
    material = cursor.fetchone()

    if not material:
        flash("Material inexistent sau acces interzis.", "danger")
        return redirect(url_for('student_dashboard'))

    return redirect(material['Url_fisier'])

#trebuie facut pe viitor!!!!
# @app.route('/student_assessments/<int:course_id>')
# def student_assessments(course_id):
#     # Verificam daca studentul este inscris la cursul respectiv
#     student_id = session.get('user_id')
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT * FROM Enrollments
#         WHERE CourseID = ? AND UserID = ?
#     """, (course_id, student_id))
#     enrollment = cursor.fetchone()

#     if not enrollment:
#         flash('Nu sunteti inscris la acest curs!', 'danger')
#         return redirect(url_for('student_dashboard'))

#     # Preluam assessment-urile disponibile pentru cursul respectiv
#     cursor.execute("""
#         SELECT a.AssesmentID, a.Tip_assesment, a.Data_assesment, a.Max_punctaj
#         FROM Assesments a
#         WHERE a.CourseID = ?
#     """, (course_id,))
#     assessments = cursor.fetchall()
#     conn.close()

#     return render_template('student_assessments.html', assessments=assessments, course_id=course_id)

# @app.route('/start_assessment/<int:assesment_id>', methods=['GET', 'POST'])
# def start_assessment(assesment_id):
#     student_id = session.get('user_id')
    
#     # Verificam daca studentul este inscris la cursul asociat evaluarii
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT a.CourseID, s.UserID 
#         FROM Assesments a
#         JOIN Enrollments s ON a.CourseID = s.CourseID
#         WHERE a.AssesmentID = ? AND s.UserID = ?
#     """, (assesment_id, student_id))
#     course_enrollment = cursor.fetchone()

#     if not course_enrollment:
#         flash('Nu sunteti inscris la acest curs sau acest test nu exista!', 'danger')
#         return redirect(url_for('student_dashboard'))

#     # Preluam intrebarile si raspunsurile pentru assessment-ul selectat
#     cursor.execute("""
#         SELECT q.QuestionID, q.Question, r.AnswerID, r.Answer
#         FROM Questions q
#         JOIN Answers r ON q.QuestionID = r.QuestionID
#         WHERE q.AssesmentID = ?
#     """, (assesment_id,))
#     questions = cursor.fetchall()
#     conn.close()

#     if request.method == 'POST':
#         # Preluam raspunsurile studentului
#         answers = request.form.getlist('answers')  # Lista cu raspunsurile

#         # Calculam punctajul obtinut
#         score = 0
#         for answer_id in answers:
#             cursor = conn.cursor()
#             cursor.execute("""
#                 SELECT Correct FROM Answers WHERE AnswerID = ?
#             """, (answer_id,))
#             correct_answer = cursor.fetchone()

#             if correct_answer and correct_answer[0] == 1:
#                 score += 1  # Adaugam punctaj pentru raspuns corect

#         # Salvam punctajul obtinut in baza de date
#         cursor.execute("""
#             UPDATE Assesments
#             SET Punctaj_obtinut = ?
#             WHERE AssesmentID = ? AND UserID = ?
#         """, (score, assesment_id, student_id))
#         conn.commit()

#         flash('Testul a fost finalizat! Punctajul obtinut: ' + str(score), 'success')
#         return redirect(url_for('student_dashboard'))

#     return render_template('take_assessment.html', assessment_id=assesment_id, questions=questions)


@app.route('/instructor_dashboard')
def instructor_dashboard():
    if session.get('role') != 'instructor':
        flash('Access denied. Instructors only!', 'danger')
        return redirect(url_for('index'))

    user_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtinem notificarile necitite pentru instructor
    cursor.execute("SELECT * FROM Course_Notifications WHERE UserID = ? AND Status_notificare = 'necitit'", (user_id,))
    notifications = cursor.fetchall()

    # Daca instructorul a citit notificarile, le marcam ca citite
    if notifications:
        cursor.execute("UPDATE Course_Notifications SET Status_notificare = 'citit' WHERE UserID = ?", (user_id,))
        conn.commit()

    conn.close()

    return render_template('instructor_dashboard.html', notifications=notifications)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if session.get('role') != 'instructor':
        flash('Access denied. Instructors only!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        course_name = request.form['course_name']
        course_description = request.form['course_description']
        selected_categories = request.form.getlist('categories')  # Categoriile selectate

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Adaugam cursul in Pending_Courses
            cursor.execute(
                "INSERT INTO Pending_Courses (Nume_curs, Descriere, InstructorID, Status_curs) VALUES (?, ?, ?, ?)",
                (course_name, course_description, session.get('user_id'), 'pending')
            )
            conn.commit()

            # Obtinem ID-ul cursului adaugat
            cursor.execute("SELECT SCOPE_IDENTITY()")
            pending_course_id = cursor.fetchone()[0]

            # Adaugam categoriile (daca exista)
            if selected_categories:
                for category_id in selected_categories:
                    cursor.execute(
                        "INSERT INTO Course_Category_Association (CourseID, CategoryID) VALUES (?, ?)",
                        (pending_course_id, category_id)
                    )
                conn.commit()

            flash('Cursul a fost adaugat cu succes si este in asteptare pentru aprobare.', 'success')

            # Redirectionam utilizatorul la pagina de adaugare materiale curs
            return redirect(url_for('add_course_materials', course_id=pending_course_id))
        except Exception as e:
            conn.rollback()
            flash(f'A aparut o problema: {e}', 'danger')
        finally:
            conn.close()

    # Obtinem categoriile disponibile pentru formular
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT CategoryID, Nume_Categorie FROM Course_Categories")
    categories = cursor.fetchall()
    conn.close()

    return render_template('add_course.html', categories=categories)





# Adaugarea materialelor pentru un curs (pentru instructori)
@app.route('/add_course_materials/<int:course_id>', methods=['GET', 'POST'])
def add_course_materials(course_id):
    if session.get('role') != 'instructor':
        flash('Access denied. Instructors only!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        material_name = request.form['material_name']
        material_type = request.form['material_type']
        material_url = request.form['material_url']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Adaugam materialul pentru cursul specificat
            cursor.execute(
                "INSERT INTO Course_Materials (CourseID, Nume_fisier, Tip_material, Url_fisier) VALUES (?, ?, ?, ?)",
                (course_id, material_name, material_type, material_url)
            )
            conn.commit()
            flash('Materialul a fost adaugat cu succes!', 'success')

        except Exception as e:
            flash(f'Eroare la adaugarea materialului: {str(e)}', 'danger')

        conn.close()

    return render_template('add_course_materials.html', course_id=course_id)

@app.route('/finish_course/<int:course_id>', methods=['POST'])
def finish_course(course_id):
    if session.get('role') != 'instructor':
        flash('Access denied. Instructors only!', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Actualizam statutul cursului din "pending" in "publicat"
        cursor.execute("UPDATE Pending_Courses SET Status_curs = 'publicat' WHERE Pending_courseID = ?", (course_id,))
        conn.commit()

        # Mutam cursul din Pending_Courses in tabelul Courses
        cursor.execute("SELECT * FROM Pending_Courses WHERE Pending_courseID = ?", (course_id,))
        course = cursor.fetchone()

        if course:
            cursor.execute(
                "INSERT INTO Courses (Nume_curs, Descriere, InstructorID) VALUES (?, ?, ?)",
                (course.Nume_curs, course.Descriere, course.InstructorID)
            )
            conn.commit()

        flash('Cursul a fost publicat cu succes!', 'success')

    except Exception as e:
        flash(f'Eroare la finalizarea cursului: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('instructor_dashboard'))


@app.route('/add_review/<int:course_id>', methods=['GET', 'POST'])
def add_review(course_id):
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        user_id = session.get('user_id')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Adaugam recenzia in tabelul Course_Reviews
            cursor.execute(""" 
                INSERT INTO Course_Reviews (CourseID, UserID, Rating, Comentariu, Data_review)
                VALUES (?, ?, ?, ?, GETDATE())
            """, (course_id, user_id, rating, comment))
            conn.commit()
            flash('Recenzia a fost adaugata cu succes!', 'success')
        except Exception as e:
            flash(f'Eroare la adaugarea recenziei: {str(e)}', 'danger')
        finally:
            conn.close()

    return redirect(url_for('view_course_reviews', course_id=course_id))


@app.route('/view_course_reviews/<int:course_id>')
def view_course_reviews(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtinem recenziile pentru cursul dat
    cursor.execute("""
        SELECT Users.Nume, Course_Reviews.Rating, Course_Reviews.Comentariu, Course_Reviews.Data_review
        FROM Course_Reviews
        JOIN Users ON Course_Reviews.UserID = Users.UserID
        WHERE Course_Reviews.CourseID = ?
    """, (course_id,))
    reviews = cursor.fetchall()
    conn.close()

    return render_template('view_course_reviews.html', course_id=course_id, reviews=reviews)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('index'))

# Pornirea aplicatiei Flask
if __name__ == '__main__':
    app.run(debug=True)  