from fastapi import FastAPI, BackgroundTasks
# from redis import Redis, ConnectionError
import redis.asyncio as redis
from redis import ConnectionError
import asyncio
from models.submission import Submission
import requests
import json
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


# Redis client

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
# redis_client = Redis(host='localhost', port=6379   , db=0)
  

async def execute_program(program: Submission):
    # Simulate program execution
    await asyncio.sleep(10)
    return {
        "submission_id": program.submission_id,
        "problem_id": program.problem_id,
        "user_id": program.user_id,
        "results": program.results,
        "status": "wrong answer"
    }

async def send_result_to_webhook(result):
    async with httpx.AsyncClient() as client:
        response = await client.post(WEB_HOOK_URL, json=result)
    return response


async def worker(queue: asyncio.Queue):
    while True:
        task = await queue.get()
        try:
            result = await execute_program(task)
            print("Result: ", result)
            
            await send_result_to_webhook(result)
            print("Result sent to webhook")
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
                

    
@app.on_event("startup")
async def startup_event():
    try:
        # redis_client = await aioredis.create_redis_pool(REDIS_URL)

        # Ping the Redis server to check the connection
        if not redis_client.ping():
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

@app.get("/")
async def root():
    return {"message": "Server is running, queue processor is active."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)