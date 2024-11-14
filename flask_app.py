from flask import Flask, redirect, render_template, request, url_for, jsonify
import ai_backend
import db_backend
import file_processing
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

#Requirement Editing
@app.route('/requirement/editing')

#Proposal Writing
@app.route('/proposal/writing')
def proposal_writing():
    return render_template('proposal_writing_page.html')

#CRUD Operations

#RFP Functions
@app.route('/rfp', methods=['POST'])
def create_rfp():
    rfp = request.json
    result = db_backend.create_rfp(db_backend.get_supabase_connection, rfp['rfp_title'], rfp['rfp_description'], rfp['rfp_full_text'])
    return jsonify(result)

@app.route('/rfp', methods=['GET'])
def get_rfps():
    result = db_backend.get_rfps(db_backend.get_supabase_connection)
    return jsonify(result)

@app.route('/rfp/<int:rfp_id>', methods=['GET'])
def get_rfp(rfp_id):
    result = db_backend.get_rfp_by_id(db_backend.get_supabase_connection, rfp_id)
    return jsonify(result)

@app.route('/rfp/<int:rfp_id>', methods=['PUT'])
def update_rfp(rfp_id):
    rfp = request.json
    result = db_backend.update_rfp(db_backend.get_supabase_connection, rfp_id, rfp['rfp_title'], rfp['rfp_description'], rfp['rfp_full_text'], rfp["rfp_overall_context"])
    return jsonify(result)

@app.route('/rfp/<int:rfp_id>', methods=['DELETE'])
def delete_rfp(rfp_id):
    result = db_backend.delete_rfp(db_backend.get_supabase_connection, rfp_id)
    return jsonify(result)

#Requirement Functions
@app.route('/requirement', methods=['POST'])
def create_requirement():
    requirement = request.json
    result = db_backend.create_requirement(db_backend.get_supabase_connection, requirement['rfp_id'], requirement['req_text'], requirement['category'], requirement['chunk_extracted_from'])
    return jsonify(result)

@app.route('/requirement', methods=['GET'])
def get_requirements():
    result = db_backend.get_requirements(db_backend.get_supabase_connection)
    return jsonify(result)

@app.route('/requirement/<int:req_id>', methods=['GET'])
def get_requirement(req_id):
    result = db_backend.get_requirement_by_id(db_backend.get_supabase_connection, req_id)
    return jsonify(result)

@app.route('/requirement/<int:rfp_id>', methods=['GET'])
def get_requirements_by_rfp(rfp_id):
    result = db_backend.get_requirements_by_rfp_id(db_backend.get_supabase_connection, rfp_id)
    return jsonify(result)

@app.route('/requirement/<int:req_id>', methods=['PUT'])
def update_requirement(req_id):
    requirement = request.json
    result = db_backend.update_requirement(db_backend.get_supabase_connection, req_id, requirement['rfp_id'], requirement['req_text'], requirement['category'], requirement['chunk_extracted_from'])
    return jsonify(result)

@app.route('/requirement/<int:req_id>', methods=['DELETE'])
def delete_requirement(req_id):
    result = db_backend.delete_requirement(db_backend.get_supabase_connection, req_id)
    return jsonify(result)

#Proposal Functions
@app.route('/proposal', methods=['POST'])
def create_proposal():
    proposal = request.json
    result = db_backend.create_proposal(db_backend.get_supabase_connection, proposal['prop_title'], proposal['prop_full_text'], proposal['rfp_id'])
    return jsonify(result)

@app.route('/proposal', methods=['GET'])
def get_proposals():
    result = db_backend.get_proposals(db_backend.get_supabase_connection)
    return jsonify(result)

@app.route('/proposal/<int:prop_id>', methods=['GET'])
def get_proposal(prop_id):
    result = db_backend.get_proposal_by_id(db_backend.get_supabase_connection, prop_id)
    return jsonify(result)

@app.route('/proposal/<int:rfp_id>', methods=['GET'])
def update_proposal(rfp_id):
    proposal = request.json
    result = db_backend.update_proposal(db_backend.get_supabase_connection, rfp_id, proposal['prop_title'], proposal['prop_full_text'], proposal['rfp_id'])
    return jsonify(result)

@app.route('/proposal/<int:prop_id>', methods=['DELETE'])
def delete_proposal(prop_id):
    result = db_backend.delete_proposal(db_backend.get_supabase_connection, prop_id)
    return jsonify(result)

#Answer Functions
@app.route('/answer', methods=['POST'])
def create_answer():
    answer = request.json
    result = db_backend.create_answer(db_backend.get_supabase_connection, answer['seq_order'], answer['answer_text'], answer['approved'], answer['prop_id'], answer['req_id'], answer['potential_answers'])
    return jsonify(result)

@app.route('/answer', methods=['GET'])
def get_answers():
    result = db_backend.get_answers(db_backend.get_supabase_connection)
    return jsonify(result)

@app.route('/answer/<int:answer_id>', methods=['GET'])
def get_answer(answer_id):
    result = db_backend.get_answer_by_id(db_backend.get_supabase_connection, answer_id)
    return jsonify(result)

@app.route('/answer/<int:prop_id>', methods=['GET'])
def get_answers_by_prop(prop_id):
    result = db_backend.get_answers_by_prop_id(db_backend.get_supabase_connection, prop_id)
    return jsonify(result)

@app.route('/answer/<int:answer_id>', methods=['PUT'])
def update_answer(answer_id):
    answer = request.json
    result = db_backend.update_answer(db_backend.get_supabase_connection, answer_id, answer['seq_order'], answer['answer_text'], answer['approved'], answer['prop_id'], answer['req_id'], answer['potential_answers'])
    return jsonify(result)

@app.route('/answer/<int:answer_id>', methods=['DELETE'])
def delete_answer(answer_id):
    result = db_backend.delete_answer(db_backend.get_supabase_connection, answer_id)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)