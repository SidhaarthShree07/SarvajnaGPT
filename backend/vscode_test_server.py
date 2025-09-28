from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
import sys

app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define our test VSCodeOpenRequest class
from pydantic import BaseModel, Field

class VSCodeOpenRequest(BaseModel):
    abs_path: str = Field(..., description="Absolute path to a file to open in VS Code")
    split_screen: bool = Field(True, description="Place VS Code and current foreground window side-by-side")
    code_side: str = Field('right', description="'left' or 'right'")
    fallback_snap: bool = Field(True, description="If pairing fails, snap VS Code to requested side anyway")
    use_os_snap_keys: bool = Field(True, description="Use OS snap keys for window arrangement")
    use_cua_for_selection: bool = Field(True, description="Use CUA for window selection")
    arrangement_delay_ms: int = Field(1000, description="Delay for window arrangement")

@app.post("/api/automation/vscode/open_existing")
def vscode_open_existing(req: VSCodeOpenRequest):
    print(f"Opening file in VS Code: {req.abs_path}")
    print(f"Split screen: {req.split_screen}, Side: {req.code_side}")
    print(f"Full request: {req}")
    
    # Check if file exists
    if os.path.isfile(req.abs_path):
        print(f"File exists: {req.abs_path}")
        return {"opened": True, "path": req.abs_path, "snapped": True}
    else:
        print(f"File does not exist: {req.abs_path}")
        return {"opened": False, "error": f"File not found: {req.abs_path}"}

if __name__ == "__main__":
    port = 8002
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="127.0.0.1", port=port)