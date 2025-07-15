import uasyncio as asyncio

# Create a lock object for shared printing
print_lock = asyncio.Lock() 

# Create an event object for task synchronization
# Lets Task A Notify Task B When It's Done
event = asyncio.Event()

# A task that prints a message every `delay_ms`
async def print_task(name, delay_ms, max_count=5):    # async def: defines an asynchronous coroutine.
    for i in range(max_count):
        async with print_lock:  # Only one task can print at a time...  # async with print_lock: ensures exclusive access to printing.
            print(f"[{name}] Count: {i}")
        await asyncio.sleep_ms(delay_ms)  # await asyncio.sleep_ms: async sleep in milliseconds.

    # After finishing, signal the event if it's Task A
    if name == "Task A":
        print(f"[{name}] Setting event to notify Task B.")
        event.set()

# A task that waits for an event
async def event_waiting_task():
    print("[Task B] Waiting for event from Task A...")
    # Pauses here until event is set 
    await event.wait()       # event.wait() suspends execution until event.set() is called.
    print("[Task B] Got event! Continuing...")

# A task demonstrating wait_for_ms with timeout
async def limited_task():
    print("[Task C] Starting and will timeout if not done in 1s")
    try:
        # Simulate a long wait, but wrap with timeout
        await asyncio.wait_for_ms(asyncio.sleep(2), 1000)
        print("[Task C] Completed within timeout")
    except asyncio.TimeoutError:
        print("[Task C] Timeout occurred!")

# A forever-running task (optional for demonstration)
async def forever_task():
    count = 0
    while True:
        async with print_lock:
            print(f"[Forever Task] Heartbeat {count}")
        count += 1
        await asyncio.sleep(1)

# Main coroutine
async def main():
    print("Main: Starting all tasks...\n")

    # Creating different types of tasks
    asyncio.create_task(print_task("Task A", 400))
    asyncio.create_task(event_waiting_task())
    asyncio.create_task(print_task("Task B", 1000, max_count=3))
    asyncio.create_task(limited_task())
    asyncio.create_task(forever_task())  # optional, runs forever

    # Let tasks run for 8 seconds
    await asyncio.sleep(8)

    print("\nMain: Done. Stopping.")

# Start the asyncio event loop
asyncio.run(main())
