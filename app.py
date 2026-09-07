import os
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'psych_quiz_secret_key'

# gunicorn + eventlet support for Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Game State
game_state = {
    "current_level": "Easy",
    "teams": {
        "Team Alpha": {"score": 0},
        "Team Beta": {"score": 0}
    },
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
        {"q": "Medium (20 pts): What cognitive bias causes high performers to underestimate their skills and low performers to overestimate theirs?", "pts": 20},
        {"q": "Medium (20 pts): What is the psychological phenomenon where people are less likely to offer help if others are present?", "pts": 20}
    ],
    "diff": [
        {"q": "Difficult (30 pts): What specific brain region, when damaged, results in fluent but nonsensical speech production (receptive aphasia)?", "pts": 30},
        {"q": "Difficult (30 pts): Which defense mechanism involves attributing one's own unacceptable feelings or impulses onto another person?", "pts": 30}
    ],
    "tie": [
        {"q": "🔥 TIE-BREAKER: Name the 5 stages of grief in the Kübler-Ross model in order.", "pts": 50}
    ]
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Psychology Team Quiz</title>
    <script src="https://cdn.socket.io/4.5.4/socketio.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; color: #333; }
        .container { max-width: 900px; margin: 0 auto; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .btn { padding: 10px 16px; border: none; background: #007bff; color: white; border-radius: 6px; cursor: pointer; font-weight: bold; margin: 4px; }
        .btn-danger { background: #dc3545; }
        .btn-success { background: #28a745; }
        .btn-warning { background: #ffc107; color: #212529; }
        .timer { font-size: 32px; font-weight: bold; color: #d9534f; text-align: center; }
        .score { font-size: 42px; font-weight: bold; margin: 10px 0; text-align: center; }
        .badge { background: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="text-align: center;">🧠 Virtual Psychology Quiz Show</h1>
        
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3>Current Stage: <span id="level" class="badge">Easy</span></h3>
                <div class="timer">⏱️ <span id="timer">40:00</span></div>
            </div>
        </div>

        <div class="grid">
            <div class="card" style="border-top: 5px solid #007bff;">
                <h2 style="text-align: center; color: #007bff;">Team Alpha</h2>
                <div id="score-Alpha" class="score" style="color: #007bff;">0</div>
            </div>
            <div class="card" style="border-top: 5px solid #28a745;">
                <h2 style="text-align: center; color: #28a745;">Team Beta</h2>
                <div id="score-Beta" class="score" style="color: #28a745;">0</div>
            </div>
        </div>

        <div class="card">
            <h2>Active Question</h2>
            <p id="question-text" style="font-size: 20px; font-weight: 500; line-height: 1.5; color: #444;"></p>
        </div>

        <!-- Organizer Control Room (Only visible if ?role=host in URL) -->
        <div id="control-panel" class="card" style="display: none; border: 2px solid #333; background: #fffde7;">
            <h2>🎛️ Organizer Control Room</h2>
            <p><strong>Timer & Stage Controls:</strong></p>
            <button class="btn btn-warning" onclick="sendAction('toggle_timer')">Start / Pause Timer</button>
            <button class="btn" onclick="sendAction('next_level')">Change Level Stage</button>
            <hr>
            <p><strong>Score Adjustments:</strong></p>
            <button class="btn" onclick="addPoint('Team Alpha', 10)">+10 Alpha</button>
            <button class="btn" onclick="addPoint('Team Alpha', -10)">-10 Alpha</button> | 
            <button class="btn btn-success" onclick="addPoint('Team Beta', 10)">+10 Beta</button>
            <button class="btn btn-success" onclick="addPoint('Team Beta', -10)">-10 Beta</button>
            <hr>
            <p><strong>Push Questions to Screen:</strong></p>
            <button class="btn" onclick="loadQuestion('easy')">Load Easy Q</button>
            <button class="btn" onclick="loadQuestion('med')">Load Medium Q</button>
            <button class="btn" onclick="loadQuestion('diff')">Load Difficult Q</button>
            <button class="btn btn-danger" onclick="loadQuestion('tie')">Load Tie-Breaker Q</button>
        </div>
    </div>

    <script>
        const socket = io();
        const urlParams = new URLSearchParams(window.location.search);
        const isHost = urlParams.get('role') === 'host';

        if (isHost) {
            document.getElementById('control-panel').style.display = 'block';
        }

        socket.on('state_update', (data) => {
            document.getElementById('level').innerText = data.current_level;
            document.getElementById('score-Alpha').innerText = data.teams['Team Alpha'].score;
            document.getElementById('score-Beta').innerText = data.teams['Team Beta'].score;
            document.getElementById('question-text').innerText = data.current_question.q;
            
            let minutes = Math.floor(data.timer_seconds / 60);
            let seconds = data.timer_seconds % 60;
            document.getElementById('timer').innerText = 
                `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        });

        function sendAction(action) { socket.emit('host_action', { action: action }); }
        function addPoint(team, pts) { socket.emit('host_action', { action: 'adjust_score', team: team, points: pts }); }
        function loadQuestion(type) { socket.emit('host_action', { action: 'load_q', type: type }); }
    </script>
</body>
</html>
"""

q_indices = {"easy": 0, "med": 0, "diff": 0, "tie": 0}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def handle_connect():
    emit('state_update', game_state)

@socketio.on('host_action')
def handle_action(data):
    act = data.get('action')
    
    if act == 'adjust_score':
        game_state['teams'][data['team']]['score'] += data['points']
        
    elif act == 'next_level':
        levels = ["Easy", "Medium", "Difficult", "Tie-Breaker"]
        curr_idx = levels.index(game_state['current_level'])
        game_state['current_level'] = levels[(curr_idx + 1) % len(levels)]
        
    elif act == 'load_q':
        q_type = data['type']
        q_list = QUESTIONS.get(q_type, [])
        if q_list:
            idx = q_indices[q_type] % len(q_list)
            game_state['current_question']['q'] = q_list[idx]['q']
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

socketio.start_background_task(timer_background_task)

if __name__ == '__main__':
    # Binds to Render environment port automatically
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)