import os
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask( __name__)
app.config['SECRET_KEY'] = 'psych_quiz_secret_key'

socketio = SocketIO(app, cors_allowed_origins="*")

HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
    <title>Quiz App</title>
</head>
<body>
    <h1>Quiz Game UI</h1>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_CODE)
game_state = {
    "timer_seconds": 40 * 60,
    "timer_running": False,
    "current_question": {"q": "Welcome! Waiting for organizer to start the quiz.", "pts": 0}
}

QUESTIONS = {
    "easy": [
        {"q": "Easy (10 pts): What term describes the tendency to search for information that matches existing beliefs?", "pts": 10},
        {"q": "Easy (10 pts): Who is considered the founding father of psychoanalysis?", "pts": 10},
        {"q": "Easy (10 pts): Which lobe of the brain is primarily responsible for visual processing?", "pts": 10}
    ],
    "med": [
        {"q": "Medium (20 pts): Which experiment tested obedience to authority using fake electric shocks?", "pts": 20},
        {"q": "Medium (20 pts): What cognitive bias causes high performers to underestimate their skills and low performers to overestimate?", "pts": 20},
        {"q": "Medium (20 pts): What is the psychological phenomenon where people are less likely to offer help if others are present?", "pts": 20}
    ],
    "diff": [
        {"q": "Difficult (30 pts): What specific brain region, when damaged, results in fluent but nonsensical speech production?", "pts": 30},
        {"q": "Difficult (30 pts): Which defense mechanism involves attributing one's own unacceptable feelings onto another?", "pts": 30}
    ],
    "tie": [
        {"q": "TIE-BREAKER: Name the 5 stages of grief in the Kübler-Ross model in order.", "pts": 50}
    ]
}

q_indices = {"easy": 0, "med": 0, "diff": 0, "tie": 0}

@socketio.on('connect')
def handle_connect():
    emit('state_update', game_state)

@socketio.on('host_action')
def handle_action(data):
    act = data.get('action')
    
    if act == 'adjust_score':
        team = data.get('team')
        points = data.get('points', 0)
        if team in game_state['teams']:
            game_state['teams'][team]['score'] += points
            
    elif act == 'next_level':
        # Aligned key names with QUESTIONS dictionary
        levels = ["easy", "med", "diff", "tie"]
        curr_idx = levels.index(game_state['current_level']) if game_state['current_level'] in levels else 0
        game_state['current_level'] = levels[(curr_idx + 1) % len(levels)]
        
    elif act == 'load_q':
        q_type = data.get('type')
        q_list = QUESTIONS.get(q_type, [])
        if q_list:
            idx = q_indices[q_type] % len(q_list)
            # Correctly updates both question text AND points
            game_state['current_question']['q'] = q_list[idx]['q']
            game_state['current_question']['pts'] = q_list[idx]['pts']
            q_indices[q_type] += 1

    elif act == 'toggle_timer':
        game_state['timer_running'] = not game_state['timer_running']

    socketio.emit('state_update', game_state)

def timer_background_task():
    while True:
        socketio.sleep(1)
        if game_state['timer_running'] and game_state['timer_seconds'] > 0:
            game_state['timer_seconds'] -= 1
            socketio.emit('state_update', game_state)

if __name__ == '__main__':
    # Start the timer task inside the main entry point to prevent double execution
    socketio.start_background_task(timer_background_task)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
