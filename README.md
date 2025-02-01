# OpsAgent

## Overview

OpsAgent is a modular AI-driven system that efficiently manages e-commerce functionalities and product-related
inquiries. The system operates around a centralized **Supervisor** that directs user queries to the appropriate *
*sub-agent**, ensuring an optimized and structured response workflow.

## Main Components

### Supervisor

**Role:** The central controller that determines whether to route the conversation to a sub-agent or conclude the
interaction.

**Process:**

- Receives user messages and parses the conversation.
- Uses a GPT-4 based model to output structured JSON.
- Specifies whether the **Product Query Agent** or **E-Commerce Agent** should handle the next step, or if the session
  should end.

### Product Query Agent

**Role:** Specializes in handling product-related questions, search parameters, and product recommendations.

**Interaction:**

- Invokes **product_query_tool** to retrieve or filter relevant product information.
- Generates and executes optimized SQL queries against the local database.

### E-Commerce Agent

**Role:** Manages e-commerce-related tasks such as store configuration, management, and feature implementation.

**Interaction:**

- Uses the **ecommerce_chat_tool** to execute context-specific operations.
- Processes queries by integrating retrieved context from a vector database.
- Constructs responses based on a predefined prompt (ANSWER_PROMPT) and the most relevant documents retrieved.

## Data Flow

1. **User Input:** The system captures user messages in a shared conversation state.
2. **Decision Logic:** The **Supervisor** determines whether the request pertains to product selection, e-commerce
   tasks, or if the conversation should end.
3. **Sub-Agent Execution:** If routed to a sub-agent, that agent processes the given instructions and invokes the
   necessary tools.
4. **Final Answer:** If the **Supervisor** decides to finish, it consolidates all conversation data and generates a
   final answer.

## Future Enhancements

- **Additional Sub-Agents:** Expand capabilities to support more specialized domains.