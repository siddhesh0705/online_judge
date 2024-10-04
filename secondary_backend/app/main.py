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

app = FastAPI()
redis_client = Redis(host='localhost', port=6379   , db=0)



app = FastAPI()
redis_client = Redis(host='localhost', port=6379, db=0)


class ActionEnum(str, Enum):
    RUN = "RUN"
    SUBMIT = "SUBMIT"


def run_code_in_docker(code: str, language: str, submission_id: int) -> str:
    """
    Runs the code inside a Docker container with a time limit using subprocess timeout.
    """
    # Define the filename based on the submission ID and language
    filename = f"submission_{submission_id}"
    if language == "python":
        filename += ".py"
    elif language == "cpp":
        filename += ".cpp"
    else:
        return "Unsupported language"

    # Save the code to a file in the current directory
    with open(filename, "w") as f:
        f.write(code)

    # Get the absolute path of the current working directory
    host_path = os.getcwd()

    # Set a time limit for code execution
    time_limit = 2

    # Prepare Docker commands based on the language
    docker_command = ""
    if language == "python":
        docker_command = (
            f"docker run --rm --memory=256m --cpus=1 "
            f"-v {host_path}:/app -w /app python:3.9 python {filename}"
        )
    elif language == "cpp":
        compile_command = (
            f"docker run --rm --memory=256m --cpus=1 "
            f"-v {host_path}:/app -w /app gcc:latest g++ -o {filename}_exec {filename}"
        )
        run_command = (
            f"docker run --rm --memory=256m --cpus=1 "
            f"-v {host_path}:/app -w /app gcc:latest ./{filename}_exec"
        )
        docker_command = f"{compile_command} && {run_command}"

    try:
        # Run the Docker command with a timeout
        result = subprocess.run(docker_command, shell=True, capture_output=True, text=True, timeout=time_limit)

        # Return stdout if successful, otherwise return stderr with the error
        return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        # Kill the Docker container if it exceeds the time limit
        subprocess.run(f"docker ps -q --filter ancestor=python:3.9 | xargs -r docker kill", shell=True)

        return f"Error: Time Limit Exceeded ({time_limit} seconds)"

    finally:
        # Clean up the code file after execution
        if os.path.exists(filename):
            os.remove(filename)
        # Clean up compiled files in case of C++
        if language == "cpp" and os.path.exists(f"{filename}_exec"):
            os.remove(f"{filename}_exec")


@app.post("/submit/")
async def submit_code(submission: Submission):
    """
    API endpoint to submit and run code inside a Docker container.
    """
    # Run the code in Docker
    result = run_code_in_docker(submission.code, submission.language, submission.submission_id)

    # Set the status based on the result
    if "Error: Time Limit Exceeded" in result:
        submission.status = StatusEnum.time_limit_exceeded
    elif "Error" in result:
        submission.status = StatusEnum.runtime_error
    else:
        submission.status = StatusEnum.accepted
        submission.results = result

    return submission


async def execute_program(program: Submission):
    # Execute the program and set the submission_id
    result = run_code_in_docker(program.code, program.language, program.submission_id)

    if "Error" in result:
        program.status = StatusEnum.runtime_error
    else:
        program.status = StatusEnum.accepted
        program.results = result
    return program


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
