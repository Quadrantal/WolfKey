# Student Forum

This is a Django-based forum application where users can create posts, add solutions, and comment on solutions. The application supports user registration, login, and logout functionalities.

## Project Structure

## Setup Instructions

1. **Clone the repository:**

    ```sh
    git clone https://github.com/HugoC1000/School-Forum.git
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

4. **Install PostgreSQL:**

    You can install PostgreSQL using Homebrew:

    ```sh
    brew install postgresql
    #for Windows users, go to <https://www.postgresql.org/download/windows/> and download the official installer
    ```

    After installation, start the PostgreSQL service:

    ```sh
    brew services start postgresql
    ```

5. **Set up PostgreSQL:**

    Initialize the database cluster (if not already initialized):

    ```sh
    initdb /usr/local/var/postgres
    ```

    Create a new PostgreSQL user and database: 
    Note: database name and user should be all lowercase. 

    ```sh
    createuser --interactive
    createdb student_forum
    ```

    You can also set a password for the PostgreSQL user:

    ```sh
    psql
    \password <your-username>
    \q
    ```


6. **Configure Django to use PostgreSQL:**

    Update your `settings.py` file to configure the database settings:

    ```python
    # filepath: /Users/a0014208/Documents/GitHub/School-Forum/forum/settings.py
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'student_forum',
            'USER': '<your-username>',
            'PASSWORD': '<your-password>',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
    ```

7. **Apply the migrations to set up the database:**

    ```sh
    python manage.py migrate
    ```

8. **Create a superuser to access the admin interface:**

    ```sh
    python manage.py createsuperuser
    ```

9. **Run the development server:**

    ```sh
    python manage.py runserver
    ```

By following these steps, you will have PostgreSQL installed and configured for your Django application on a Mac.

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
