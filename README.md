# Sbily

[![license mit](https://img.shields.io/badge/licence-MIT-blue)](/LICENSE)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/format.json)](https://github.com/astral-sh/ruff)

A Django project for a link shortener.

## Technologies Used

- [Python](https://www.python.org/)
- [Django](https://www.djangoproject.com/)
- [Rspack](https://rspack.dev/)
- [TailwindCSS](https://tailwindcss.com/)
- [Docker](https://www.docker.com/)

## How to Execute the Project

To run the project, you need to have [Python](https://www.python.org/) and [Node](https://nodejs.org/) (to run Rspack) installed on your machine, or you can use [Docker](#with-docker).

### Without Docker

Once the repository is cloned and the global dependencies are installed, you can install the project's local dependencies.

#### 1. Install Local Dependencies

Python dependencies:

```bash
uv sync
```

Node dependencies:

```bash
pnpm install
```

#### 2. Configure environment variables

Copy the `.envs.example` directory to the `.envs` directory _(which will be ignored by Git)_:

```bash
cp -r .envs.example .envs
```

#### 3. Make the migrations

```bash
uv run python manage.py migrate
```

#### 4. Create a super user

```bash
uv run python manage.py createsuperuser
```

#### 5. Running application in development mode

Django application:

```bash
uv run python manage.py runserver
```

Rspack:

```bash
pnpm run dev
```

The Python command will start the Django application at <http://localhost:8000> and Node will start Rspack and a proxy server for automatic reloading at <http://localhost:3000>.

- Open <http://localhost:3000> to see the application.
- In the administrative area, enter the username and password created in [step 4](#4-create-a-super-user).

### With Docker

Once the repository is cloned, the global dependencies are installed and [variables defined](#2-configure-environment-variables), let's start the container:

```bash
docker compose -f docker-compose.local.yml up
```

When started, the container starts the Django application!

> **_The steps below will only be necessary if you have not yet carried out the migrations and created a super user! If you have already done so, the application can be accessed at: <http://localhost:3000>_**

You will need to enter the container via CLI:

```bash
docker compose -f docker-compose.local.yml up exec django zsh
```

> Now you are inside the container!

You will need to make the migrations:

```bash
uv run python manage.py migrate
```

Creating a super user:

```bash
uv run python manage.py createsuperuser
```

The Python command will start the Django application at <http://localhost:8000> and Node will start Rspack and a proxy server for automatic loading at <http://localhost:3000>.

- Open <http://localhost:3000> to see the application.

## License

This project is under the [MIT license](/LICENSE).

🔝[Back to top](#sbily)
