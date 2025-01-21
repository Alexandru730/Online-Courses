Sure! Here's the `README.md` in English:

```markdown
# Online Course Platform

This application implements an online course platform where users can create, view, and review courses. It is built using **Flask** for the backend and **SQLite** for database management.

## Features

- **User Authentication**: Users can create accounts and log in. There are three types of users:
  - **Admins**: Can approve or reject courses, view all data, and manage users.
  - **Instructors**: Can create and manage courses, upload materials, and view reviews.
  - **Students**: Can enroll in courses, view materials, and leave reviews.

- **Courses**:
  - Instructors can create courses, and admins can approve them.
  - Courses are associated with categories to make searching easier.

- **Course Materials**: Instructors can upload course materials, including documents and videos.

- **Ratings and Reviews**: Students can leave reviews and answer questions for the courses they are enrolled in.

- **Course Enrollment**: Students can enroll in courses and view course materials.

---

## Installation

Follow the steps below to set up and run the application locally.

### 1. Clone the repository

```bash
git clone https://github.com/<username>/online-course-platform.git
cd online-course-platform
```

### 2. Create a virtual environment

It is recommended to use a virtual environment for installing the application dependencies.

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

Install all the required dependencies by using `pip`.

```bash
pip install -r requirements.txt
```

### 4. Configure the database

The application uses **SQLite** for data storage. The database will be automatically created the first time the app is run.

### 5. Run the application

To run the application, use the following command:

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000/`.

---

## Directory Structure

```plaintext
online-course-platform/
│
├── app.py                # The main file that runs the Flask application
├── static/               # Static files (CSS, JS, images)
├── templates/            # HTML templates for the front-end
├── OnlineCoursesDB.      # SQL database backup
├── README.md             # This file
└── .gitignore            # Files to be ignored by Git
```

---

## SQL Queries

### Simple Queries

- **Get all courses:**
  ```sql
  SELECT * FROM courses;
  ```

- **Get a list of all students enrolled in a course:**
  ```sql
  SELECT students.name FROM students
  JOIN enrollments ON students.id = enrollments.student_id
  WHERE enrollments.course_id = <course_id>;
  ```

### Complex Queries

- **Get all courses created by an instructor, including course details and the number of students enrolled:**
  ```sql
  SELECT courses.title, COUNT(enrollments.student_id) AS num_students
  FROM courses
  LEFT JOIN enrollments ON courses.id = enrollments.course_id
  WHERE courses.instructor_id = <instructor_id>
  GROUP BY courses.id;
  ```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

For any questions or feedback, feel free to open an issue or reach out to [your-email@example.com].
```

You can customize the fields like repository URL, contact email, or any other details specific to your project. Let me know if you need anything else!
