import os
import time
from threading import Thread
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'psych_quiz_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

game_state = {
    "timer_seconds": 60,
    "timer_running": False,
    "current_question": {"q": "Welcome! Waiting for organizer to start the quiz.", "pts": 0},
    "teams": {
        "Team Alpha": {"score": 0},
        "Team Beta": {"score": 0}
    }
}

QUESTIONS = {
    "easy": [
        {"q": "What term describes the tendency to search for information that matches existing beliefs?", "pts": 10},
        {"q": "Who is considered the founding father of psychoanalysis?", "pts": 10},
        {"q": "Which lobe of the brain is primarily responsible for visual processing?", "pts": 10}
    ]
}
q_indices = {"easy": 0}

HTML_CODE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Psychology Battle Arena</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; }
        h1 { margin-bottom: 20px; color: #2c3e50; }
        #timer { font-size: 1.5rem; font-weight: bold; background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        #question { font-size: 1.25rem; background: #007bff; color: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; min-height: 80px; display: flex; align-items: center; justify-content: center; }
        .dashboard { display: flex; justify-content: space-around; gap: 15px; margin-top: 20px; }
        .card { background: #f8f9fa; padding: 15px; border-radius: 8px; flex: 1; border: 1px solid #dee2e6; }
        button { background: #28a745; color: white; border: none; padding: 10px 15px; font-size: 1rem; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background: #218838; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Psychology Battle Arena</h1>
        <div id="timer">Timer: 01:00</div>
        <div id="question">Welcome! Waiting for organizer to start the quiz.</div>
        <div class="dashboard">
            <div class="card">
                <h3>Team Alpha</h3>
                <p id="team-alpha-score" style="font-size: 1.5rem; font-weight: bold;">0</p>
            </div>
            <div class="card">
                <h3>Team Beta</h3>
                <p id="team-beta-score" style="font-size: 1.5rem; font-weight: bold;">0</p>
            </div>
            <div class="card">
                <h3>Organizer Controls</h3>
                <button onclick="sendAction('toggle_timer')">Start/Pause Timer</button>
                <button onclick="sendAction('next_question')">Next Question</button>
            </div>
        </div>
    </div>

    <script>
        const socket = io();

        function sendAction(actionType) {
            socket.emit('host_action', { action: actionType });
        }

        socket.on('state_update', (state) => {
            if (state.timer_seconds !== undefined) {
                const mins = Math.floor(state.timer_seconds / 60);
                const secs = state.timer_seconds % 60;
                document.getElementById('timer').innerText = `Timer: ${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }
            if (state.current_question) {
                document.getElementById('question').innerText = `${state.current_question.q} — [${state.current_question.pts} Points]`;
            }
            if (state.teams) {
                document.getElementById('team-alpha-score').innerText = state.teams['Team Alpha'].score;
                document.getElementById('team-beta-score').innerText = state.teams['Team Beta'].score;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@socketio.on('connect')
def handle_connect():
    emit('state_update', game_state)

@socketio.on('host_action')
def handle_host_action(data):
    action = data.get('action')
    if action == 'toggle_timer':
        game_state['timer_running'] = not game_state['timer_running']
    elif action == 'next_question':
        q_type = "easy"
        q_list = QUESTIONS[q_type]
        idx = q_indices[q_type] % len(q_list)
        game_state['current_question'] = q_list[idx]
        q_indices[q_type] += 1
    socketio.emit('state_update', game_state)

def timer_background_task():
    while True:
        socketio.sleep(1)
        if game_state['timer_running'] and game_state['timer_seconds'] > 0:
            game_state['timer_seconds'] -= 1
            socketio.emit('state_update', game_state)
import os
if __name__ == '__main__':
        import eventlet
        import eventlet.wsgi
        socketio.start_background_task(timer_background_task)
eventlet.wsgi.server(eventlet.listen(('0.0.0.0', int(os.environ.get('PORT', 5000)))), app)
