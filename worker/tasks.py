import os
import json
import subprocess
import httpx
from celery import Celery, shared_task
from celery.schedules import timedelta
from redis import Redis
from dotenv import load_dotenv
import base64
import re

load_dotenv(".env")
# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
RUN_QUEUE = os.getenv('RUN_QUEUE', 'runQueue')
SUBMIT_QUEUE = os.getenv('SUBMIT_QUEUE', 'submitQueue')

# Webhook configuration
WEB_HOOK_URL = os.getenv('WEB_HOOK_URL', "http://localhost:3000/api/webhook")

# Celery configuration
app = Celery('tasks', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}')
app.conf.broker_url = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
app.conf.result_backend = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

app.conf.broker_connection_retry_on_startup = True

# Redis client
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def run_code_in_docker(code, language, submission_id, problem_id, test_case_paths, expected_output_paths):
    try:
        results = {
            "status": "accepted",
            "message": "All testcases passed",
            "results": ""
        }

        filename = f"submission_{submission_id}"
        if language == "python":
            filename += ".py"
            image = "python:3.9-slim"
            run_cmd = f"python {filename}"
            timeout = 4
        elif language in ["cpp", "c++"]:
            filename += ".cpp"
            image = "gcc:latest"
            compile_cmd = f"g++ -o {filename}_exec {filename}"
            run_cmd = f"./{filename}_exec"
            timeout = 2
        elif language == "java":
            filename = "Main.java"
            image = "openjdk:11-jdk-slim"
            compile_cmd = f"javac {filename}"
            run_cmd = f"java {filename[:-5]}"
            timeout = 2
        elif language == "javascript":
            filename += ".js"
            image = "node:14-slim"
            run_cmd = f"node {filename}"
            timeout = 4
        else:
            return {"status": "failed", "message": "Unsupported programming language"}

        work_dir = os.path.join(os.getcwd(), "..", "problems", f"submission_{submission_id}")
        output_dir = os.path.join(work_dir, "outputs")
        input_dir = os.path.join(work_dir, "inputs")
        expected_output_dir = os.path.join(work_dir, "exp_outputs")
        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(expected_output_dir, exist_ok=True)
        
        with open(os.path.join(work_dir, filename), "w") as f:
            f.write(code)

        for i, (test_case, expected_output) in enumerate(zip(test_case_paths, expected_output_paths)):
            subprocess.run(f"cp {test_case} {os.path.join(input_dir, f'in{i}.txt')}", shell=True)
            subprocess.run(f"cp {expected_output} {os.path.join(expected_output_dir, f'out{i}.txt')}", shell=True)

        if language in ["cpp", "c++", "java"]:
            compile_result = subprocess.run(
                f"docker run --rm -v {work_dir}:/app -w /app {image} {compile_cmd}",
                shell=True, capture_output=True, text=True
            )
            if compile_result.returncode != 0:
                error_message = compile_result.stderr
                error_lines = error_message.split('\n')
                relevant_errors = [line for line in error_lines if re.search(r'error|warning', line)]
                formatted_error = '\n'.join(relevant_errors)
                return {
                    "status": "compilation_error",
                    "message": f"Compilation failed.",
                    "results": f"{formatted_error}"
                }
        final_correct_result = ""
        for i in range(len(test_case_paths)):
            run_result = subprocess.run(
                f"docker run --rm --memory=256m --cpus=1 -v {work_dir}:/app -w /app {image} "
                f"sh -c 'timeout {timeout}s {run_cmd} < inputs/in{i}.txt | tee outputs/output_{i}.txt'",
                shell=True, capture_output=True, text=True
            )

            if run_result.returncode == 124:
                return {
                    "status": "time_limit_exceeded",
                    "message": f"Execution time exceeded {timeout} seconds on testcase {i}."
                }
            elif run_result.returncode != 0:
                error_message = run_result.stderr
                if "Segmentation fault" in error_message:
                    return {
                        "status": "runtime_error",
                        "message": f"Segmentation fault occurred on testcase {i}. This typically indicates accessing memory that does not belong to your program."
                    }
                elif "std::bad_alloc" in error_message:
                    return {
                        "status": "runtime_error",
                        "message": f"Memory allocation failed on testcase {i}. This usually means your program is trying to use more memory than available."
                    }
                elif language == "javascript" and "RangeError: Maximum call stack size exceeded" in error_message:
                    return {
                        "status": "runtime_error",
                        "message": f"Stack overflow error occurred on testcase {i}. This usually indicates infinite recursion or excessive function calls."
                    }
                else:
                    error_lines = error_message.split('\n')
                    relevant_error = '\n'.join(error_lines[-5:])
                    return {
                        "status": "runtime_error",
                        "message": f"Runtime error occurred on testcase {i}",
                    }

            with open(os.path.join(output_dir, f"output_{i}.txt"), "r") as f_output, \
                 open(os.path.join(expected_output_dir, f"out{i}.txt"), "r") as f_expected:
                if f_output.read().strip() != f_expected.read().strip():
                    return {"status": "wrong_answer", "message": f"Failed on testcase {i}.", "results": run_result.stdout}

            final_correct_result = run_result.stdout

        results['results'] = final_correct_result
        return results
    except Exception as e:
        print("Error in running in docker", e)
        return {"status": "pending", "message": "Unexpected error occurred", "results": str(e)}
    finally:
        if os.path.exists(work_dir):
            subprocess.run(f"rm -rf {work_dir}", shell=True)

@app.task
def execute_program_submit(submission):
    try:
        test_case_paths = [f"../problems/{submission['problem_id']}/in{i}.txt" for i in range(6)]
        expected_output_paths = [f"../problems/{submission['problem_id']}/out{i}.txt" for i in range(6)]

        results = run_code_in_docker(
            submission['code'],
            submission['language'],
            submission['submission_id'],
            submission['problem_id'],
            test_case_paths,
            expected_output_paths
        )

        # print(f"Program ran in Docker successfully with result : {results}")

        submission['status'] = results['status']
        submission['message'] = results['message']
        submission['results'] = ''

        return submission
    except Exception as e:
        print(f"Error executing the task: {e}")
        return None


@app.task
def execute_program_run(submission):
    try:
        test_case_paths = [f"../problems/{submission['problem_id']}/in0.txt"]
        expected_output_paths = [f"../problems/{submission['problem_id']}/out0.txt"]

        results = run_code_in_docker(
            submission['code'],
            submission['language'],
            submission['submission_id'],
            submission['problem_id'],
            test_case_paths,
            expected_output_paths
        )

        # print(f"Program ran in Docker successfully with result : {results}")

        submission['status'] = results['status']
        submission['message'] = results['message']
        submission['results'] = results['results']

        return submission
    except Exception as e:
        print(f"Error executing the task: {e}")
        return None


@shared_task
def send_result_to_webhook(result):
    try:
        print(WEB_HOOK_URL)
        response = httpx.post(WEB_HOOK_URL, json=result)
        response.raise_for_status()
        print(f"Result sent to webhook: {result}")
    except httpx.HTTPError as e:
        print(f"Error sending result to webhook: {e}")
    except Exception as e:
        print(f"DONT KNOW WHAT ERROR: {e}")


@app.task
def process_queue(queue_name = SUBMIT_QUEUE):
    try:
        item = redis_client.brpop(queue_name, timeout=1)
        
        if item is None:
            print(f"Queue {queue_name} is empty, waiting for new submissions...")
            return
        
        print(f"Item received from {queue_name}, {item}")

        _, value = item
        submission = json.loads(value)

        # Decode from base64
        decoded_bytes = base64.b64decode(submission['code'])
        # Convert bytes to string
        submission['code'] = decoded_bytes.decode('utf-8')

        if queue_name == 'submitQueue':
            result = execute_program_submit(submission)
        else:
            result = execute_program_run(submission)

        print(f"Program executed successfully with result : {result}")
        
        if result:
            submission_result = {
                "submission_id": result['submission_id'],
                "problem_id": result['problem_id'],
                "user_id": result['user_id'],
                "results": result['results'],
                "message": result['message'],
                "status": result['status']
            }
            
            send_result_to_webhook(submission_result)
        else:
            print("Error sending execution result to primary backend via webhook")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Error in process_queue: {e}")

app.conf.beat_schedule = {
    'process-run-queue': {
        'task': 'tasks.process_queue',
        'schedule': timedelta(seconds=1),
        'args': (RUN_QUEUE,)
    },
    'process-submit-queue': {
        'task': 'tasks.process_queue',
        'schedule': timedelta(seconds=1),
        'args': ('submitQueue',)
    }
}

if __name__ == "__main__":
    app.start()