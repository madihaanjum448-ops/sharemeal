from fastapi import FastAPI

app = FastAPI(title="ShareMeal - Member 2")

@app.get("/health")
def health():
    return {"status": "ok"}
