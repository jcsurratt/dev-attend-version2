# Dev Attend Technology Stack

## Purpose Of This Document

This file explains the main technologies used in Dev Attend and what each one is used for.

The goal is to make the tech stack easy to understand, even if you are new to programming.

## Main Tech Stack

This project is mainly built with:

- Python
- FastAPI
- PostgreSQL
- HTML
- CSS
- JavaScript
- PyTorch
- facenet-pytorch

## Backend Technologies

### Python

Python is the main programming language used on the backend.

It is used for:

- starting the web application
- connecting to the database
- handling API requests
- running the face recognition logic

Why it is used:

- Python is readable
- Python is common in web development
- Python is also very common in AI and machine learning projects

### FastAPI

FastAPI is the backend web framework.

A web framework helps build the server-side part of a web application.

FastAPI is used for:

- creating web routes like `/teacher` and `/api/students`
- returning HTML pages
- returning JSON API responses
- handling form uploads such as image files

Why it is used:

- it is modern and fast
- it works well with Python type hints
- it makes API development clean and organized

### Uvicorn

Uvicorn is the server that runs the FastAPI app.

It is used for:

- starting the backend
- serving the application locally during development

You can think of it as the engine that keeps the FastAPI app running.

### python-dotenv

`python-dotenv` helps the app read values from the `.env` file.

It is used for:

- loading database settings
- keeping sensitive values out of the source code

Why it matters:

- passwords and connection settings should not be hardcoded in normal source files

### python-multipart

`python-multipart` helps FastAPI handle uploaded form data.

It is used for:

- receiving uploaded images from the browser

This matters because the camera and registration workflow send image files to the backend.

## Database Technologies

### PostgreSQL

PostgreSQL is the main database used by the app.

A database stores structured information.

In this project, PostgreSQL is used for:

- student roster data
- student lookups
- attendance-related data

Why it is used:

- it is reliable
- it is powerful
- it is a standard database used in many real-world applications

### psycopg2-binary

`psycopg2-binary` is the Python package that lets Python talk to PostgreSQL.

It is used for:

- opening database connections
- running SQL queries
- reading and writing student records

Without it, the Python backend would not be able to communicate with PostgreSQL.

## Frontend Technologies

### HTML

HTML builds the structure of the web pages.

It is used for:

- page layout
- headings
- buttons
- forms
- containers for the camera view and roster view

HTML gives the app its basic page structure.

### CSS

CSS controls how the app looks.

It is used for:

- colors
- spacing
- fonts
- page layout styling

CSS makes the app look like a real interface instead of plain text on a page.

### JavaScript

JavaScript makes the pages interactive.

It is used for:

- calling backend API routes
- updating page content without reloading everything
- handling button clicks
- working with the camera page

Examples in this project include:

- adding students
- looking up student information
- sending camera frames to the backend

## Face Recognition And AI Technologies

### PyTorch

PyTorch is the main machine learning library used by the app.

It is used for:

- running the face recognition models
- working with tensors, which are data structures used in AI

Why it is used:

- it is one of the most common AI libraries in Python
- many computer vision tools are built on top of it

### torchvision

`torchvision` is a helper library that works with PyTorch.

It is used for:

- supporting image-related machine learning tasks
- providing tools that work well with vision models

It is part of the computer vision side of the project.

### facenet-pytorch

`facenet-pytorch` is the main face recognition package used in this app.

It provides prebuilt face-related models.

In this project, it is used for:

- detecting faces in images
- turning faces into embeddings
- comparing one face to another

An embedding is a numeric representation of a face that the computer can compare.

### Pillow

Pillow is a Python image library.

It is used for:

- opening uploaded image files
- converting images into a format the face-recognition pipeline can use

### NumPy

NumPy is a library for working with numerical data.

It is commonly used in AI, image processing, and scientific programming.

In this project, it supports the image and machine learning ecosystem used by PyTorch and face-recognition tools.

## File-Based Face Storage

### Pickle

The app currently stores face embeddings in a file instead of in PostgreSQL.

Python uses `pickle` for that.

It is used for:

- saving face embedding data to disk
- loading it again later

This is handled in the face storage service.

## Development Environment Technologies

### venv

`venv` is Python’s built-in virtual environment system.

It is used for:

- creating a project-specific Python environment
- keeping this project’s packages separate from other Python projects on the same machine

Why it matters:

- different projects often need different package versions
- a virtual environment helps avoid package conflicts

### requirements.txt

`requirements.txt` is the file that lists the Python packages needed by the project.

It is used for:

- installing the app’s dependencies with `pip`

### .env

The `.env` file stores local configuration values.

It is used for:

- database connection settings
- optional app settings such as the face database file path

## How These Technologies Work Together

Here is the simple flow:

1. Python runs the project.
2. FastAPI provides the backend routes.
3. Uvicorn serves the backend app.
4. HTML, CSS, and JavaScript build the user interface.
5. PostgreSQL stores student and attendance data.
6. `psycopg2-binary` connects Python to PostgreSQL.
7. PyTorch and `facenet-pytorch` handle face recognition.
8. `python-dotenv` reads settings from `.env`.
9. `venv` keeps all required Python packages organized for this project.

## Simple Summary

If you want a very short version:

- Python = main programming language
- FastAPI = backend framework
- Uvicorn = server that runs the app
- PostgreSQL = database
- psycopg2-binary = PostgreSQL connector for Python
- HTML/CSS/JavaScript = frontend pages
- PyTorch = AI library
- facenet-pytorch = face recognition tools
- Pillow = image handling
- python-dotenv = reads `.env`
- venv = project-specific Python environment

## Final Note

This app combines normal web-development tools and AI tools.

That is why the stack includes both:

- standard web technologies like FastAPI, PostgreSQL, HTML, CSS, and JavaScript
- machine learning technologies like PyTorch and face-recognition libraries

Together, they allow the app to act like both:

- a normal student attendance system
- a camera-based face recognition system
