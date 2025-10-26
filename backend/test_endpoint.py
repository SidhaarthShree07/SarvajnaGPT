from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

class VSCodeOpenRequest(BaseModel):
    abs_path: str = Field(..., description="Absolute path to a file to open in VS Code")
    split_screen: bool = Field(True, description="Place VS Code and current foreground window side-by-side")
    code_side: str = Field('right', description="'left' or 'right'")

@app.post("/api/automation/vscode/open_existing")
def vscode_open_existing(req: VSCodeOpenRequest):
    print(f"Opening file in VS Code: {req.abs_path}")
    return {"opened": True, "path": req.abs_path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)