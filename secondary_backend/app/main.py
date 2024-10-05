import subprocess
from fastapi import FastAPI
import redis.asyncio as redis
from redis import ConnectionError
import asyncio
from models.submission import Submission, StatusEnum
import json
from enum import Enum       
from fastapi.exceptions import HTTPException
import os
import shutil
import httpx


app = FastAPI()

# Redis configuration
# REDIS_URL = "redis://localhost:6379/0"
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
QUEUE_NAME = 'runQueue'

# Webhook configuration
WEB_HOOK_URL = "http://localhost:3000/api/webhook"

# Worker pool size
WORKER_POOL_SIZE = 5

redis_client = redis.Redis(host='localhost', port=6379   , db=0)

class ActionEnum(str, Enum):
    RUN = "RUN"
    SUBMIT = "SUBMIT"


def run_code_in_docker(code: str, language: str, submission_id: int, problem_id: int, test_case_paths: list, expected_output_paths: list):
    try:
        results = {
            "status": "accepted",
            "message": "All testcases passed",
            "results": ""                       
        }

        filename = f"submission_{submission_id}"
        if language == "python":
            filename += ".py"
        elif language == "cpp" or language == "c++":
            filename += ".cpp"
        else:
            results["status"] = "failed"
            results["message"] = "Unsupported programming language"
            return results

        # Create folder structure
        
        # question_dir = "/home/atharvfakatkar/contrib/online_judge/problems/"
        question_dir = os.path.join(os.getcwd(), f"../../problems/submission_{submission_id}")
        input_dir = os.path.join(question_dir, "inputs")
        output_dir = os.path.join(question_dir, "outputs")
        expected_output_dir = os.path.join(question_dir, "exp_outputs")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(expected_output_dir, exist_ok=True)

        # Save code to a file in the question directory
        with open(os.path.join(question_dir, filename), "w") as f:
            f.write(code)

        # for test_case_path in test_case_paths:
        #     print(test_case_path)

        # Copy test cases into the dedicated input directory
        for test_case_path in test_case_paths:
            subprocess.run(f"cp {test_case_path} {input_dir}", shell=True)
            
        for expected_output_path in expected_output_paths:
            subprocess.run(f"cp {expected_output_path} {expected_output_dir}", shell=True)


        # Prepare Docker command based on language  
        if language == "python":
            run_command_template = (
                f"docker run --rm --memory=256m --cpus=1 "
                f"-v {question_dir}:/app -w /app python:3.9 bash -c "
                f"\"timeout 2s python {filename} < {{input_file}} > {{output_file}} 2>&1\""
            )
            # run_command_template = (
            #     f"docker run --rm --memory=256m --cpus=1 "
            #     f"-v {question_dir}:/app -w /app python:3.9 bash -c"
            #     f"'timeout 2s python {filename} < {{input_file}} > {{output_file}} 2>&1'"
            # )
            
        elif language == "cpp" or language == "c++":
            print("Compiling the cpp code")
            # Compile C++ code
            compile_command = (
                f"docker run --rm --memory=256m --cpus=1 "
                f"-v {question_dir}:/app -w /app gcc:latest g++ -o {filename}_exec {filename}"
            )
            
            
            compile_result = subprocess.run(compile_command, shell=True, capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                compile_result["status"] = "Failed"
                compile_result["message"] = compile_result.stderr

                print("Compilation Error")

                return compile_result
            
            print("compilation successful")
            
            run_command_template = (
                f"docker run --rm --memory=256m --cpus=1 "
                f"-v {question_dir}:/app -w /app gcc:latest bash -c"
                f"'timeout 2s ./{filename}_exec < {{input_file}} > {{output_file}} 2>&1'"
            )
        
        
        
        # for test_case, expected_output_path in zip(os.listdir(input_dir),expected_output_paths):
        for number, test_case, expected_output_filename in zip(range(6), os.listdir(input_dir), os.listdir(expected_output_dir)):
            input_file = os.path.join("/app/inputs", test_case)
            output_file = os.path.join("/app/outputs", f"{test_case[0:-4]}_output.txt")
            output_val_file  = os.path.join(output_dir, f"{test_case[0:-4]}_output.txt")
            expected_output_file = os.path.join(expected_output_dir, expected_output_filename)
            
            full_command = run_command_template.format(input_file=input_file, output_file=output_file)
            
            print(f"Executing command: {full_command}")
    
            try:
                result = subprocess.run(
                    full_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=4  # Adjust timeout as needed
                )
                
                if result.returncode == 0:
                    print("Command executed successfully")

                    with open(output_val_file, "r") as f_output, open(expected_output_file, "r") as f_expected:
                        actual_output = f_output.read().strip()
                        expected_output = f_expected.read().strip()
                        # results["results"] = actual_output

                        
                        if actual_output != expected_output:
                            results["status"] = "Failed"
                            results["message"] = f"Failed on testcase {number}."
                            return results
                        

                else:
                    print(f"Command failed with return code {result.returncode}")
                    print(f"output : {result.stdout}\n message : {result.stderr}")
                    return {
                        "status": "error",
                        # "results": result.stdout,
                        "message": result.stderr
                    }
            
            except subprocess.TimeoutExpired:
                print("Command execution timed out")
                return {
                    "status": "timeout",
                    "message": "Execution took too long and was terminated"
                }
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                return {
                    "status": "exception",
                    "message": str(e)
                }
        
        return results
    except Exception as e:
        print(f"Error running code in Docker : ", e)


@app.post("/submit/")
async def execute_program(submission: Submission):
    try:
        test_case_paths = os.path.join(os.getcwd(), "..", "..", "problems", str(submission.problem_id))
        # Define the test case paths
        # print(os.getcwd())
        # test_case_paths = os.path.join(os.getcwd(), "/../../problems/", str(submission.problem_id))
        input_test_case_paths = []
        expected_output_paths = []

        for i in range(0,6):
            input_test_case_paths.append(os.path.join(test_case_paths, f"in{i}.txt"))
            # print(in)
            expected_output_paths.append(os.path.join(test_case_paths, f"out{i}.txt"))

        results = run_code_in_docker(submission.code, submission.language, submission.submission_id, submission.problem_id, input_test_case_paths, expected_output_paths)
    

        # Status management missing
        if results["status"] == "accepted":
            submission.status = StatusEnum.accepted
        
        else:
            submission.status = StatusEnum.wrong_answer
        
        submission.results = {
            "message": results["message"],
            "results": results['results'],
        }
        
        
        # Cleanup the question directory
        
        question_dir = os.path.join(os.getcwd(), "../../problems", f"submission_{submission.submission_id}")
        if os.path.exists(question_dir):
            shutil.rmtree(question_dir)

        return submission
        
    except Exception as e:
        print(f"Error executing the task : {e}")

async def send_result_to_webhook(result):
    async with httpx.AsyncClient() as client:
        response = await client.post(WEB_HOOK_URL, json =result)
    return response


async def worker(queue: asyncio.Queue):
    while True:
        task = await queue.get()
        try:
            result = await execute_program(task)
            print("Result: ", result)

            submission_result = {
                "submission_id": result.submission_id,
                "problem_id": result.problem_id,
                "user_id": result.user_id,
                "results": result.results["message"],
                "status": result.status
            }

            # payload = json.dumps(submission_result)


            await send_result_to_webhook(submission_result)
            print(f"Result sent to webhook : {submission_result}")
        except Exception as e:
            print(f"Error processing task: {e}")
        finally:
            print("Task done")
            queue.task_done()


async def process_queue_continuously(queue: asyncio.Queue):
    try:
        while True:
            try:
                print("getting item from queue")
                item = await redis_client.brpop(QUEUE_NAME, timeout=1)
                # print("received item")
                if item is None:
                    continue
                
                print("Received item from redis: ", item)           

                _, value = item
                program = Submission(**json.loads(value))
                await queue.put(program)

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")

            except Exception as e:
                print(f"Error in redis_listener: {e}")

            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print("Cancellation request received, shutting down...")
        raise


# Check the connection to Redis and start processing the queue on startup
@app.on_event("startup")
async def startup_event():
    try:
        # redis_client = await aioredis.create_redis_pool(REDIS_URL)

        # Ping the Redis server to check the connection
        if not await redis_client.ping():
            raise ConnectionError("Failed to connect to Redis")
        
        print("Successfully connected to Redis!")
        
        # Create asyncio queue
        queue = asyncio.Queue()
        print("Queue created!")
        
        # Start the listener task
        asyncio.create_task(process_queue_continuously(queue))
        print("Processing the tasks continuously")
        
        # Start the worker pool
        for _ in range(WORKER_POOL_SIZE):
            asyncio.create_task(worker(queue))
        
    except ConnectionError as e:
        print(f"Redis connection error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    if redis_client:
        await redis_client.close()
    # await asyncio.gather(*worker_tasks, return_exceptions=True)


@app.get("/")
async def root():
    return {"message": "Server is running, queue processor is active."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
