import os
import db_backend

def add_proposal_from_file(supabase, filepath, prop_title, rfp_id=None):
    try:
        # Check if the file exists
        if not os.path.exists(filepath):
            return f"File {filepath} does not exist."

        # Open the file and read its content
        with open(filepath, 'r', encoding='utf-8') as file:
            prop_full_text = file.read()

        # Use the existing create_proposal function to add it to the database
        response = db_backend.create_proposal(supabase, prop_title, prop_full_text, rfp_id)
        
        # Check the response for success and extract the proposal ID
        if response and 'prop_id' in response[0]:  # Assuming the ID field is named 'id'
            proposal_id = response[0]['id']
            return f"Proposal '{prop_title}' added successfully with ID: {proposal_id}"
        else:
            return f"Failed to add proposal '{prop_title}'."
    except Exception as e:
        return f"An error occurred: {e}"
    

    # Testing the function
    