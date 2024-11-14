import os
from dotenv import load_dotenv
from openai import OpenAI
from file_processing import extract_text_from_html, read_file, chunk_text, chunk_text_v2
import time
import json
import re
from typing import List
from db_backend import create_lookup, get_rfp_by_id, get_supabase_connection, generate_lookup_file, create_requirement, get_requirements_by_rfp_id, get_lookup_by_id, update_rfp, create_answer, create_proposal, get_answer_by_req_id, update_answer, update_proposal_status, update_rfp_status, update_proposal

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


# Function for processing one chunk at a time and storing the generated answers in the database
def process_chunk(chunk, overall_context, client, assistant_id, supabase, chunk_index, total_chunks):
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
            "Here is the overall context: [" + overall_context + "]. Here is the chunk to look for useful answers in: [" + chunk + "]"
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
    print(f"\nChunk {chunk_index + 1} of {total_chunks} Processed")
    
    # Extract response for the chunk and parse
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    chunk_response_json = extract_responses(messages)
    try:
        chunk_response_json = json.loads(chunk_response_json[0])
        answers = chunk_response_json if isinstance(chunk_response_json, list) else chunk_response_json.get("answers", [])
        # For each answer, store in database and print
        i = 0
        for answer in answers:
            verbatim_answer = answer.get("verbatim_answer", "N/A")
            req_description = answer.get("req_description", "N/A")
            keywords = answer.get("keywords", [])
            # Add the answer to the lookup database
            create_lookup(supabase, req_description, verbatim_answer, keywords, overall_context, req_id=None, answer_id=None, chunk_extracted_from=chunk)
            print(f"Extracted Answer #{i}:\n  Verbatim Answer: {verbatim_answer}\n  Requirement Description: {req_description}\n  Keywords: {', '.join(keywords)}\n")
            i += 1
    except Exception as e:
        print(f"Error parsing JSON for chunk {chunk_index + 1}: {chunk_response_json}")
        print(f"Exception: {e}")

# Function for controlling the parsing of a proposal one chunk at a time
def parse_proposal_for_lookup(proposalText, prop_id, client=setup_GPT_client(), chunk_length=20000, chunk_overlap=3):
    # Get supabase connection
    supabase = get_supabase_connection()

    # Create the proposal in the database and set status to processing
    update_proposal_status(supabase, prop_id, "processing")
    
    # Using the new chunking function
    proposalChunks = chunk_text_v2(proposalText, chunk_length, chunk_overlap)
    assistant_id = 'asst_rstr7lrME0LAhivV2sJzwLXD'  # This is the id of the Proposal Parser assistant

    # Use the first 2 chunks to generate context
    context_chunks = proposalChunks[:2]  
    context = "\n".join(context_chunks)

    # Create a thread and generate the overall context
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here are the first few chunks of a proposal written by Transnomis Solutions, a traffic software company that creates proposals in response to government rfps (request for proposal). "
            "Generate a context summary in JSON format that will be used to help extract existing answers from the rest of the proposal. These answers will be added to a lookup table that will be used to help write more proposals in the future. "
            "The JSON object should include only 'overall_context'. Here is the beginning of the Proposal: \n" + context
        ),
    )

    # Send to assistant
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

    # Wait until run is completed
    while run.status != "completed":
        print(run.status)
        time.sleep(3)

    # Get the generated context from OpenAI and extract it from the JSON
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    responses = extract_responses(messages)
    context = responses[-1]
    try:
        context_json = json.loads(context)
        overall_context = context_json.get("overall_context", "")
    except json.JSONDecodeError:
        print("Error parsing context JSON")
        overall_context = context

    overall_context_str = json.dumps(overall_context) if isinstance(overall_context, dict) else str(overall_context)
    print("Overall Context: " + overall_context_str + "\n")

    # Update overall context in the database
    update_proposal(supabase, prop_id, None, None, None, overall_context_str)

    # Process each chunk
    total_chunks = len(proposalChunks)
    for i, chunk in enumerate(proposalChunks):
        process_chunk(chunk, overall_context_str, client, assistant_id, supabase, i, total_chunks)

    # Generate a new lookup file based on everything in the database
    lookup_file_path = generate_lookup_file(supabase, "database_lookup.json")
    print(f"Lookup file generated at: {lookup_file_path}")

    # Update the proposal in the database and set status to complete
    update_proposal_status(supabase, prop_id, "complete")
    
    # TODO: Update the lookup file in the RFP assistant (which isn't implemented yet)
    return lookup_file_path

    

    




# ---------------------------- RFP Parsing Functions ----------------------------
# This function takes an RFP as input, and uses the assistants API to parse the RFP into the requirements database

# Function to process one chunk at a time and store the generated requirements in the database
def process_rfp_chunk(chunk, overall_context_str, client, assistant_id, supabase, rfp_id, chunk_index, total_chunks, prop_id):
    # Create a new thread for each chunk
    thread = client.beta.threads.create()

    # Add the chunk to the thread as a message
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here is a chunk of the RFP. Based on the overall context and the chunk of the RFP, extract any verbatim requirements that the proposal should address. "
            "Focus on extracting the exact text from the RFP. "
            "For each requirement, we will attempt to find matching answers in our database of previous proposals, so requirements should be specific and detailed. "
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

    # Wait until the run is completed
    while run.status != "completed":
        print(run.status)
        time.sleep(1)

    # Print progress
    print(f"\nChunk {chunk_index + 1} of {total_chunks} Processed")

    # Extract response for the chunk and process
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
                    # Add the requirement to the requirements database
                    response = create_requirement(supabase, rfp_id, verbatim_requirement, "test", chunk)
                    requirement_id = response[0].get("req_id")
                    create_answer(supabase, None, None, False, prop_id, requirement_id, None)
                    print(f"Extracted Requirement:\n  Verbatim Requirement: {verbatim_requirement}\n")
        else:
            print(f"\n~~~\nUnexpected format for requirements in chunk {chunk_index + 1}: {requirements_list}")
    except json.JSONDecodeError:
        print(f"Error parsing JSON for chunk {chunk_index + 1}: {chunk_response_json}")

# Function to control the parsing of an RFP, chunk the text, generate context, and process each chunk
def parse_rfp(rfp_text, rfp_id, client=setup_GPT_client(), chunk_length=20000, chunk_overlap=3):
    print("Parsing RFP")
    # Using the new chunking function
    rfp_chunks = chunk_text_v2(rfp_text, chunk_length, chunk_overlap)
    assistant_id = 'asst_rstr7lrME0LAhivV2sJzwLXD'  # This is the id of the Proposal Parser assistant

    # Get supabase connection
    supabase = get_supabase_connection()

    # Set the RFP status to processing
    update_rfp_status(supabase, rfp_id, "processing")

    # Use the first few chunks to generate context
    context_chunks = rfp_chunks[:2]  
    context = "\n".join(context_chunks)

    # Create a thread and generate the overall context
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here are the first few chunks of a RFP (request for proposal) given to Transnomis Solutions, a traffic software company that creates proposals in response to government rfps. Generate a context summary in JSON format that will be used to extract requirements from the rest of the RFP. "
            "The JSON object should include only 'overall_context'. Here is the beginning of the RFP: \n" + context
        ),
    )

    # Send to assistant
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

    # Wait until run is completed
    while run.status != "completed":
        print(run.status)
        time.sleep(3)

    # Get the generated context from OpenAI and extract it from the JSON
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    responses = extract_responses(messages)
    context = responses[-1]
    try:
        context_json = json.loads(context)
        overall_context = context_json.get("overall_context", "")
    except json.JSONDecodeError:
        print("Error parsing context JSON")
        overall_context = context

    overall_context_str = json.dumps(overall_context) if isinstance(overall_context, dict) else str(overall_context)
    print("Context: " + overall_context_str + "\n")


    # Update overall context in the database
    update_rfp(supabase, rfp_id, None, None, None, overall_context_str)

    # Create proposal entry in the database
    response = create_proposal(supabase, None, None, rfp_id)
    prop_id = response[0].get("prop_id")

    print("Processing chunks now")

    # Process each chunk
    total_chunks = len(rfp_chunks)
    for i, chunk in enumerate(rfp_chunks):
        process_rfp_chunk(chunk, overall_context_str, client, assistant_id, supabase, rfp_id, i, total_chunks, prop_id)

    print("\n\nAll Requirements Extracted and added to the database\n\n")

    # Update the RFP status to complete
    update_rfp_status(supabase, rfp_id, "complete")


# ---------------------------- Requirement Matching Function ----------------------------
# This function takes a rfp id as input, and uses the assistants api to match the requirements in the rfp to potential answers in the lookup table
# TODO Refactor this function to be more modular, and also return the first final results to the user before moving on to the next requirement
# TODO Write the end of the function for asking for user output, but might make sense to wait until we have the ui for that
# TODO Make a seperate function for step 6
# TODO Take another look at what I am storing in the database, could be a good way to split this function into smaller parts
# TODO Run the code with PDB to see what the contents of the variables are at each step
# TODO Add lookup_id to the answers database to keep track of where the answers came from



# Function to process a single requirement
def process_requirement(requirement, prop_id, overall_context, client, assistant_id_lookup, assistant_id_parser, supabase, answer_id, req_id):
    requirement_text = requirement.get("req_text", "")
    requirement_id = requirement.get("req_id")
    print(f"\nProcessing requirement ID {requirement_id}: {requirement_text}")

    # Step 2: Use the assistant to find the best matching answers in the lookup file (3-5 potential answers per requirement)
    # Assistant ID for lookup
    print("Finding potential matches from lookup file...")
    thread = client.beta.threads.create()

    # Add the requirement to the thread as a message
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here is a requirement from the RFP. Find the best matching answers from the lookup file. "
            "Return a JSON object with a list of 'lookup_ids' representing the best matches (3-5 matches). "
            "The lookup ids should ALWAYS be returned in the following format to ensure that we can parse your response: {'lookup_ids': ['id1', 'id2', 'id3']}. "
            "Ensure that the lookup ids are valid and correspond to the lookup file. "
            "Here is some overall context about the RFP: [" + overall_context + "]. "
            "Here is the requirement: [" + requirement_text + "]"
        ),
    )

    # Send the thread to the assistant for generation
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id_lookup,
    )

    # Wait until the run is completed
    timeout = 0
    while run.status != "completed":
        print(run.status)
        time.sleep(1)
        if timeout > 10:
            print("Timeout reached for chat completion")
            return
        timeout = timeout + 1

    # Extract response for the requirement
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    full_response = extract_responses(messages)
    print("Full Response from Assistant (Lookup):", full_response)

    # Extract JSON from the response
    response_json = []
    for response in full_response:
        json_match = re.search(r'({.*?})', response, re.DOTALL)
        if json_match:
            response_json.append(json_match.group(1))

    if not response_json:
        print(f"No valid JSON found in assistant response for requirement ID {requirement_id}")
        return

    try:
        response_data = json.loads(response_json[0])
        lookup_ids = response_data.get("lookup_ids", [])
        print(f"Lookup IDs found: {lookup_ids}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for requirement ID {requirement_id}: {e}")
        return

    # Step 3: Retrieve verbatim text from the lookup database
    full_answers = []
    for lookup_id in lookup_ids:
        response = get_lookup_by_id(supabase, lookup_id)
        if response:
            full_answers.append(response[0])
        else:
            print(f"No lookup entry found for ID {lookup_id}")

    if not full_answers:
        print(f"No answers found in lookup database for requirement ID {requirement_id}")
        return

    # Step 4: Use the assistant to choose the best answer(s) from the list of potential answers (0 - 2 answers per requirement)
    print("Selecting the best answers from potential matches...")
    thread = client.beta.threads.create()

    # Prepare the answers content
    answers_content = json.dumps(full_answers, ensure_ascii=False)

    # Add the requirement and potential answers to the thread as a message
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            "Here are the potential answers for a requirement from an RFP. Choose the best answers from the list. "
            "Return a JSON object with zero to two 'lookup_ids' representing the best matches. "
            "If there are no good matches, respond with an empty JSON object {}. "
            "Ensure that the lookup ids are valid and correspond to the answers given to choose from. "
            "Here is some overall context about the RFP: [" + overall_context + "]. "
            "Here is the requirement: [" + requirement_text + "]. "
            "Here are the potential answers: " + answers_content
        ),
    )

    # Send the thread to the assistant for generation
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id_parser,
    )

    timeout = 0
    while run.status != "completed":
        print(run.status)
        time.sleep(1)
        if timeout > 10:
            print("Timeout reached for chat completion")
            return
        timeout = timeout + 1

    # Extract response for the requirement
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    full_response = extract_responses(messages)
    print("Full Response from Assistant (Selection):", full_response)

    # Extract JSON from the response
    response_json = []
    for response in full_response:
        json_match = re.search(r'({.*?})', response, re.DOTALL)
        if json_match:
            response_json.append(json_match.group(1))

    if not response_json:
        print(f"No valid JSON found in assistant response for requirement ID {requirement_id}")
        return

    try:
        response_data = json.loads(response_json[0])
        selected_lookup_ids = response_data.get("lookup_ids", [])
        print(f"Selected Lookup IDs: {selected_lookup_ids}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for requirement ID {requirement_id}: {e}")
        return

    # Step 5: Update the database with the selected answers
    # TODO, include the remaining details in the answer update
    print(f"Updating database with selected answers for requirement ID {requirement_id}...")
    print(update_answer(supabase, answer_id, None, None, None, prop_id, req_id, selected_lookup_ids))

    # For debugging purposes, print the selected answers
    for lookup_id in selected_lookup_ids:
        answer = next((ans for ans in full_answers if str(ans.get("look_id")) == str(lookup_id)), None)
        if answer:
            print(f"Selected Answer for Requirement ID {requirement_id}:\n{answer}")
        else:
            print(f"Lookup ID {lookup_id} not found in potential answers for requirement ID {requirement_id}")

# Function to manage the overall process
def find_existing_requirement_answers(rfp_id, prop_id, client=setup_GPT_client()):
    # Step 1: Get the list of requirements associated with the rfp_id
    supabase = get_supabase_connection()
    requirements = get_requirements_by_rfp_id(supabase, rfp_id)
    rfp = get_rfp_by_id(supabase, rfp_id)

    # Set proposal status to processing
    update_proposal_status(supabase, prop_id, "processing")

    overall_context = rfp[0].get("rfp_overall_context", "")
    print(f"Overall Context: {overall_context}")

    # Assistant IDs
    assistant_id_lookup = 'asst_AJU8IaPEP7cbaqQtqWNeAtcn'  # Assistant with access to the lookup file
    assistant_id_parser = 'asst_rstr7lrME0LAhivV2sJzwLXD'  # Proposal Parser assistant

    # Step 2 to 5: Process each requirement
    for requirement in requirements:
        answer = get_answer_by_req_id(supabase, requirement.get("req_id"))
        print(answer)
        answer_id = answer[0]['answer_id']
        process_requirement(requirement, prop_id, overall_context, client, assistant_id_lookup, assistant_id_parser, supabase, answer_id)

    # TODO Set proposal status to complete
    update_proposal_status(supabase, prop_id, "complete")



# Requirement Matching Function Single Requirement
# This function takes a single requirement as input, and uses the assistants api to match the requirement to potential answers in the lookup table
# def single_requirement_matching(requirement_id, overall_context, client=setup_GPT_client()):

# ---------------------------- Testing Functions ----------------------------
# filepath = './test_proposal.html'
# parse_proposal_for_lookup(extract_text_from_html(read_file(filepath)))
# print("Proposal Parsed")

#generate_lookup_file(get_supabase_connection(), "database_lookup.json")

# rfp_filepath = './test_rfp.html'
# parse_rfp(extract_text_from_html(read_file(rfp_filepath)), 16)
# print("RFP Parsed")

# find_existing_requirement_answers(16)
# print("Requirements Matched")
