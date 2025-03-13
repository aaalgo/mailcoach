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

# Quickstart

## Chat with Agents

```
mailcoach
```

The full command is

```
mailcoach [-m path_to_memory] [-t path_to_trace] [-u user_address] [--debug]
```

- If a memory file is not specified, a sample is loaded.
- If a trace path is not specified, the trace is written to `mailcoach.YYYYMMDDHHMMSS` under the current directory.
- If the user address is specified, use this address to represent the user. 
- If --debug is specified, ask for confirmation before each AI generation.

Memory file and trace file (and also the queue file) are of the same format.
You can load the trace file with `-m` to continue an existing session.

## The Default Memory

(You are encouraged to read the content of the file. The address will be printed upon start.)

The default memory has three parties in the conversation:

- `user@localdomain`: This is you.
- `swe1@localdomain`: This is the AI agent, Software Engineer 1.  It has already been trained to use the Linux command line.
- `shell@localdomain`: This is the shell robot.

By default the message you type goes to `swe1@localdomain` (or the 1st email address found in memory that is neither user or shell).

Type [ENTER] without anything will bring up a menu which allows you to choose from models and addresses.  Enter the single number (for models) or letter (for email addressses) to make a choice.  Enter `0` to input your own model, or `z` to input a new address.  You can also input ":your subject" to change the email subject. (Try to run a shell command by sending the command as the subject to `shell@localhost`; that's how agents run commands.)

If you want to create a new agent, simply pick a new address to send message to.

## Task Automation

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

Mailcoach will run in non-interactive mode until all messages to AI agents are processed.  The messages to the user will not be processed.  If you rig a multi-agent conversation, make sure you set a budget so the conversation doesn't go one forever.

## Task Automation in Auto Pilot Mode

In the auto pilot mode, the AI will play the user role as well, so conversation will keep on until budget is reached.  You must provide a budget in auto pilot mode.

```
mailcoach -m queue.mbox --auto --budget 0.001  # Use at most 5 cents.
```

**Warning:** The agent has access to the shell and currently it's not restricted. Please keep an eye on its activity. 

