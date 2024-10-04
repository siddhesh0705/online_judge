import subprocess
from fastapi import FastAPI, BackgroundTasks
from redis import Redis, ConnectionError
import asyncio
from pydantic import BaseModel
from models.submission import Submission ,StatusEnum
import requests
import json
from enum import Enum
from fastapi.exceptions import HTTPException
import os
import shutil


app = FastAPI()
redis_client = Redis(host='localhost', port=6379   , db=0)



app = FastAPI()
redis_client = Redis(host='localhost', port=6379, db=0)


class ActionEnum(str, Enum):
    RUN = "RUN"
    SUBMIT = "SUBMIT"


def run_code_in_docker_combo(code: str, language: str, submission_id: int, test_case_paths: list):
    """
    Runs Python or C++ code in Docker, processing multiple input files and saving each output.
    Organizes input and output files within a single question folder.
    """
    # Define paths and filenames
    filename = f"submission_{submission_id}"
    if language == "python":
        filename += ".py"
    elif language == "cpp":
        filename += ".cpp"
    else:
        return "Unsupported language"

    # Create question-specific folder structure
    question_dir = os.path.join(os.getcwd(), f"question_{submission_id}")
    input_dir = os.path.join(question_dir, "inputs")
    output_dir = os.path.join(question_dir, "outputs")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Save code to a file in the question directory
    with open(os.path.join(question_dir, filename), "w") as f:
        f.write(code)

    # Copy test cases into the dedicated input directory
    for test_case_path in test_case_paths:
        subprocess.run(f"cp {test_case_path} {input_dir}", shell=True)

    # Prepare Docker command based on language
    if language == "python":
        docker_command = (
            f"docker run --rm --memory=256m --cpus=1 "
            f"-v {question_dir}:/app -w /app python:3.9 bash -c 'for file in /app/inputs/*; do "
            f"timeout 2s python {filename} < $file > /app/outputs/$(basename $file)_output.txt 2>&1 || echo Time Limit Exceeded > /app/outputs/$(basename $file)_output.txt; done'"
        )
    elif language == "cpp":
        # Compile C++ code
        compile_command = (
            f"docker run --rm --memory=256m --cpus=1 "
            f"-v {question_dir}:/app -w /app gcc:latest g++ -o {filename}_exec {filename}"
        )
        compile_result = subprocess.run(compile_command, shell=True, capture_output=True, text=True)
        
        if compile_result.returncode != 0:
            return f"Compilation Error: {compile_result.stderr.strip()}"

        docker_command = (
            f"docker run --rm --memory=256m --cpus=1 "
            f"-v {question_dir}:/app -w /app gcc:latest bash -c 'for file in /app/inputs/*; do "
            f"timeout 2s ./{filename}_exec < $file > /app/outputs/$(basename $file)_output.txt 2>&1 || echo Time Limit Exceeded > /app/outputs/$(basename $file)_output.txt; done'"
        )

    # Execute Docker command
    subprocess.run(docker_command, shell=True)

    # Collect output file paths and return them
    outputs = {f: os.path.join(output_dir, f) for f in os.listdir(output_dir)}
    return outputs


@app.post("/submit/")
async def execute_program(submission: Submission):
    # Define the test case paths
    test_case_paths = ["input1.txt", "input2.txt"]  # Example test case files

    # Run the code in Docker
    result = run_code_in_docker_combo(submission.code, submission.language, submission.submission_id, test_case_paths)

    # Check expected vs. actual output logic here (pseudo-code example)
    # Let's assume you load expected output from files and compare
    expected_output_paths = ["expected1.txt", "expected2.txt"]  # Define paths to expected outputs
    is_correct = True  # A placeholder for actual comparison logic

    for output_file, expected_path in zip(result.values(), expected_output_paths):
        with open(output_file) as f_output, open(expected_path) as f_expected:
            if f_output.read().strip() != f_expected.read().strip():
                is_correct = False
                break

    # Set status based on comparison result
    if is_correct:
        submission.status = StatusEnum.accepted
        submission.results = result
    else:
        submission.status = StatusEnum.wrong_answer
        submission.results = result

    # Cleanup the question directory
    question_dir = os.path.join(os.getcwd(), f"question_{submission.submission_id}")
    if os.path.exists(question_dir):
        shutil.rmtree(question_dir)

    return submission

async def process_single_queue_item():
    # Try to get an item from the Redis queue
    item = redis_client.lpop('runQueue')
    print("Item fetched from queue: ", item)

    if item is None:
        # No item in the queue
        return {"status": "No items in queue"}

    try:
        program = Submission(**json.loads(item))

        # Execute the program
        result = await execute_program(program)
        print("Program executed with result: ", result)

        # Send the result back to the primary backend via webhook
        # Uncomment and configure the webhook URL when ready
        # response = requests.post(os.environ['PRIMARY_BACKEND_WEBHOOK'], json=result)

        return {
            "status": "Processed",
            "execution_result": result,
        }
    except Exception as e:
        # Handle any errors that occur during processing
        return {"status": "Error", "message": str(e)}


async def process_queue_continuously():
    while True:
        result = await process_single_queue_item()
        if result["status"] == "No items in queue":
            # If no items in queue, sleep for a short time before checking again
            await asyncio.sleep(1)
        else:
            print(result)
            # Simulate some processing time
            await asyncio.sleep(0.5)


# Check the connection to Redis and start processing the queue on startup
@app.on_event("startup")
async def startup_event():
    try:
        # Ping the Redis server to check the connection
        response = redis_client.ping()
        if response:
            print("Successfully connected to Redis!")
            # If connection successful, start the queue processor
            asyncio.create_task(process_queue_continuously())
        else:
            print("Failed to connect to Redis.")
    except ConnectionError as e:
        print(f"Redis connection error: {e}")


@app.get("/")
async def root():
    return {"message": "Server is running, queue processor is active."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
