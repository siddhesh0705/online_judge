from fastapi import FastAPI, BackgroundTasks
from redis import Redis, ConnectionError
import asyncio
from pydantic import BaseModel
from models.submission import Submission
import requests
import json


app = FastAPI()
redis_client = Redis(host='localhost', port=6379   , db=0)

async def execute_program(program: Submission):
    # Simulate program execution
    await asyncio.sleep(5)
    return {
        "submission_id": program.submission_id,
        "problem_id": program.problem_id,
        "user_id": program.user_id,
        "results": program.results,
        "status": "wrong answer"
    }



async def process_single_queue_item():
    # Try to get an item from the Redis queue
    
    item = redis_client.lpop('runQueue')
    print("Item fetched from queue: ", item)
    
    if item is None:
        # No item in the queue
        return {"status": "No items in queue"}
    
    try:
        print("before")
        program = Submission(**json.loads(item))
        print("after")

        # Execute the program
        result = await execute_program(program)
        print("Program executed with result: ", result)

        # Send the result back to the primary backend via webhook
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
            # result = await process_single_queue_item()
            print(result)
            # Simulate some processing time
            await asyncio.sleep(0.5)

    
#check the connection to Redis
@app.on_event("startup")
async def startup_event():
    try:
        # Ping the Redis server to check the connection
        response =  redis_client.ping()
        if response:
            print("Successfully connected to Redis!")
            #if connection successful, start the queue processor
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



# @app.get("/process_queue")
# async def process_queue():
#     results = []

#     while True:
#         result = await process_single_queue_item()
#         results.append(result)
#         if result["status"] == "No items in queue":
#             break
#     return results




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)