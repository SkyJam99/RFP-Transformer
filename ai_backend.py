import os
from dotenv import load_dotenv
from openai import OpenAI
from file_processing import extract_text_from_html, read_file, chunk_text
import time
import json
from typing import List
from db_backend import create_lookup, get_supabase_connection, generate_lookup_file

load_dotenv()


def setup_GPT_client():
    client = OpenAI(
        organization= 'org-jIubm8k3HElevXNOWzQoIxOG',
        project= 'proj_aHSkZJkaEFFa2KwQGyEhnx3i',
        api_key = os.getenv("GPT_API_KEY")
    )
    return client

def get_gpt_response(message, client=setup_GPT_client()):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": message}],
        stream=False,
    )
    return response

#print(get_gpt_response("Say this is a test"))

# This will only extract text responses from the assistant TODO switch to JSON response format
def extract_responses(messages):
    responses = []
    for message in messages.data:
        if message.role == "assistant":
            for content_block in message.content:
                if content_block.type == "text":
                    responses.append(content_block.text.value)
    return responses


# This function takes a proposal as input, and uses the assistants API to parse the proposal into the lookup table
# Steps for completion
# DONE - 1. Split proposal into chunks
# DONE - 2. Either create seperate threads for each chunk, or use the same thread for all chunks
# DONE - 3. Read the first few chunks to generate context for the assistant and the lookup table
# DONE - 4. Run each thread through the assistant, extracting verbatim answers, and keywords for searching the lookup table. This should be extracted in JSON format so we can easily parse it later
# 5. Add each answer to the lookup database
# 6. Generate a new lookup file based on everything in the database
# DONE TODO Switch to JSON response format
# TODO Write better instructions for the assistant
# TODO Make the chunking logic more robust and less likely to cut off words / paragraphs
# TODO Switch to seperate threads for each chunk of text. This will reduce input token usage and therefore reduce cost
def parse_proposal_for_lookup(proposalText, client=setup_GPT_client(), chunk_length=20000):
    proposalChunks = chunk_text(proposalText, chunk_length)
    thread = client.beta.threads.create()
    assistant_id = 'asst_rstr7lrME0LAhivV2sJzwLXD' # This is the id of the Proposal Parser assistant

    # Use the first 3 chunks to generate context
    context_chunks = proposalChunks[:2]  
    context = "\n".join(context_chunks)

    # Create a message object associated with the thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here are the first few chunks of the proposal. Generate a short context summary in JSON format that will be used to extract answers and keywords. "
            "The JSON object should include only 'overall_context'. Beginning of Proposal: \n" + context
        ),
    )

    # This sends the thread of messages to the assistant for generation
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

    # This checks the status of the run, and waits until it is completed
    while run.status != "completed":
        print(run.status)
        time.sleep(3)

    # Get the generated context from OpenAi and extract it from the JSON
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    responses = extract_responses(messages)
    context = responses[-1]
    try:
        context_json = json.loads(context)
        overall_context = context_json.get("overall_context", "")
    except json.JSONDecodeError:
        print("Error parsing context JSON")
        overall_context = context
    print(overall_context)

    
    # Create a list to store all of the responses from the assistant
    chunk_responses = []

    # Send each chunk to the assistant to extract verbatim answers
    i = 0
    for chunk in proposalChunks:

        # Create a new thread for each chunk
        thread = client.beta.threads.create()

        # Add the chunk to the thread as a message
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                "Here is a chunk of the proposal. Based on the overall context, extract any verbatim answers that should "
                "be added to an answer database. This database will be used to help write more proposals in the future. "
                "Return the answers in structured JSON format, where each answer has a 'verbatim_answer', a "
                "'req_description', and a list of 'keywords'. If there are no good verbatim answers, respond with an empty JSON list []. "
                "Here is the overall context: [" + context + "]. Here is the chunk to look for useful answers in: [" + chunk + "]"
            ),
        )

        # Send the thread to the assistant for generation
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )

        # Check the status of the run, and wait until it is completed
        while run.status != "completed":
            print(run.status)
            time.sleep(1)

        # Send print message to console about what number chunk we are on out of the total chunks
        print(f"\nChunk {i} of {len(proposalChunks)} Processed")

        # Extract response for the chunk and append to the list of responses
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        chunk_response_json = extract_responses(messages)
        # print(chunk_response_json)
        try:
            chunk_response_json = json.loads(chunk_response_json[0])
            answers = chunk_response_json.get("answers", [])
            for answer in answers:
                chunk_responses.append(answer)
            # chunk_responses.extend(chunk_response_json)
            # print(chunk_responses)
        except:
            print(f"Error parsing JSON for chunk {i}: {chunk_response_json}")

        #chunk_responses.append(extract_responses(messages))
        
        # Move on to the next chunk
        i += 1

    # DEPRECATED # Extract and print all of the responses from the assistant
    # messages = client.beta.threads.messages.list(thread_id=thread.id)
    # responses = extract_responses(messages)

    # Get supabase connection
    supabase = get_supabase_connection()

    # Print all of the responses
    i = 0
    for response in chunk_responses:
        verbatim_answer = response.get("verbatim_answer", "N/A")
        req_description = response.get("req_description", "N/A")
        keywords = response.get("keywords", [])

        # Add the answer to the lookup database
        create_lookup(supabase, req_description, verbatim_answer, keywords, overall_context)

        print(f"Extracted Answer #{i}:\n  Verbatim Answer: {verbatim_answer}\n  Requirement Description: {req_description}\n  Keywords: {', '.join(keywords)}\n")
        i += 1

    # Generate a new lookup file based on everything in the database
    lookup_file_path = generate_lookup_file(supabase)
    print(f"Lookup file generated at: {lookup_file_path}")


    # TODO: Update the lookup file in the RFP assistant (which isn't implemented yet)
    return lookup_file_path



        

filepath = './test_proposal.html'
parse_proposal_for_lookup(extract_text_from_html(read_file(filepath)))
#print(response)
