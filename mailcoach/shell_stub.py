#!/usr/bin/env python3
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import uvicorn
import argparse

app = FastAPI()

class CommandRequest(BaseModel):
    command: str
    stdin: str | None = None

class CommandResponse(BaseModel):
    returncode: int
    stdout: str
    stderr: str

@app.post("/api/run")
async def run_command(request: CommandRequest) -> CommandResponse:
    try:
        # Run the command
        process = subprocess.Popen(
            request.command,
            stdin=subprocess.PIPE if request.stdin else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Handle text instead of bytes
            shell=True
        )
        
        # Send stdin if provided
        stdout, stderr = process.communicate(input=request.stdin)
        
        return CommandResponse(
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8642)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)

if __name__ == "__main__":
    main()
