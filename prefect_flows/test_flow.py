from prefect import flow, task
import time

@task
def say_hello(name: str):
    print(f"Hello, {name}!")
    return f"Hello, {name}!"

@task
def say_goodbye(name: str):
    print(f"Goodbye, {name}!")
    return f"Goodbye, {name}!"

@flow
def hello_world_flow(name: str = "Prefect"):
    # Task 실행
    greeting = say_hello(name)
    time.sleep(2)
    farewell = say_goodbye(name)
    
    return greeting, farewell

if __name__ == "__main__":
    # 로컬에서 직접 실행
    hello_world_flow(name="LawDigest User")
