# Student Forum

This is a Django-based forum application where users can create posts, add solutions, and comment on solutions. The application supports user registration, login, and logout functionalities.

## Project Structure

## Setup Instructions

1. **Clone the repository:**

    ```sh
    git clone <https://github.com/HugoC1000/School-Forum>
    cd student_forum
    ```

2. **Create and activate a virtual environment:**

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Apply the migrations to set up the database:**

    ```sh
    python manage.py migrate
    ```

5. **Create a superuser to access the admin interface:**

    ```sh
    python manage.py createsuperuser
    ```

6. **Run the development server:**

    ```sh
    python manage.py runserver
    ```

7. **Access the application:**

    Open your web browser and go to [http://127.0.0.1:8000/](http://_vscodecontentref_/13).

## Database

The application uses PostgreSQL as the database. Ensure you have PostgreSQL installed and a database created for the application. Update the `DATABASES` setting in `student_forum/settings.py` with your database credentials.

## User Authentication

The application supports user registration, login, and logout functionalities. The following views handle user authentication:

- **Registration:** The [register](http://_vscodecontentref_/16) view in [views.py](http://_vscodecontentref_/17) handles user registration using Django's [UserCreationForm](http://_vscodecontentref_/18).
- **Login:** The [login_view](http://_vscodecontentref_/19) view in [views.py](http://_vscodecontentref_/20) handles user login using Django's [AuthenticationForm](http://_vscodecontentref_/21).
- **Logout:** The [logout_view](http://_vscodecontentref_/22) view in [views.py](http://_vscodecontentref_/23) handles user logout.

## Application Structure

- **`forum/models.py`:** Contains the database models for [Post](http://_vscodecontentref_/24), [Solution](http://_vscodecontentref_/25), and [Comment](http://_vscodecontentref_/26).
- **`forum/forms.py`:** Contains the forms for creating and editing posts, solutions, and comments.
- **`forum/views.py`:** Contains the views for handling requests and rendering templates.
- **[forum](http://_vscodecontentref_/27):** Contains the HTML templates for the application.
- **`forum/urls.py`:** Contains the URL patterns for the forum application.
- **`student_forum/settings.py`:** Contains the Django project settings.
- **`student_forum/urls.py`:** Contains the URL patterns for the project.

## Running Tests

To run the tests, use the following command:

```sh
python manage.py test
