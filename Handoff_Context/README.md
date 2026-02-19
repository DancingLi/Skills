# Handoff Context

A skill for generating context handoff Markdown files when transitioning between Agent sessions.

## Features

- Compresses current session context into a single `handoff_context.md` file
- Captures current goals, research findings, and execution plans
- High signal-to-noise ratio output
- Enables seamless context transfer between Agent sessions

## When to Use

Invoke this skill when you need to:

- Switch to a new Agent session
- Transfer current work state to another Agent
- Preserve session context when approaching complexity limits
- Create a checkpoint for complex multi-step tasks

## Output

The generated `handoff_context.md` file contains:

### Current Goal
A clear description of the core problem to be solved.

### Research Findings
- Confirmed relevant file paths
- Key code locations (line numbers) and function names
- Factual understanding of the current system/code logic

### Execution Plan
- Detailed implementation steps
- File modifications for each step
- Verification/testing methods for each change

## Output Specifications

| Property | Value |
|----------|-------|
| Filename | `handoff_context.md` |
| Location | Current working directory |
| Format | Markdown |
| Language | Matches current conversation language |

## Best Practices

- Include only high signal-to-noise information useful for the next Agent
- Exclude conversation history, error logs, and failed attempts
- Focus on factual information, not search processes
- Keep content concise, clear, and actionable

## License

MIT License
