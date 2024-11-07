from flask import Flask, redirect, render_template, request, url_for, jsonify
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

#Proposal Writing
@app.route('/proposal/writing')
def proposal_writing():
    return render_template('proposal_writing_page.html')

