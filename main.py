import os
from dotenv import load_dotenv
from composio_langchain import Action, ComposioToolSet
from langchain import hub
from langchain.agents import (
    AgentExecutor,
    create_openai_functions_agent,
)
from langchain_openai import ChatOpenAI
from composio.client.collections import TriggerEventData

load_dotenv()
# Initialize the ComposioToolSet
composio_toolset = ComposioToolSet()

# Define the tools
pr_agent_tools = composio_toolset.get_actions(
    actions=[
        Action.GITHUB_GET_CODE_CHANGES_IN_PR,
        Action.GITHUB_PULLS_CREATE_REVIEW_COMMENT,
        Action.SLACKBOT_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL,
    ]
)

# Initialize the language model
llm = ChatOpenAI(model="gpt-4o")
# Define the code review assistant prompt
code_review_assistant_prompt = f"""
        You are an experienced code reviewer.
        Your task is to review the provided file diff and give constructive feedback.

        Follow these steps:
        1. Identify if the file contains significant logic changes.
        2. Summarize the changes in the diff in clear and concise English within 100 words.
        3. Provide actionable suggestions if there are any issues in the code.

        Send the summary of the PR review to the"  "" +os.environ['CHANNEL_ID']+"  "" channel on Slack. Slack doesn't have Markdown, so send a plain text message.
        Also, add the comprehensive review to the PR as a comment.
"""

prompt = hub.pull("hwchase17/openai-functions-agent")
combined_prompt = prompt + code_review_assistant_prompt
# query_agent = create_tool_calling_agent(llm, pr_agent_tools, combined_prompt)
query_agent = create_openai_functions_agent(llm, pr_agent_tools, combined_prompt)
agent_executor = AgentExecutor(agent=query_agent, tools=pr_agent_tools, verbose=True)

# Create a trigger listener
listener = composio_toolset.create_trigger_listener()


@listener.callback(filters={"trigger_name": "github_pull_request_event"})
def review_new_pr(event: TriggerEventData) -> None:
    # Using the information from Trigger, execute the agent
    code_to_review = str(event.payload)
    query_task = f"Review the following code changes: {code_to_review}"
    # Execute the agent
    res = agent_executor.invoke({"input": query_task})
    print(res)


print("Listener started!")
print("Create a PR to get the review")
listener.listen()
