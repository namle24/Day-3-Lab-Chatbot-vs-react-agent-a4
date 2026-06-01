# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Pham Thanh Hang
- **Student ID**: 2A202600593
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implemented**: Frontend User Interface (UI Components, Layout, Styling).
- **Code Highlights**: 
  - Designed and developed the user interface (UI) for the Chatbot and ReAct Agent.
  - Built the chat layout, input field, and components that visually distinguish between normal messages and the Agent's reasoning steps (Thought/Action/Observation).
  - *Note*: My contribution focused solely on the frontend layout, CSS, and component structure. The API integration to connect the UI with the backend logic was handled by another team member.
- **Documentation**: The UI structure was designed to easily receive data from the backend, with states and components prepared to render the reasoning steps independently from the final answer.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Difficulty in displaying the intermediate data stream (Thought/Action steps) of the ReAct Agent on the interface. When the Agent performed multiple reasoning loops, the UI became cluttered without clear separation.
- **Log Source**: Frontend console logs and UI rendering issues during long Agent reasoning processes.
- **Diagnosis**: The initial UI was not optimized to display raw text containing keywords like `Action:` or `Observation:`. Long reasoning chains made it hard for users to focus on the main answer.
- **Solution**: Designed separate UI blocks (e.g., collapsible panels or dimmed text areas) specifically to contain the "Thought" process of the Agent, keeping the interface clean and enhancing UX.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: The `Thought` block makes the model's thinking process transparent. Unlike a standard Chatbot that answers immediately (and sometimes hallucinates), the ReAct Agent analyzes the problem, decides which tool to use, and evaluates the results before giving a final answer.
2.  **Reliability**: The ReAct Agent might perform *worse* than a standard Chatbot on basic conversational questions (like greetings) or very simple tasks. It tends to "overcomplicate" the problem by unnecessarily calling tools, leading to slower response times or occasionally getting stuck in an error loop.
3.  **Observation**: Feedback from the environment (tool results) helps keep the Agent grounded in reality. If a search yields no results, the Agent can "observe" this and change its reasoning direction instead of hallucinating.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: From a frontend perspective, we should switch to using WebSockets instead of standard HTTP REST. This allows real-time, low-latency streaming of the Agent's thoughts and actions as they happen.
- **Safety**: Build an error-filtering mechanism on the frontend to display user-friendly error messages, rather than printing the entire raw error stack or system prompt if the backend encounters an issue.
- **Performance**: Implement Virtualization (virtual list rendering) for the chat window to maintain smooth scrolling and performance when the conversation becomes extremely long due to extensive tool call histories.

---