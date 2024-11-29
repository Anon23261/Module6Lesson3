from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import logging
from flasgger import Swagger, swag_from
from marshmallow import Schema, fields, ValidationError

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialize Swagger
swagger = Swagger(app)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    join_date = db.Column(db.Date, nullable=False)

class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    type = db.Column(db.String(50), nullable=False)

# Define a schema for input validation
class MemberSchema(Schema):
    name = fields.String(required=True)
    email = fields.Email(required=True)
    join_date = fields.Date(required=True)

member_schema = MemberSchema()

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {str(e)}")
    return jsonify(error=str(e)), 500

@app.route('/')
def home():
    return jsonify(message="Welcome to the Flask API!"), 200

@app.route('/members', methods=['POST'])
@swag_from('add_member.yml')
def add_member():
    try:
        data = request.get_json()
        # Validate input
        member_schema.load(data)
        new_member = Member(name=data['name'], email=data['email'], join_date=data['join_date'])
        db.session.add(new_member)
        db.session.commit()
        logging.info(f"Added member {new_member.name} with email {new_member.email}")
        return jsonify({'message': 'New member added'}), 201
    except ValidationError as ve:
        logging.error(f"Validation error: {ve.messages}")
        return jsonify({'error': ve.messages}), 400
    except Exception as e:
        logging.error(f"Failed to add member: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add member'}), 500

@app.route('/members', methods=['GET'])
def get_members():
    members = Member.query.all()
    return jsonify([{'id': m.id, 'name': m.name, 'email': m.email, 'join_date': m.join_date} for m in members])

@app.route('/members/<int:id>', methods=['PUT'])
def update_member(id):
    try:
        data = request.get_json()
        member = Member.query.get_or_404(id)
        member.name = data.get('name', member.name)
        member.email = data.get('email', member.email)
        db.session.commit()
        logging.info(f"Updated member {member.name}")
        return jsonify({'message': 'Member updated'})
    except Exception as e:
        logging.error(f"Failed to update member: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update member'}), 500

@app.route('/members/<int:id>', methods=['DELETE'])
def delete_member(id):
    try:
        member = Member.query.get_or_404(id)
        db.session.delete(member)
        db.session.commit()
        logging.info(f"Deleted member {member.name}")
        return jsonify({'message': 'Member deleted'})
    except Exception as e:
        logging.error(f"Failed to delete member: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete member'}), 500

@app.route('/workout_sessions', methods=['POST'])
def add_workout_session():
    data = request.get_json()
    new_session = WorkoutSession(
        member_id=data['member_id'],
        date=data['date'],
        duration=data['duration'],
        type=data['type']
    )
    db.session.add(new_session)
    db.session.commit()
    return jsonify({'message': 'Workout session scheduled'}), 201

@app.route('/workout_sessions', methods=['GET'])
def get_workout_sessions():
    sessions = WorkoutSession.query.all()
    return jsonify([{
        'id': s.id,
        'member_id': s.member_id,
        'date': s.date,
        'duration': s.duration,
        'type': s.type
    } for s in sessions])

@app.route('/workout_sessions/member/<int:member_id>', methods=['GET'])
def get_member_workout_sessions(member_id):
    sessions = WorkoutSession.query.filter_by(member_id=member_id).all()
    return jsonify([{
        'id': s.id,
        'date': s.date,
        'duration': s.duration,
        'type': s.type
    } for s in sessions])

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
