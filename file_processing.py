import os
import db_backend
import mammoth
import markdownify

#Convert docx to html (so that the HTML can be converted to markdown)
def convert_docx_to_html(docx_path):
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
        messages = result.messages
        print(messages)
    return html

def convert_html_to_markdown(html_path):
    with open(html_path, "r") as html_file:
        html = html_file.read()
    
    markdown = markdownify.markdownify(html)
    return markdown

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
supabase = db_backend.get_supabase_connection()
filepath = './test_proposal.docx'
prop_title = 'Test Proposal'

#prop_html = convert_docx_to_html('./test_proposal.docx')
#print(prop_html)

prop_md = convert_html_to_markdown('./test_proposal.html')
print(prop_md)
#add_proposal_from_file(supabase, filepath, prop_title)    