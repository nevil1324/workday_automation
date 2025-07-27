# Workday Application Scraper

This project contains a robust Playwright-based Python script designed to automate logging into Workday, traversing job application forms, uploading a resume, filling in form fields with arbitrary data, and extracting a structured JSON map of all processed fields. The script is modularized for better maintainability and readability.

---

## Features

* **Automated Login**: Logs into your Workday tenant using provided credentials.
* **Resume Upload**: Detects and handles resume upload sections, attaching a specified file.
* **Form Field Filling**: Intelligently identifies various form field types (text, textarea, date, checkbox, radio, dropdown, multiselect) and fills them with arbitrary, valid-looking data.
* **Data Extraction**: Extracts details for each form field, including its label, automation ID, required status, input type, available options (for select fields), and the values used for filling.
* **Application Traversal**: Navigates through multiple pages of the application process.
* **Structured Output**: Generates a JSON file (`workday_form_map.json`) containing all extracted form field data.
* **Error Handling & Screenshots**: Captures screenshots on successful login, final page, and any errors encountered.

---

## Project Structure

The project is divided into several modular files for clarity and organization:

* **`main.py`**: The main entry point of the application. It orchestrates the flow, initializes Playwright, calls the login function, and then starts the scraping process.
* **`config.py`**: Handles configuration variables, constants (like "Next" button selectors), and loads environment variables.
* **`auth.py`**: Contains the `login_to_workday` function responsible for handling the Workday login process.
* **`utils.py`**: Provides utility functions such as `arbitrary_user_data` (for generating test data), `handle_resume_upload`, `close_all_popups`, and `wait_for_popup`.
* **`scraper.py`**: Contains the core logic for traversing application pages, extracting form fields, and filling them.

---

## Setup and Installation

### Prerequisites

* Python 3.8+
* `pip` (Python package installer)

### Steps

1.  **Clone the Repository (or create files manually):**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright Browsers:**
    After installing the Python package, you need to install the browser binaries:
    ```bash
    playwright install
    ```

5.  **Create a `.env` file:**
    In the root directory of your project, create a file named `.env` and add your Workday credentials, tenant URL, and resume path:

    ```
    WORKDAY_EMAIL="your_email@example.com"
    WORKDAY_PASSWORD="your_workday_password"
    WORKDAY_URL="https://your_[company.workday.com/login.htm](https://company.workday.com/login.htm)" # Or the direct application URL
    RESUME_PATH="/path/to/your/resume.pdf" # e.g., C:\Users\YourUser\Documents\resume.pdf or /home/youruser/Documents/resume.pdf
    ```
    **Ensure the `RESUME_PATH` points to an actual PDF file on your system.**

---

## Usage

To run the scraper, simply execute the `main.py` script:

```bash
python main.py