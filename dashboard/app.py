#!/usr/bin/env python3
"""
Web dashboard for anchor research tool.
Provides real-time visualization of conversation progress and anchor responses.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from runner.conversation_state import ConversationState
from runner.scenario_loader import load_scenario
from runner.ai_client import ai_client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'anchor-research-dashboard'
socketio = SocketIO(app, cors_allowed_origins="*")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Global state management
active_sessions: Dict[str, ConversationState] = {}
session_data: Dict[str, Dict] = {}

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/scenarios')
def get_scenarios():
    """Get list of available scenarios."""
    scenarios_dir = Path(__file__).parent.parent / 'scenarios'
    scenarios = []
    
    for scenario_file in scenarios_dir.glob('*.md'):
        try:
            scenario = load_scenario(scenario_file)
            scenarios.append({
                'id': scenario_file.stem,
                'name': scenario.get('name', scenario_file.stem),
                'behavior_tested': scenario.get('behavior_tested', 'unknown'),
                'max_turns': scenario.get('max_user_turns', 0),
                'anchor_questions': scenario.get('anchor_question', [])
            })
        except Exception as e:
            print(f"Error loading scenario {scenario_file}: {e}")
    
    return jsonify(scenarios)

@app.route('/api/session/<session_id>')
def get_session_state(session_id: str):
    """Get current state of a conversation session."""
    if session_id not in session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(session_data[session_id])

@app.route('/api/session/<session_id>/start', methods=['POST'])
def start_session(session_id: str):
    """Start a new conversation session."""
    data = request.json
    scenario_id = data.get('scenario_id')
    model_name = data.get('model', 'gpt-4')
    branch_id = data.get('branch', 'baseline')
    
    try:
        # Load scenario
        scenario_path = Path(__file__).parent.parent / 'scenarios' / f'{scenario_id}.md'
        scenario = load_scenario(scenario_path)
        
        # Initialize session data
        session_data[session_id] = {
            'session_id': session_id,
            'scenario_id': scenario_id,
            'scenario_name': scenario.get('name', scenario_id),
            'model': model_name,
            'branch': branch_id,
            'behavior_tested': scenario.get('behavior_tested', 'unknown'),
            'max_turns': scenario.get('max_user_turns', 6),
            'current_turn': 0,
            'anchor_questions': scenario.get('anchor_question', []),
            'probes_per_point': scenario.get('probes_per_point', 4),
            'conversation': [],
            'anchor_responses': {},
            'metrics': {},
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        # Add initial system message
        turns = scenario.get('turns', [])
        if turns and turns[0].get('role') == 'system':
            session_data[session_id]['conversation'].append({
                'role': 'system',
                'content': turns[0]['content'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Broadcast update
        socketio.emit('session_updated', session_data[session_id], room=session_id)
        
        return jsonify({'success': True, 'session': session_data[session_id]})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/message', methods=['POST'])
def add_message(session_id: str):
    """Add a message to the conversation."""
    if session_id not in session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json
    role = data.get('role')
    content = data.get('content')
    
    if not role or not content:
        return jsonify({'error': 'Role and content required'}), 400
    
    # Add message to conversation
    message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    
    session_data[session_id]['conversation'].append(message)
    
    # Update turn counter for user messages
    if role == 'user':
        session_data[session_id]['current_turn'] += 1
    
    # Broadcast update
    socketio.emit('session_updated', session_data[session_id], room=session_id)
    
    return jsonify({'success': True})

@app.route('/api/session/<session_id>/anchor', methods=['POST'])
def add_anchor_response(session_id: str):
    """Add an anchor question response."""
    if session_id not in session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json
    turn = data.get('turn')
    question = data.get('question')
    response = data.get('response')
    
    if turn is None or not question or not response:
        return jsonify({'error': 'Turn, question, and response required'}), 400
    
    # Initialize turn data if needed
    if str(turn) not in session_data[session_id]['anchor_responses']:
        session_data[session_id]['anchor_responses'][str(turn)] = {}
    
    # Add response
    session_data[session_id]['anchor_responses'][str(turn)][question] = {
        'response': response,
        'timestamp': datetime.now().isoformat()
    }
    
    # Broadcast update
    socketio.emit('session_updated', session_data[session_id], room=session_id)
    
    return jsonify({'success': True})

@socketio.on('join_session')
def on_join_session(data):
    """Join a session room for real-time updates."""
    session_id = data['session_id']
    join_room(session_id)
    
    # Send current session state
    if session_id in session_data:
        emit('session_updated', session_data[session_id])

@app.route('/api/session/<session_id>/ai_response', methods=['POST'])
async def get_ai_response(session_id: str):
    """Get AI response for the current conversation state."""
    if session_id not in session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    session = session_data[session_id]
    
    try:
        # Build message history for AI
        messages = []
        for msg in session['conversation']:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Get AI response
        model = session['model']
        response = await ai_client.get_response(model, messages)
        
        # Add AI response to conversation
        ai_message = {
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        }
        session['conversation'].append(ai_message)
        
        # Broadcast update
        socketio.emit('session_updated', session, room=session_id)
        socketio.emit('ai_response', {'response': response}, room=session_id)
        
        return jsonify({'success': True, 'response': response})
        
    except Exception as e:
        error_msg = f"Error getting AI response: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

@app.route('/api/session/<session_id>/anchor_query', methods=['POST'])
async def query_anchor(session_id: str):
    """Query AI with an anchor question at current conversation state."""
    if session_id not in session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json
    query = data.get('query')
    turn = data.get('turn')
    
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    session = session_data[session_id]
    
    try:
        # Build message history up to the specified turn
        messages = []
        for i, msg in enumerate(session['conversation']):
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
            # Stop at the turn we want to query
            if msg['role'] == 'assistant' and len([m for m in messages if m['role'] == 'assistant']) >= turn:
                break
        
        # Add the anchor query
        messages.append({
            'role': 'user',
            'content': query
        })
        
        # Get AI response to anchor query
        model = session['model']
        response = await ai_client.get_response(model, messages, temperature=0.3)  # Lower temp for consistency
        
        return jsonify({'success': True, 'response': response})
        
    except Exception as e:
        error_msg = f"Error querying anchor: {str(e)}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnect."""
    print('Client disconnected')

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not openai_key and not anthropic_key:
        print("⚠️  Warning: No API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
    else:
        available_models = ai_client.get_available_models()
        print(f"✅ Available models: {', '.join(available_models)}")
    
    # Run the app
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
