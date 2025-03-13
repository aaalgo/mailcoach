Mailcoach
=========

Wei Dong

wdong@aaalgo.com

# Introduction

Mailcoach is the self-contained single-user version of [Postline](https://arxiv.org/abs/2502.09903).  Mailcoach realizes the AI agent architecture by:

- Using email as the communication protocol.
- Extending the standard chat paradigm into multi-party chat.
- Allowing robots (commonly referred to as tools) to connect into the chat.

# Setup

Method 1. Directly install from git repo.
```
pip3 install git+https://github.com/aaalgo/mailcoach.git
```

Method 2. Checkout the codebase.

This method allows you to make change to the source code after installation, and have your change reflected immediately without reinstallation.
```
git clone https://github.com/aaalgo/mailcoach
cd mailcoach
pip3 install -e .
```

# Quickstart

## Chat with Agents

```
mailcoach [-m path_to_memory_file] [-t path_to_trace_file]
```

- If a memory file is not specified, a sample is loaded.
- If a trace path is not specified, the trace is written to `mailcoach.YYYYMMDDHHMMSS` under the current directory.

Memory file and trace file are of the same format.  You can load the trace file
with `-m` to continue an existing session.

## Task Automation

Prepare a text file called `task.mbox` using the following content:

```
From ----
From: user@localdomain
To: swe1@localdomain
X-Hint-Model: openai/gpt-4o-mini

Generate a fortune using command line.
```

Then run

```
mailcoach -m task.mbox
```

Mailcoach will run in non-interactive mode until all messages to AI agents are processed.  The messages to the user will not be responded to.

## Task Automation in Auto Pilot Mode

In the auto pilot mode, the AI will play the user role as well, so conversation will keep on until budget is reached.  You must provide a budget in auto pilot mode.

```
mailcoach -m task.mbox --auto --budget 0.05  # Use at most 5 cents.
```

# Tips

The default session has three parties in the conversation:

- `user@localdomain`: That's you.
- `swe1@localdomain`: This is the 1st AI agent, Software Engineer 1.
- `shell@localdomain`:  This is the shell robot.

If you just type a message, the message goes to `swe1@localdomain`.

Type [ENTER] without anything will bring up a menu which allows you to choose from models and the target of message.  Just enter the single number (for models) or letter (for email addressses) to make a choice.  Enter `0` to input your own model, or `z` to input a new address.  You can also use ":your subject" to change the email subject.

If you want to create a new agent, simply pick a new address to send message to.
