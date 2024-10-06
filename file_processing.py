import os
import db_backend
import mammoth
import markdownify
from bs4 import BeautifulSoup

#Convert docx to html (so that the HTML can be converted to markdown)
def convert_docx_to_html(docx_path):
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
        messages = result.messages
        print(messages)
    return html

# def clean_proposal_html(html_content):
#     # Parse the HTML content
#     soup = BeautifulSoup(html_content, 'html.parser')

#     # Remove unnecessary tags
#     for tag in soup.find_all(['span', 'o:p', 'style', 'img']):
#         tag.unwrap()  # Removes the tag but keeps the content

#     # Remove attributes from retained tags
#     for tag in soup.find_all(True):
#         tag.attrs = {}  # Removes all attributes

#     # Keep only the text structure with <p>, and headers
#     cleaned_html = soup.prettify()

#     return cleaned_html

def extract_text_from_html(html_content):
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract text content, removing all HTML tags
    text_only = soup.get_text(separator='\n') 
    
    return text_only


# def convert_html_to_markdown(html_path):
#     with open(html_path, "r") as html_file:
#         html = html_file.read()
    
#     markdown = markdownify.markdownify(html)
#     return markdown

def add_proposal_from_file(supabase, filepath, prop_title, rfp_id=None):
    try:
        print("Test")
        # Check if the file exists
        if not os.path.exists(filepath):
            return f"File {filepath} does not exist."

        # Open the file and read its content
        with open(filepath, 'r', encoding='latin-1') as file:
            print("File opened successfully")
            prop_full_text = file.read()
        
        #print(f"File Content (first 100 chars): {prop_full_text[:100]}...")

        # Clean the HTML content
        prop_full_text = extract_text_from_html(prop_full_text)
        print(f"Cleaned Content (first 100 chars): {prop_full_text[:100]}...")

        # Use the existing create_proposal function to add it to the database
        response = db_backend.create_proposal(supabase, prop_title, prop_full_text, rfp_id)
        print(f"Response from DB: {response}")
        
        # Check the response for success and extract the proposal ID
        if response and 'prop_id' in response[0]:  # Assuming prop_id is the correct field
            proposal_id = response[0]['prop_id']
            return f"Proposal '{prop_title}' added successfully with ID: {proposal_id}"
        else:
            return f"Failed to add proposal '{prop_title}'."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred: {e}"
    
# TODO Create a smarter chunking function that splits the text at the end of a sentence / section, but also keeps the chunks within a certain length, and includes an overlap of the last x sentences at the beginning and end of each chunk
def chunk_text(text, chunk_length=1000):
    chunks = []
    # Split the text into chunks of the specified length
    for i in range(0, len(text), chunk_length):
        chunk = text[i:i + chunk_length]
        chunks.append(chunk)
    return chunks

def read_file(filepath):
    with open(filepath, 'r', encoding='latin-1') as file:
        print("File opened successfully")
        prop_full_text = file.read()
        return prop_full_text

# Testing the function
supabase = db_backend.get_supabase_connection()
filepath = './test_proposal.html'
prop_title = 'Test Proposal'

#prop_html = convert_docx_to_html('./test_proposal.docx')
#print(prop_html)

#prop_md = convert_html_to_markdown('./test_proposal.html')
#print(prop_md)
#add_proposal_from_file(supabase, filepath, prop_title)    