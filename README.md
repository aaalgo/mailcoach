Mailcoach
=========

Wei Dong

wdong@aaalgo.com

# Introduction

Mailcoach is the self-contained single-user version of [Postline](https://arxiv.org/abs/2502.09903).  Mailcoach realizes the AI agent architecture by:

- Using email as the (conceptual) communication protocol.
- Extending the standard chat paradigm into multi-party chat.
- Allowing robots (commonly referred to as tools) to connect into the chat.

# Setup

Method 1. Direct install from github.
```
pip3 install git+https://github.com/aaalgo/mailcoach.git
```

Method 2. Setup Local Development Environment

This method allows you to make change to the source code after installation.  Your change will be immediately reflected without reinstallation.

```
git clone https://github.com/aaalgo/mailcoach
cd mailcoach
pip3 install -e .
```

Set up your enviroment variables so the API keys of the model endpoints are available (OPENAI_API_KEY, ANTHROPID_API_KEY, ...).

# Quickstart

## Chat with Agents

```
mailcoach
```

The full command is

```
mailcoach [-m path_to_memory] [-t path_to_trace] [-u user_address] [--debug]
```

- If a memory file/directory is not specified, a default sample is loaded.
- If a trace path is not specified, the trace is written to `mailcoach.YYYYMMDDHHMMSS` under the current directory.
- If the user address is specified, use this address to represent the user. 
- If --debug is specified, ask for confirmation before each AI generation.

The memory can be a single file (for compatibility) or a directory of
mailboxes, one for each agent.

The trace is a directory of the same format as memory and saves the
global trace as well as the memory of each agent.

You can load the trace with `-m` to continue an existing session.

Note that the per-agent memory is only saved when you normally exit a session.  If it is a chat session, you can end with Ctrl+D.  If the program crashes or if you kill it, you won't have the per-agent mbox; but there would still be a trace file which you can load with -m to recover your data.

You can import the mbox files into almost any email clients, e.g. claws-mail.

## Task Automation

In addition to the parameters described above, mailcoach can run with a queue file for automation.  When a queue file is provided, you won't see the interactive chat interface unless you add `-c,--chat`.

Prepare a text file called `queue.mbox` using the following content:

```
From ----
From: user@localdomain
To: swe1@localdomain
X-Hint-Model: openai/gpt-4o-mini

Generate a fortune using command line.
```

Then run

```
mailcoach -q queue.mbox [--budget 0.05]
```

Mailcoach will run in non-interactive mode until all messages to AI agents are processed.  The messages to the user will not be processed.  If your queue file involves a multi-agent conversation, make sure you set a budget so the conversation doesn't go one forever.

## Auto Pilot

In the auto pilot mode, the AI will play the user's role as well, so conversation will keep on until the budget is reached.  In auto pilot mode the budget is mandatory.

```
mailcoach -m queue.mbox --auto --budget 0.001  # Use at most 5 cents.
```

**Warning:** The agent has access to the shell and currently it's not restricted. Please keep an eye on its activity. 

# The Default Memory

(You are encouraged to read the content of the file. The address will be printed upon start.)

The default memory has three parties in the conversation:

- `user@localdomain`: This is you.
- `swe1@localdomain`: This is the AI agent, Software Engineer 1.  It has already been trained to use the Linux command line.
- `shell@localdomain`: This is the shell robot.

By default the message you type goes to `swe1@localdomain` (or the 1st email address found in memory that is neither user or shell).

Type [ENTER] without anything will bring up a menu which allows you to choose from models and addresses.  Enter the single number (for models) or letter (for email addressses) to make a choice.  Enter `0` to input your own model, or `z` to input a new address.  You can also input ":your subject" to change the email subject. (Try to run a shell command by sending the command as the subject to `shell@localhost`; that's how agents run commands.)

If you want to create a new agent, simply pick a new address to send message to.

# About Models

Mailcoach uses `litellm` (https://github.com/BerriAI/litellm) as the model gateway.  See [Document](https://docs.litellm.ai/docs/providers) for supported providers.

You can optionally supply the API base of the model by appending `@http://the_api_base` to the model name.  Use the following method to use your own vLLM backend.

## Running the vLLM server

The following script serves the Llama 3.3 70B model on a machine with 8 GPUs of 40GB each.  It does 4-way tensor parallelization and 2-way pipeline parallelization; that is, each request is handled by 4 GPUs in parallel, and at most 2 requests can be processed in parallel.

```
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export NCCL_P2P_DISABLE=1
MODEL=Llama-3.3-70B-Instruct
vllm serve $MODEL --tensor-parallel-size 4 --pipeline-parallel-size 2 --dtype bfloat16 --max-model-len 32768 --port 4444
```

## Running Mailcoach

Suppose the above server runs on host `192.168.122.241`, use the following queue file, or chat with `--model hosted_vllm/Llama-3.3-70B-Instruct@http://192.168.122.241:4444/v1`

```
From ----
From: user@localdomain
To: swe1@localdomain
X-Hint-Model: hosted_vllm/Llama-3.3-70B-Instruct@http://192.168.122.241:4444/v1

Generate a fortune using command line.
```

Currently the last message with a `X-Hint-Model` header an agent sees determines its model to use next.  In the chat mode, the chat interface sets the header according to your choice, but in queue automation you have to set the header by yourself, or the models in the memory will be used.
