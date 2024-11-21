from flask import Flask, redirect, render_template, request, url_for, jsonify
import ai_backend
import db_backend
import file_processing
import time
import threading
app = Flask(__name__)

#Main Page
@app.route('/')
def main_page():
    return render_template('main_page.html')

#Proposal Parsing
@app.route('/proposal/parsing')
def proposal_parsing():
    return render_template('proposal_parsing_page.html')


#RFP Parsing
@app.route('/rfp/parsing')
def rfp_parsing():
    return render_template('rfp_parsing_page.html')

# Requirement Editing
@app.route('/requirement/editing')
def requirement_editing():
    rfp_id = request.args.get('rfp_id')
    if not rfp_id:
        return "No RFP ID provided", 400
    return render_template('edit_extracted_requirement_page.html', rfp_id=rfp_id)

# Lookup / Answer Editing
@app.route('/lookup/editing')
def lookup_editing():
    prop_id = request.args.get('prop_id')
    if not prop_id:
        return "No Proposal ID provided", 400
    return render_template('edit_extracted_answer_page.html', prop_id=prop_id)

#Proposal Writing
@app.route('/proposal/writing')
def proposal_writing():
    return render_template('proposal_writing_page.html')

#Proposal Editing
@app.route('/proposal/editing')
def proposal_editing():
    prop_id = request.args.get('prop_id')
    if not prop_id:
        return "No Proposal ID provided", 400
    return render_template('proposal_editing_page.html', prop_id=prop_id)

# Answer Editing
@app.route('/answer/editing')
def answer_editing():
    prop_id = request.args.get('prop_id')
    answer_id = request.args.get('answer_id')
    if not answer_id or not prop_id:
        return "No Proposal ID or Answer ID provided", 400
    return render_template('answer_editing_page.html', prop_id=prop_id, answer_id=answer_id)

#File upload routes
@app.route('/upload_proposal', methods=['POST'])
def upload_proposal():
    if 'prop_file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['prop_file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    title = request.form.get("title")

    if not title:
        return jsonify({"error": "Title missing"}), 400
    
    if file:
        file_content = file.read()
        full_text = file_processing.extract_text_from_html(file_content)
        supabase = db_backend.get_supabase_connection()
        result = db_backend.create_proposal(supabase, title, full_text)
        if result is None:
            return jsonify({"error": "Error creating Proposal in DB"}), 400
        
        # Get the prop_id from the result
        prop_id = result[0]['prop_id']
        
        # Start parsing the rfp
        parsing_thread = threading.Thread(target = ai_backend.parse_proposal_for_lookup, args = (full_text, prop_id))
        parsing_thread.start()
        

        return jsonify({'redirect_url': url_for('lookup_editing', prop_id=prop_id)})


@app.route('/upload_rfp', methods=['POST'])
def upload_rfp():
    if 'rfp_file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['rfp_file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    title = request.form.get("title")
    description = request.form.get("description")

    if not title or not description:
        return jsonify({"error": "Title or description missing"}), 400
    
    if file:
        file_content = file.read()
        full_text = file_processing.extract_text_from_html(file_content)
        supabase = db_backend.get_supabase_connection()
        result = db_backend.create_rfp(supabase, title, description, full_text)
        if result is None:
            return jsonify({"error": "Error creating RFP in DB"}), 400
        
        # Get the rfp_id from the result
        rfp_id = result[0]['rfp_id']
        
        # Create new proposal for this rfp
        result = db_backend.create_proposal(supabase, f"Proposal for {title}", None, rfp_id)
        if result is None:
            return jsonify({"error": "Error creating Proposal in DB"}), 400
        
        proposal_title = "Proposal for " + title

        client = ai_backend.setup_GPT_client()

        # Start parsing the rfp
        parsing_thread = threading.Thread(target = ai_backend.parse_rfp, args = (full_text, rfp_id, client, 20000, 3, proposal_title))
        parsing_thread.start()
    

        return jsonify({'redirect_url': url_for('requirement_editing', rfp_id=rfp_id)})



@app.route('/get_next_lookup', methods=['GET'])
def get_next_lookup():
    prop_id = request.args.get('prop_id')
    look_id = request.args.get('look_id')

    if not prop_id:
        return jsonify({'error': 'Missing prop_id'}), 400
    
    if not look_id:
        return jsonify({'error': 'Missing look_id'}), 400

    # Get the next lookup based on prop_id and look_id
    next_lookup = db_backend.get_next_lookup(db_backend.get_supabase_connection(), prop_id, look_id)

    if next_lookup == -1:
        # Next requirement isn't ready yet
        return jsonify({'look_id': -1})
    elif next_lookup:
        return jsonify({
            'look_id': next_lookup['look_id'],
            'chunk_text': next_lookup['chunk_extracted_from'],
            'answer_text': next_lookup['answer_text']
        })
    else:
        # No more lookups
        return jsonify({'look_id': 0})


@app.route('/get_next_requirement', methods=['GET'])
def get_next_requirement():
    rfp_id = request.args.get('rfp_id')
    req_id = request.args.get('req_id')

    if not rfp_id:
        return jsonify({'error': 'Missing rfp_id'}), 400
    
    if not req_id:
        return jsonify({'error': 'Missing req_id'}), 400

    # Get the next requirement based on rfp_id and req_id
    next_requirement = db_backend.get_next_requirement(db_backend.get_supabase_connection(), rfp_id, req_id)

    if next_requirement == -1:
        # Next requirement isn't ready yet
        return jsonify({'req_id': -1})
    elif next_requirement:
        return jsonify({
            'req_id': next_requirement['req_id'],
            'chunk_text': next_requirement['chunk_extracted_from'],
            'req_text': next_requirement['req_text']
        })
    else:
        # No more requirements
        return jsonify({'req_id': 0})

@app.route('/get_next_answer', methods=['GET'])
def get_next_answer():
    prop_id = request.args.get('prop_id')
    answer_id = request.args.get('answer_id')

    if not prop_id:
        return jsonify({'error': 'Missing prop_id'}), 400
    
    if not answer_id:
        return jsonify({'error': 'Missing answer_id'}), 400

    # Get the next answer based on prop_id and answer_id
    next_answer = db_backend.get_next_answer(db_backend.get_supabase_connection(), prop_id, answer_id)

    if next_answer == -1:
        # Error getting next answer or no more answers
        return jsonify({'answer_id': -1})
    elif next_answer:
        return jsonify({
            'answer_id': next_answer['answer_id'],
            'req_text': next_answer['req_text'],
            'answer_text': next_answer['answer_text'],
            'potential_answers': next_answer['potential_answers']
        })
    else:
        # No more answers
        return jsonify({'answer_id': 0})
    
@app.route('/get_previous_answer', methods=['GET'])
def get_previous_answer():
    prop_id = request.args.get('prop_id')
    answer_id = request.args.get('answer_id')

    if not prop_id:
        return jsonify({'error': 'Missing prop_id'}), 400
    
    if not answer_id:
        return jsonify({'error': 'Missing answer_id'}), 400
    
    # Get the previous answer based on prop_id and answer_id
    previous_answer = db_backend.get_previous_answer(db_backend.get_supabase_connection(), prop_id, answer_id)

    if previous_answer == -1:
        # Error getting previous answer or no more answers
        return jsonify({'answer_id': -1})
    elif previous_answer:
        return jsonify({
            'answer_id': previous_answer['answer_id'],
            'req_text': previous_answer['req_text'],
            'answer_text': previous_answer['answer_text'],
            'potential_answers': previous_answer['potential_answers']
        })
    else:
        # No more answers
        return jsonify({'answer_id': 0})


#CRUD Operations

#RFP Functions
@app.route('/rfp', methods=['POST'])
def create_rfp():
    rfp = request.json
    result = db_backend.create_rfp(db_backend.get_supabase_connection(), rfp['rfp_title'], rfp['rfp_description'], rfp['rfp_full_text'])
    return jsonify(result)

@app.route('/rfp', methods=['GET'])
def get_rfps():
    result = db_backend.get_rfps(db_backend.get_supabase_connection())
    return jsonify(result)

@app.route('/rfp/<int:rfp_id>', methods=['GET'])
def get_rfp(rfp_id):
    result = db_backend.get_rfp_by_id(db_backend.get_supabase_connection(), rfp_id)
    return jsonify(result)

@app.route('/rfp/<int:rfp_id>', methods=['PUT'])
def update_rfp(rfp_id):
    rfp = request.json
    result = db_backend.update_rfp(db_backend.get_supabase_connection(), rfp_id, rfp['rfp_title'], rfp['rfp_description'], rfp['rfp_full_text'], rfp["rfp_overall_context"])
    return jsonify(result)

@app.route('/rfp/<int:rfp_id>', methods=['DELETE'])
def delete_rfp(rfp_id):
    result = db_backend.delete_rfp(db_backend.get_supabase_connection(), rfp_id)
    return jsonify(result)

#Requirement Functions
@app.route('/requirement', methods=['POST'])
def create_requirement():
    requirement = request.json
    result = db_backend.create_requirement(db_backend.get_supabase_connection(), requirement['rfp_id'], requirement['req_text'], requirement['category'], requirement['chunk_extracted_from'])
    return jsonify(result)

@app.route('/requirement', methods=['GET'])
def get_requirements():
    result = db_backend.get_requirements(db_backend.get_supabase_connection())
    return jsonify(result)

@app.route('/requirement/<int:req_id>', methods=['GET'])
def get_requirement(req_id):
    result = db_backend.get_requirement_by_id(db_backend.get_supabase_connection(), req_id)
    return jsonify(result)

@app.route('/requirement/<int:rfp_id>', methods=['GET'])
def get_requirements_by_rfp(rfp_id):
    result = db_backend.get_requirements_by_rfp_id(db_backend.get_supabase_connection(), rfp_id)
    return jsonify(result)

@app.route('/requirement/<int:req_id>', methods=['PUT'])
def update_requirement(req_id):
    data = request.get_json()
    if not data:
        # Try to get form data if JSON is not available
        data = request.form

    req_text = data.get('req_text')

    if not req_text:
        return jsonify({"error": "Missing parameters"}), 400

    supabase = db_backend.get_supabase_connection()
    success = db_backend.update_requirement(supabase, req_id, req_text)

    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Failed to update requirement'}), 500

@app.route('/requirement/<int:req_id>', methods=['DELETE'])
def delete_requirement(req_id):
    result = db_backend.delete_requirement(db_backend.get_supabase_connection(), req_id)
    if result:
        return jsonify({"status": "success"})
    else:
        return jsonify({'status': 'failure'}), 500

#Proposal Functions
@app.route('/proposal', methods=['POST'])
def create_proposal():
    proposal = request.json
    result = db_backend.create_proposal(db_backend.get_supabase_connection(), proposal['prop_title'], proposal['prop_full_text'], proposal['rfp_id'])
    return jsonify(result)

@app.route('/proposal', methods=['GET'])
def get_proposals():
    print("Getting proposals")
    result = db_backend.get_proposals(db_backend.get_supabase_connection())
    #print(result)
    return jsonify({'proposals': result})

@app.route('/proposal/<int:prop_id>', methods=['GET'])
def get_proposal(prop_id):
    result = db_backend.get_proposal_by_id(db_backend.get_supabase_connection(), prop_id)
    return jsonify(result)

@app.route('/proposal/<int:rfp_id>', methods=['GET'])
def update_proposal(rfp_id):
    proposal = request.json
    result = db_backend.update_proposal(db_backend.get_supabase_connection(), rfp_id, proposal['prop_title'], proposal['prop_full_text'], proposal['rfp_id'])
    return jsonify(result)

@app.route('/proposal/<int:prop_id>', methods=['DELETE'])
def delete_proposal(prop_id):
    result = db_backend.delete_proposal(db_backend.get_supabase_connection(), prop_id)
    return jsonify(result)

#Answer Functions
@app.route('/answer', methods=['POST'])
def create_answer():
    answer = request.json
    result = db_backend.create_answer(db_backend.get_supabase_connection(), answer['seq_order'], answer['answer_text'], answer['approved'], answer['prop_id'], answer['req_id'], answer['potential_answers'])
    return jsonify(result)

@app.route('/answer', methods=['GET'])
def get_answers():
    result = db_backend.get_answers(db_backend.get_supabase_connection())
    return jsonify(result)

@app.route('/answer/<int:answer_id>', methods=['GET'])
def get_answer(answer_id):
    result = db_backend.get_answer_by_id(db_backend.get_supabase_connection(), answer_id)
    return jsonify(result)

@app.route('/answer/proposal/<int:prop_id>', methods=['GET'])
def get_answers_by_prop(prop_id):
    result = db_backend.get_answers_by_prop_id(db_backend.get_supabase_connection(), prop_id)
    print("Getting answers")
    print(result)
    return jsonify({'answers': result})

@app.route('/answer/<int:answer_id>', methods=['PUT'])
def update_answer(answer_id):
    answer = request.json
    result = db_backend.update_answer(db_backend.get_supabase_connection(), answer_id, answer['seq_order'], answer['answer_text'], answer['approved'], answer['prop_id'], answer['req_id'], answer['potential_answers'])
    return jsonify(result)

@app.route('/answer/<int:answer_id>', methods=['DELETE'])
def delete_answer(answer_id):
    result = db_backend.delete_answer(db_backend.get_supabase_connection(), answer_id)
    return jsonify(result)

#Lookup Functions
@app.route('/lookup/<int:look_id>', methods=['PUT'])
def update_lookup(look_id):
    data = request.get_json()
    if not data:
        # Try to get form data if JSON is not available
        data = request.form

    answer_text = data.get('answer_text')

    if not answer_text:
        return jsonify({"error": "Missing parameters"}), 400

    supabase = db_backend.get_supabase_connection()
    success = db_backend.update_lookup(supabase, look_id, answer_text)

    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Failed to update answer'}), 500
    
@app.route('/lookup/<int:look_id>', methods=['DELETE'])
def delete_lookup(look_id):
    result = db_backend.delete_lookup(db_backend.get_supabase_connection(), look_id)
    if result:
        return jsonify({"status": "success"})
    else:
        return jsonify({'status': 'failure'}), 500

if __name__ == '__main__':
    app.run(debug=True)