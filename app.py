import os
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'psych_quiz_secret_key'

socketio = SocketIO(app, cors_allowed_origins="*")

HTML_CODE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Psychology Quiz Game</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
       body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 20px; }
        .timer-box { font-size: 24px; font-weight: bold; text-align: center; background: #eef2f7; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
        .question-box { background: #3498db; color: white; padding: 25px; border-radius: 8px; font-size: 20px; text-align: center; margin-bottom: 25px; min-height: 80px; display: flex; align-items: center; justify-content: center; }
        .scoreboard { display: flex; justify-content: space-around; margin-bottom: 20px; }
        .card { background: #fafafa; border: 2px solid #e0e0e0; border-radius: 8px; padding: 15px; width: 40%; text-align: center; }
        .card h3 { margin: 0 0 10px 0; }
        .score { font-size: 28px; font-weight: bold; color: #27ae60; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Psychology Battle Arena</h1>
        <div class="timer-box" id="timer">Timer: --:--</div>
        
        <div class="question-box" id="question">
            Loading question...
        </div>

        <div class="scoreboard">
            <div class="card">
                <h3 id="team-alpha-name">Team Alpha</h3>
                <div class="score" id="team-alpha-score">0</div>
            </div>
            <div class="card">
                <h3 id="team-beta-name">Team Beta</h3>
                <div class="score" id="team-beta-score">0</div>
            </div>
       <div style="text-align: center; margin-top: 20px;">
            <button onclick="socket.emit('host_action', {'action': 'toggle_timer'})" style="padding: 10px 20px; font-size: 16px; cursor: pointer; margin-right: 10px;">Start/Pause Timer</button>
            <button onclick="socket.emit('host_action', {'action': 'load_q', 'type': 'easy'})" style="padding: 10px 20px; font-size: 16px; cursor: pointer;">Next Question</button>
        </div>
        </div>
    <script>
        const socket = io();

        socket.on('connect', () => {
            console.log('Connected to quiz server!');
        });

        socket.on('state_update', (state) => {
            if (state.current_question) {
                document.getElementById('question').innerText = state.current_question.q;
            }
            if (state.teams) {
                if (state.teams['Team Alpha']) {
                    document.getElementById('team-alpha-score').innerText = state.teams['Team Alpha'].score;
                }
                if (state.teams['Team Beta']) {
                    document.getElementById('team-beta-score').innerText = state.teams['Team Beta'].score;
                }
            }
            if (state.timer_seconds !== undefined) {
                let mins = Math.floor(state.timer_seconds / 60);
                let secs = state.timer_seconds % 60;
                document.getElementById('timer').innerText = `Timer: ${mins}:${secs < 10 ? '0' : ''}${secs}`;
            }
        });
    </script>
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
    socketio.start_background_task(timer_background_task)
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

if __name__ == "__main__":
    # Start the timer task inside the main entry point to prevent double execution
    socketio.start_background_task(timer_background_task)
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
