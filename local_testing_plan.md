# Local Testing Plan for IG Live Host Ready Worker

This document outlines the plan for setting up a local testing environment for the `ig live(host ready)` worker.

## 1. Environment Setup

*   Create a Python virtual environment to isolate dependencies.
*   Install all dependencies from `worker/requirements.txt` into the virtual environment.
*   The existing `.env` file will be used for configuration. We need to ensure the database is accessible and the bot tokens are valid for testing.

## 2. Local Execution

*   Create a new python script `run_local_test.py` in the `ig live(host ready)` directory.
*   This script will:
    *   Load the environment variables from the `.env` file.
    *   Import and run the main function from `worker/main.py`.
    *   It should be possible to pass arguments to this script to simulate different scenarios.

## 3. Test Cases

*   **Test Case 1: Basic Startup:**
    *   **Objective:** Verify that the worker can start up correctly without errors.
    *   **Procedure:** Run `run_local_test.py`.
    *   **Expected Result:** The worker starts, connects to the database and Telegram, and logs a "ready" message.

*   **Test Case 2: Simulate a Job:**
    *   **Objective:** Verify that the worker can process a job.
    *   **Procedure:** I will inspect `create_test_job.py` to see how to create a job. The `run_local_test.py` will be modified to trigger a test job.
    *   **Expected Result:** The worker picks up the job, processes it, and updates the database accordingly. Logs should show the job being processed.

## 4. Debugging

*   The `run_local_test.py` script will be the entry point for debugging.
*   We can add breakpoints in the worker code to inspect the state at different points.