from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://owhhdcqqiewmkaqahbub.supabase.co"
key = os.getenv("SB_API_KEY")
print(key)
supabase = create_client(url, key)

#RFPS CRUD Operations
def create_rfp(supabase, rfp_title, rfp_description, rfp_full_text):
    data = {
        "rfp_title": rfp_title,
        "rfp_description": rfp_description,
        "rfp_full_text": rfp_full_text
    }
    response = supabase.table("rfp").insert(data).execute()
    return response.data

def get_rfps(supabase):
    response = supabase.table("rfp").select("*").execute()
    return response.data

def update_rfp(supabase, rfp_id, new_title, new_description, new_full_text=None):
    response = supabase.table("rfp").update({
        "rfp_title": new_title,
        "rfp_description": new_description,
        "rfp_full_text": new_full_text
    }).eq("rfp_id", rfp_id).execute()
    return response.data

def delete_rfp(supabase, rfp_id):
    response = supabase.table("rfp").delete().eq("rfp_id", rfp_id).execute()
    return response.data

#Requirements CRUD Operations
def create_requirement(supabase, rfp_id, req_text, category):
    data = {"rfp_id": rfp_id, "req_text": req_text, "category": category}
    response = supabase.table("requirements").insert(data).execute()
    return response.data

def get_requirements(supabase):
    response = supabase.table("requirements").select("*").execute()
    return response.data

def update_requirement(supabase, req_id, updated_text):
    response = supabase.table("requirements").update({"req_text": updated_text}).eq("req_id", req_id).execute()
    return response.data

def delete_requirement(supabase, req_id):
    response = supabase.table("requirements").delete().eq("req_id", req_id).execute()
    return response.data

#Proposal CRUD Operations
def create_proposal(supabase, prop_title, prop_full_text, rfp_id=None):
    data = {
        "prop_title": prop_title,
        "rfp_id": rfp_id,
        "prop_full_text": prop_full_text
    }
    response = supabase.table("proposals").insert(data).execute()
    return response.data

def get_proposals(supabase):
    response = supabase.table("proposals").select("*").execute()
    return response.data

def update_proposal(supabase, prop_id, new_title=None, new_rfp_id=None, new_full_text=None):
    update_data = {}
    if new_title:
        update_data["prop_title"] = new_title
    if new_rfp_id is not None:  # Allow updating rfp_id to null
        update_data["rfp_id"] = new_rfp_id
    if new_full_text is not None: # Same for full_text
        update_data["prop_full_text"] = new_full_text

    response = supabase.table("proposals").update(update_data).eq("prop_id", prop_id).execute()
    return response.data

def delete_proposal(supabase, prop_id):
    response = supabase.table("proposals").delete().eq("prop_id", prop_id).execute()
    return response.data

#Answer CRUD Operations
def create_answer(supabase, seq_order, answer_text, approved, prop_id=None, req_id=None):
    data = {
        "seq_order": seq_order,
        "answer_text": answer_text,
        "approved": approved,
        "prop_id": prop_id,
        "req_id": req_id
    }
    response = supabase.table("answers").insert(data).execute()
    return response.data

def get_answers(supabase):
    response = supabase.table("answers").select("*").execute()
    return response.data

def update_answer(supabase, answer_id, seq_order=None, answer_text=None, approved=None, prop_id=None, req_id=None):
    update_data = {}
    if seq_order is not None:
        update_data["seq_order"] = seq_order
    if answer_text:
        update_data["answer_text"] = answer_text
    if approved is not None:
        update_data["approved"] = approved
    if prop_id is not None:
        update_data["prop_id"] = prop_id
    if req_id is not None:
        update_data["req_id"] = req_id

    response = supabase.table("answers").update(update_data).eq("answer_id", answer_id).execute()
    return response.data

def delete_answer(supabase, answer_id):
    response = supabase.table("answers").delete().eq("answer_id", answer_id).execute()
    return response.data

#Lookup CRUD Operations
def create_lookup(supabase, req_text, answer_text, keywords, context, req_id=None, answer_id=None):
    data = {
        "req_text": req_text,
        "answer_text": answer_text,
        "keywords": keywords,
        "context": context,
        "req_id": req_id,
        "answer_id": answer_id
    }
    response = supabase.table("lookup").insert(data).execute()
    return response.data

def get_lookups(supabase):
    response = supabase.table("lookup").select("*").execute()
    return response.data

def update_lookup(supabase, look_id, req_text=None, answer_text=None, keywords=None, context=None, req_id=None, answer_id=None):
    update_data = {}
    if req_text:
        update_data["req_text"] = req_text
    if answer_text:
        update_data["answer_text"] = answer_text
    if keywords is not None:
        update_data["keywords"] = keywords
    if context:
        update_data["context"] = context
    if req_id is not None:
        update_data["req_id"] = req_id
    if answer_id is not None:
        update_data["answer_id"] = answer_id

    response = supabase.table("lookup").update(update_data).eq("look_id", look_id).execute()
    return response.data

def delete_lookup(supabase, look_id):
    response = supabase.table("lookup").delete().eq("look_id", look_id).execute()
    return response.data

#Test the CRUD operations
def test_crud_operations(supabase):
     # 1. Create a new RFP
    print("Creating a new RFP...")
    created = create_rfp(supabase, "Test RFP", "This is a test RFP description", "This is a test RFP full text.")
    assert created, "Create operation failed.\n"
    print(f"Created: {created}")

    # 2. Read RFPs
    print("Reading RFPs...")
    rfps = get_rfps(supabase)
    assert rfps, "Read operation failed.\n"
    print(f"RFPs: {rfps}")

    # 3. Update an RFP
    rfp_id = created[0]['rfp_id']  # Using the ID of the created entry
    print(f"Updating RFP with ID {rfp_id}...")
    updated = update_rfp(supabase, rfp_id, "Updated RFP Title", "Updated RFP Description", "Updated RFP Full Text")
    assert updated, "Update operation failed.\n"
    print(f"Updated: {updated}")

    # 4. Delete the RFP
    print(f"Deleting RFP with ID {rfp_id}...")
    deleted = delete_rfp(supabase, rfp_id)
    assert deleted, "Delete operation failed.\n"
    print(f"Deleted: {deleted}")


    # 1. Create a new requirement
    print("Creating a new requirement...")
    created = create_requirement(supabase, rfp_id=None, req_text="Test requirement", category="General")
    assert created, "Create operation failed.\n"
    print(f"Created: {created}")

    # 2. Read requirements
    print("Reading requirements...")
    requirements = get_requirements(supabase)
    assert requirements, "Read operation failed.\n"
    print(f"Requirements: {requirements}")

    # 3. Update a requirement
    req_id = created[0]['req_id']  # Using the ID of the created entry
    print(f"Updating requirement with ID {req_id}...")
    updated = update_requirement(supabase, req_id, "Updated requirement text")
    assert updated, "Update operation failed.\n"
    print(f"Updated: {updated}")

    # 4. Delete the requirement
    print(f"Deleting requirement with ID {req_id}...")
    deleted = delete_requirement(supabase, req_id)
    assert deleted, "Delete operation failed.\n"
    print(f"Deleted: {deleted}")

    # 1. Create a new proposal with no rfp_id (null)
    print("Creating a new proposal...")
    created = create_proposal(supabase, "Test Proposal", "This is a test proposal full text.")
    assert created, "Create operation failed.\n"
    print(f"Created: {created}")

    # 2. Read proposals
    print("Reading proposals...")
    proposals = get_proposals(supabase)
    assert proposals, "Read operation failed.\n"
    print(f"Proposals: {proposals}")

    # 3. Update the proposal
    prop_id = created[0]['prop_id']  # Using the ID of the created entry
    print(f"Updating proposal with ID {prop_id}...")
    updated = update_proposal(supabase, prop_id, "Updated Proposal Title", new_rfp_id=None, new_full_text="Updated Proposal Full Text")
    assert updated, "Update operation failed.\n"
    print(f"Updated: {updated}")

    # 4. Delete the proposal
    print(f"Deleting proposal with ID {prop_id}...")
    deleted = delete_proposal(supabase, prop_id)
    assert deleted, "Delete operation failed.\n"
    print(f"Deleted: {deleted}")

    # 1. Create a new answer with null prop_id and req_id
    print("Creating a new answer...")
    created = create_answer(supabase, seq_order=1, answer_text="Test Answer", approved=True)
    assert created, "Create operation failed.\n"
    print(f"Created: {created}")

    # 2. Read answers
    print("Reading answers...")
    answers = get_answers(supabase)
    assert answers, "Read operation failed.\n"
    print(f"Answers: {answers}")

    # 3. Update the answer
    answer_id = created[0]['answer_id']  # Using the ID of the created entry
    print(f"Updating answer with ID {answer_id}...")
    updated = update_answer(supabase, answer_id, seq_order=2, answer_text="Updated Answer", approved=False, prop_id=None, req_id=None)
    assert updated, "Update operation failed.\n"
    print(f"Updated: {updated}")

    # 4. Delete the answer
    print(f"Deleting answer with ID {answer_id}...")
    deleted = delete_answer(supabase, answer_id)
    assert deleted, "Delete operation failed.\n"
    print(f"Deleted: {deleted}")

    # 1. Create a new lookup entry with null req_id and answer_id
    print("Creating a new lookup entry...")
    created = create_lookup(supabase, "Test Requirement Text", "Test Answer Text", '{"keywords": ["example", "test"]}', "Test Context")
    assert created, "Create operation failed.\n"
    print(f"Created: {created}")

    # 2. Read lookup entries
    print("Reading lookup entries...")
    lookups = get_lookups(supabase)
    assert lookups, "Read operation failed.\n"
    print(f"Lookups: {lookups}")

    # 3. Update the lookup entry
    look_id = created[0]['look_id']  # Using the ID of the created entry
    print(f"Updating lookup entry with ID {look_id}...")
    updated = update_lookup(supabase, look_id, req_text="Updated Requirement", answer_text="Updated Answer", context="Updated Context")
    assert updated, "Update operation failed.\n"
    print(f"Updated: {updated}")

    # 4. Delete the lookup entry
    print(f"Deleting lookup entry with ID {look_id}...")
    deleted = delete_lookup(supabase, look_id)
    assert deleted, "Delete operation failed.\n"
    print(f"Deleted: {deleted}")

    print(f"\n------------------------\nTests completed successfully.\n------------------------\n")

# Run the test
test_crud_operations(supabase)
