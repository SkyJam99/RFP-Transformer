import os
from dotenv import load_dotenv
from openai import OpenAI
from file_processing import extract_text_from_html, read_file, chunk_text, chunk_text_v2
import time
import json
from typing import List
from db_backend import create_lookup, get_supabase_connection, generate_lookup_file, create_requirement, get_requirements_by_rfp_id, get_lookup_by_id

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



# To Do List
# TODO Write better instructions for the assistant
# TODO Get the proposal text from the database and include proposal ID in the lookup table
# TODO Update the lookup file in the RFP assistant (which isn't implemented yet)
# TODO Include overall context and requirement text (maybe?) in the lookup table



# ------------------------- Proposal Parsing Functions ----------------------
# This function takes a proposal as input, and uses the assistants API to parse the proposal into the lookup table
def parse_proposal_for_lookup(proposalText, client=setup_GPT_client(), chunk_length=20000, chunk_overlap=3):
    # Using the new chunking function
    proposalChunks = chunk_text_v2(proposalText, chunk_length, chunk_overlap)
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
            "Here are the first few chunks of a proposal written by Transnomis Solutions, a traffic software company that creates proposals in response to government rfps (request for proposal)""Generate a context summary in JSON format that will be used to help extract existing answers from the rest of the proposal. These answers will be added to a lookup table that will be used to help write more proposals in the future. "
            "The JSON object should include only 'overall_context'. Here is the beginning of the Proposal: \n" + context
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
    #print(overall_context)

    overall_context_str = json.dumps(overall_context) if isinstance(overall_context, dict) else str(overall_context)
    print("Overall Context: " + overall_context_str + "\n")

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
                "If there are good verbatim answers in the proposal chunk, try to extract longer answers that are more than 1 sentence long. "
                "All of the answers will be checked and edited by a human, so don't worry about making them perfect. "
                "The main goal is to extract the exact text from the proposal that should be included in the lookup table and considered for future proposals. "
                "Here is the overall context: [" + overall_context_str + "]. Here is the chunk to look for useful answers in: [" + chunk + "]"
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
    lookup_file_path = generate_lookup_file(supabase, "database_lookup.json")
    print(f"Lookup file generated at: {lookup_file_path}")


    # TODO: Update the lookup file in the RFP assistant (which isn't implemented yet)
    return lookup_file_path

# ---------------------------- RFP Parsing Functions ----------------------------
# This function takes an RFP as input, and uses the assistants API to parse the RFP into the requirements database

def parse_rfp(rfp_text, rfp_id, client=setup_GPT_client(), chunk_length=20000, chunk_overlap=3):
    print("Parsing RFP")
    # Using the new chunking function
    rfp_chunks = chunk_text_v2(rfp_text, chunk_length, chunk_overlap)
    thread = client.beta.threads.create()
    assistant_id = 'asst_rstr7lrME0LAhivV2sJzwLXD' # This is the id of the Proposal Parser assistant

    # Use the first 3 chunks to generate context
    context_chunks = rfp_chunks[:2]  
    context = "\n".join(context_chunks)

    # Create a message object associated with the thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here are the first few chunks of a RFP (request for proposal) given to Transnomis Solutions, a traffic software company that creates proposals in response to government rfps. Generate a context summary in JSON format that will be used to extract requirements from the rest of the RFP. "
            "The JSON object should include only 'overall_context'. Here is the beginning of the RFP: \n" + context
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
    #print(overall_context)

    overall_context_str = json.dumps(overall_context) if isinstance(overall_context, dict) else str(overall_context)
    print("Context: " + overall_context_str + "\n")

    # Create a list to store all of the responses from the assistant
    chunk_responses = []

    # Send each chunk to the assistant to extract verbatim answers
    i = 0
    for chunk in rfp_chunks:

        # Create a new thread for each chunk
        thread = client.beta.threads.create()

        # Add the chunk to the thread as a message
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                "Here is a chunk of the RFP. Based on the overall context and the chunk of the RFP, extract any verbatim requirements that the proposal should address. "
                "Focus on extracting the exact text from the RFP. "
                "For each requirement, we will attempt to find a matching answers in our database of previous proposals, so requirements should be specific and detailed. "
                "The output should be a JSON object with a 'requirements' object that contains any verbatim requirements found in that chunk of the RFP. If there are no requirements in this chunk, respond with an empty JSON list []. "
                "This is the schema for the JSON object: {'requirements': [{'verbatim_requirement': 'The requirement text goes here.'}]} "
                "Here is the overall context: [" + overall_context_str + "]. Here is the chunk to look for useful answers in: [" + chunk + "]"
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
        print(f"\nChunk {i} of {len(rfp_chunks)-1} Processed")

        # Extract response for the chunk and append to the list of responses
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        chunk_response_json = extract_responses(messages)
        print("Response from ChatGPT: ")
        print(chunk_response_json)
        print("\n")
        try:
            chunk_response_json = json.loads(chunk_response_json[0])
            requirements_list = chunk_response_json.get("requirements", [])
            
            if isinstance(requirements_list, list):
                for requirement in requirements_list:
                    verbatim_requirement = requirement.get("verbatim_requirement")
                    if verbatim_requirement:
                        chunk_responses.append(verbatim_requirement)
            else:
                print(f"\n~~~\nUnexpected format for requirements in chunk {i}: {requirements_list}")
            
            print(chunk_responses)
        except json.JSONDecodeError:
            print(f"Error parsing JSON for chunk {i}: {chunk_response_json}")

        #chunk_responses.append(extract_responses(messages))
    
        # Move on to the next chunk
        i += 1

    # Get supabase connection
    supabase = get_supabase_connection()


    print("\n\nAll Requirements Extracted, now adding to the database\n\n")
    # Print all of the responses
    i = 0
    for response in chunk_responses:
        if isinstance(response, dict):
            verbatim_requirement = response.get("verbatim_requirement", "N/A")
        else: 
            verbatim_requirement = response
        # Add the answer to the requirements database
        create_requirement(supabase, rfp_id, verbatim_requirement, "test")

        print(f"Extracted Requirement #{i}:\n  Verbatim Requirement: {verbatim_requirement}\n")
        i += 1

# ---------------------------- Requirement Matching Function ----------------------------
# This function takes a rfp id as input, and uses the assistants api to match the requirements in the rfp to potential answers in the lookup table
def find_existing_requirement_answers(rfp_id, client=setup_GPT_client()):
    # Step 1: Get the list of requirements associated with the rfp_id
    supabase = get_supabase_connection()
    requirements = get_requirements_by_rfp_id(supabase, rfp_id)

    #print(requirements)

    # Step 2: For each requirement, use the assistant to find the best matching answers in the lookup file (3-5 potential answers per requirement)
    assistant_id = 'asst_AJU8IaPEP7cbaqQtqWNeAtcn'  # This is the assistant with access to the lookup file

    potential_matches = []
    for requirement in requirements:
        requirement_text = requirement.get("req_text", "")
        print(f"\nProcessing requirement: {requirement_text}")
        # Create a new thread for each requirement
        thread = client.beta.threads.create()

        # Add the requirement to the thread as a message
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=(
                "Here is a requirement from the RFP. Find the best matching answers from the lookup file. "
                "Return a JSON object with a list of 'lookup_ids' representing the best matches (3-5 matches). "
                # "If there are no good matches, respond with an empty JSON list []. "
                "The lookup ids should ALWAYS be returned in the following format to ensure that we can parse your response: {'lookup_ids': ['id1', 'id2', 'id3']}. "
                "Ensure that the lookup ids are valid and correspond to the lookup file. "
                # "Here is an example from the lookup file, and what should be returned if applicable:"
                # """Entry in the lookup file: {
                #     "look_id": 239,
                #     "keywords": [
                #         "Stinson ITS",
                #         "Manufacturer",
                #         "Distributor",
                #         "System Integrator",
                #         "Intelligent Transportation Systems",
                #         "Turn-Key Solutions"
                #     ]
                # },"""
                # "Response from the assistant: {'lookup_ids': ['239']}. "
                "Here is the requirement: [" + requirement_text + "]"
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

        # Extract response for the requirement
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        #print(messages)
        response_json = extract_responses(messages)
        print(response_json)
        try:
            response_data = json.loads(response_json[0])
            lookup_ids = response_data.get("lookup_ids", [])
            potential_matches.append({"requirement_id": requirement.get("req_id"), "lookup_ids": lookup_ids})
        except json.JSONDecodeError:
            print(f"Error parsing JSON for requirement {requirement.get('req_id')}: {response_json}")

        

    # Print the potential matches for debugging
    for match in potential_matches:
        print(f"Requirement ID: {match['requirement_id']}")
        for i, lookup_id in enumerate(match["lookup_ids"], 1):
            print(f"  Lookup ID #{i}: {lookup_id}")

    # Step 3: Make the database calls to get the verbatim text from the lookup database
    supabase = get_supabase_connection()
    full_answers = []
    for match in potential_matches:
        requirement_id = match["requirement_id"]
        lookup_ids = match["lookup_ids"]
        requirement_answers = []
        for lookup_id in lookup_ids:
            response = get_lookup_by_id(supabase, lookup_id)
            if response:
                requirement_answers.append(response[0])  # Assuming response is a list of results
        full_answers.append({"requirement_id": requirement_id, "answers": requirement_answers})

    # Print the full answers for debugging
    for answer in full_answers:
        print(f"Requirement ID: {answer['requirement_id']}")
        for i, ans in enumerate(answer["answers"], 1):
            print(f"  Answer #{i}: {ans}")

    # Step 4: Use the assistant api to choose the best answer from the list of potential answers (0 - 2 answers per requirement)

    # Step 5: For each requirement, ask the user to choose the correct answer or enter a new answer (1 answer per requirement) and add the answers to the proposal answers database

    # Step 6: Compile the answers into a proposal, return the proposal text, and store the full proposal in the database


# ---------------------------- Testing Functions ----------------------------
# filepath = './test_proposal.html'
# parse_proposal_for_lookup(extract_text_from_html(read_file(filepath)))
# print("Proposal Parsed")

#generate_lookup_file(get_supabase_connection(), "database_lookup.json")

# rfp_filepath = './test_rfp.html'
# parse_rfp(extract_text_from_html(read_file(rfp_filepath)), 16)
# print("RFP Parsed")

find_existing_requirement_answers(16)
print("Requirements Matched")
