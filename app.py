from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, emit
import random, string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'party_secret_v4_ultra'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- OYUN VERİSİ ---
rooms = {}
QUESTIONS = ["Kim?", "Kiminle?", "Nerede?", "Ne zaman?", "Ne yapıyor?", "Kim gördü?", "Ne dedi?"]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kim Kimle? - Ultimate Edition</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;900&family=Plus+Jakarta+Sans:wght@300;700&display=swap" rel="stylesheet">
    <style>
        :root { --neon-indigo: #6366f1; }
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: #020617; 
            color: #f8fafc; 
            overflow: hidden; 
            height: 100vh;
        }
        .title-font { font-family: 'Unbounded', cursive; }
        
        /* Kağıt Katlanma ve Uçma Animasyonu */
        .paper-fly {
            animation: foldAndFly 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
            pointer-events: none;
        }

        @keyframes foldAndFly {
            0% { transform: scaleY(1) translateY(0); opacity: 1; }
            30% { transform: scaleY(0.15) skewX(-15deg); opacity: 0.9; }
            100% { transform: scaleY(0) translateY(-800px) rotate(-20deg); opacity: 0; }
        }

        .glass-card { 
            background: rgba(15, 23, 42, 0.8); 
            backdrop-filter: blur(20px); 
            border: 1px solid rgba(255,255,255,0.1);
        }

        .poster-bg {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        }

        /* Yüzen Emojiler */
        .float-emoji {
            position: absolute;
            animation: floatUp 2s ease-out forwards;
            pointer-events: none;
            z-index: 100;
        }
        @keyframes floatUp {
            0% { transform: translateY(0) scale(1); opacity: 1; }
            100% { transform: translateY(-400px) scale(2); opacity: 0; }
        }
    </style>
</head>
<body class="flex items-center justify-center p-4">

    <div id="main-app" class="max-w-md w-full glass-card rounded-[2.5rem] p-8 relative shadow-2xl overflow-hidden">
        
        <!-- ÜST PANEL -->
        <div id="ui-header" class="hidden flex justify-between items-center mb-6">
            <div class="bg-slate-900/50 px-3 py-1 rounded-full text-[10px] font-bold text-indigo-400 border border-indigo-500/20">
                ODA: <span id="room-display">----</span>
            </div>
            <div id="role-display" class="bg-indigo-500/10 text-indigo-300 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">
                OYUNCU
            </div>
        </div>

        <!-- 1. GİRİŞ EKRANI -->
        <div id="screen-login" class="space-y-8">
            <div class="text-center">
                <h1 class="text-5xl title-font font-black tracking-tighter bg-gradient-to-b from-white to-slate-500 bg-clip-text text-transparent leading-tight">KİM<br>KİMLE?</h1>
                <p class="text-[10px] text-slate-500 uppercase tracking-[0.4em] mt-2">Paper & Sound Edition</p>
            </div>
            <div class="space-y-3">
                <input type="text" id="in-name" placeholder="Takma Adın" class="w-full p-4 rounded-2xl bg-slate-900 border border-slate-800 outline-none focus:border-indigo-500 transition-all">
                <button onclick="createRoom()" class="w-full bg-indigo-600 p-4 rounded-2xl font-black shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition">YENİ ODA</button>
                <div class="relative py-2 text-center text-[10px] text-slate-600 font-bold uppercase tracking-widest">VEYA</div>
                <input type="text" id="in-room" placeholder="ODA KODU" class="w-full p-4 rounded-2xl bg-slate-900 border border-slate-800 text-center font-mono text-2xl tracking-widest outline-none">
                <div class="grid grid-cols-2 gap-3">
                    <button onclick="joinRoom(false)" class="bg-slate-800 p-4 rounded-2xl font-bold hover:bg-slate-700">OYNA</button>
                    <button onclick="joinRoom(true)" class="border border-slate-800 p-4 rounded-2xl font-bold hover:bg-white/5">İZLE</button>
                </div>
            </div>
        </div>

        <!-- 2. LOBİ EKRANI -->
        <div id="screen-lobby" class="hidden space-y-6">
            <div id="host-panel" class="hidden p-4 bg-amber-500/10 rounded-2xl border border-amber-500/20">
                <p class="text-[10px] font-black text-amber-500 uppercase mb-2">İzleyici İstekleri</p>
                <div id="req-container" class="space-y-2"></div>
            </div>

            <div class="space-y-2">
                <p class="text-[10px] font-black text-slate-500 uppercase tracking-widest">Oyuncular</p>
                <div id="list-players" class="space-y-2"></div>
            </div>

            <div id="spec-live-box" class="hidden p-4 bg-emerald-500/5 rounded-2xl border border-emerald-500/10">
                <p class="text-[10px] font-black text-emerald-500 uppercase mb-2">CANLI YAYIN (GİZLİ)</p>
                <div id="live-feed" class="text-xs italic text-slate-400 space-y-1 max-h-32 overflow-y-auto">Henüz yazılmadı...</div>
            </div>

            <div class="flex justify-center gap-4 py-2">
                <button onclick="sendEmoji('😂')" class="text-2xl hover:scale-125 transition">😂</button>
                <button onclick="sendEmoji('🔥')" class="text-2xl hover:scale-125 transition">🔥</button>
                <button onclick="sendEmoji('💀')" class="text-2xl hover:scale-125 transition">💀</button>
                <button onclick="sendEmoji('❤️')" class="text-2xl hover:scale-125 transition">❤️</button>
            </div>

            <button id="btn-start" onclick="startGame()" class="hidden w-full bg-indigo-600 p-4 rounded-2xl font-black shadow-xl shadow-indigo-500/30">OYUNU BAŞLAT</button>
        </div>

        <!-- 3. OYUN EKRANI -->
        <div id="screen-game" class="hidden space-y-12 py-10">
            <div id="turn-active" class="hidden space-y-6 text-center">
                <div class="space-y-1">
                    <p id="q-count" class="text-indigo-500 text-[10px] font-black uppercase tracking-widest">Soru 1/7</p>
                    <h2 id="q-label" class="text-3xl font-black title-font">Kim?</h2>
                </div>
                <div id="paper-container" class="space-y-4">
                    <input type="text" id="in-ans" placeholder="Bir isim yaz..." class="w-full p-6 rounded-[2.5rem] bg-slate-900 border-2 border-indigo-500 text-xl outline-none shadow-2xl shadow-indigo-500/20">
                    <button onclick="handlePaperSubmit()" class="w-full bg-indigo-600 p-4 rounded-2xl font-black shadow-lg">GÖNDER</button>
                </div>
            </div>

            <div id="turn-wait" class="text-center py-10 space-y-4">
                <div class="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p id="wait-msg" class="text-slate-400 italic">Arkadaşın kağıdı dolduruyor...</p>
            </div>
        </div>

        <!-- 4. FİNAL POSTER EKRANI -->
        <div id="screen-final" class="hidden space-y-6">
            <div id="poster-capture" class="poster-bg p-12 rounded-[3rem] border border-white/10 text-center space-y-8 shadow-2xl relative overflow-hidden">
                <div class="absolute inset-0 opacity-10 pointer-events-none" style="background-image: radial-gradient(circle, #fff 1px, transparent 1px); background-size: 20px 20px;"></div>
                <h3 class="title-font text-[10px] font-black text-indigo-400 tracking-[0.5em] uppercase">Efsane Hikaye</h3>
                <p id="final-story" class="text-2xl font-bold italic leading-relaxed text-white drop-shadow-md"></p>
                <div class="text-[8px] text-white/30 font-bold uppercase tracking-widest border-t border-white/5 pt-4">Kim Kimle • Dijital Hatıra</div>
            </div>

            <div class="grid grid-cols-2 gap-3">
                <button onclick="downloadPoster()" class="bg-white text-black p-4 rounded-2xl font-bold flex items-center justify-center gap-2">İNDİR</button>
                <button onclick="shareWhatsApp()" class="bg-emerald-600 p-4 rounded-2xl font-bold flex items-center justify-center gap-2 text-white">WHATSAPP</button>
            </div>
            <button onclick="location.reload()" class="w-full text-slate-500 text-[10px] font-bold uppercase tracking-widest">YENİDEN OYNA</button>
        </div>
    </div>

    <script>
        const socket = io();
        let myRoom = "", myRole = "player", isHost = false;

        // --- SES MOTORU (Web Audio API) ---
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        function playTone(freq, type, duration, vol=0.1) {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
            gain.gain.setValueAtTime(vol, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
            osc.connect(gain); gain.connect(audioCtx.destination);
            osc.start(); osc.stop(audioCtx.currentTime + duration);
        }

        const SFX = {
            ding: () => { playTone(523, 'sine', 0.2); setTimeout(() => playTone(659, 'sine', 0.2), 150); },
            paper: () => { playTone(200, 'triangle', 0.4, 0.05); playTone(150, 'sawtooth', 0.1, 0.02); },
            tada: () => { [440, 554, 659, 880].forEach((f, i) => setTimeout(() => playTone(f, 'sine', 0.5), i * 150)); }
        };

        // --- GİZLİ ÇIKIŞ KISAYOLU ---
        let keysPressed = {};
        window.addEventListener('keydown', (e) => {
            keysPressed[e.key.toLowerCase()] = true;
            if (keysPressed['control'] && keysPressed['alt'] && keysPressed['shift'] && keysPressed['f12'] && keysPressed['f11']) {
                document.body.innerHTML = "<div style='background:#000; color:#fff; height:100vh; display:flex; align-items:center; justify-content:center; font-family:sans-serif;'>Oturum Güvenli Şekilde Kapatıldı.</div>";
            }
        });
        window.addEventListener('keyup', (e) => { delete keysPressed[e.key.toLowerCase()]; });

        // --- FONKSİYONLAR ---
        function createRoom() {
            const n = document.getElementById('in-name').value;
            if(!n) return;
            socket.emit('create_room', {name: n});
            isHost = true;
        }

        function joinRoom(spec) {
            const n = document.getElementById('in-name').value;
            const c = document.getElementById('in-room').value.toUpperCase().trim();
            if(!n || !c) return;
            if(spec) socket.emit('req_spec', {name: n, room: c});
            else socket.emit('join_room', {name: n, room: c});
        }

        function handlePaperSubmit() {
            const val = document.getElementById('in-ans').value;
            if(!val) return;
            
            SFX.paper();
            const container = document.getElementById('paper-container');
            container.classList.add('paper-fly');

            setTimeout(() => {
                socket.emit('submit_ans', {room: myRoom, answer: val});
                document.getElementById('in-ans').value = "";
                container.classList.remove('paper-fly');
            }, 800);
        }

        function startGame() { socket.emit('start_game', {room: myRoom}); }
        function sendEmoji(e) { socket.emit('emoji', {room: myRoom, emoji: e}); }

        function downloadPoster() {
            html2canvas(document.querySelector("#poster-capture")).then(canvas => {
                const a = document.createElement('a');
                a.download = "KimKimle_Hikaye.png";
                a.href = canvas.toDataURL();
                a.click();
            });
        }

        function shareWhatsApp() {
            const t = encodeURIComponent("Kim Kimle oynadık, efsane bir hikaye çıktı! Hemen bak: " + window.location.href);
            window.open(`https://wa.me/?text=${t}`, '_blank');
        }

        // --- SOCKET EVENTLERİ ---
        socket.on('room_ready', d => {
            myRoom = d.room; myRole = d.role;
            document.getElementById('screen-login').classList.add('hidden');
            document.getElementById('screen-lobby').classList.remove('hidden');
            document.getElementById('ui-header').classList.remove('hidden');
            document.getElementById('room-display').innerText = myRoom;
            document.getElementById('role-display').innerText = myRole === 'izleyici' ? 'İZLEYİCİ' : 'OYUNCU';
            if(myRole === 'izleyici') document.getElementById('spec-live-box').classList.remove('hidden');
            if(isHost) document.getElementById('btn-start').classList.remove('hidden');
        });

        socket.on('spec_request', d => {
            if(!isHost) return;
            document.getElementById('host-panel').classList.remove('hidden');
            const div = document.getElementById('req-container');
            div.innerHTML += `<div class="flex justify-between items-center bg-white/5 p-2 rounded-xl text-xs">
                <span>👁️ ${d.name}</span>
                <button onclick="socket.emit('acc_spec', {room: myRoom, sid:'${d.sid}', name:'${d.name}'})" class="bg-indigo-600 px-3 py-1 rounded-lg font-bold">ONAYLA</button>
            </div>`;
        });

        socket.on('update_list', (p, s) => {
            document.getElementById('list-players').innerHTML = 
                p.map(n => `<div class="p-3 bg-white/5 rounded-2xl border border-white/5 flex justify-between text-sm"><span>👤 ${n}</span><span class="text-[8px] text-indigo-400 font-bold uppercase">OYUNCU</span></div>`).join('') +
                s.map(n => `<div class="p-3 bg-white/5 rounded-2xl border border-white/5 opacity-50 flex justify-between text-sm"><span>👁️ ${n}</span><span class="text-[8px] text-slate-400 font-bold uppercase">İZLEYİCİ</span></div>`).join('');
        });

        socket.on('next_step', d => {
            document.getElementById('screen-lobby').classList.add('hidden');
            document.getElementById('screen-game').classList.remove('hidden');
            if(socket.id === d.active_id) {
                SFX.ding();
                document.getElementById('turn-active').classList.remove('hidden');
                document.getElementById('turn-wait').classList.add('hidden');
                document.getElementById('q-label').innerText = d.question;
                document.getElementById('q-count').innerText = `SORU ${d.step + 1}/7`;
            } else {
                document.getElementById('turn-active').classList.add('hidden');
                document.getElementById('turn-wait').classList.remove('hidden');
                document.getElementById('wait-msg').innerText = `${d.active_name} kağıdı dolduruyor...`;
            }
        });

        socket.on('live_feed', d => {
            if(myRole !== 'izleyici') return;
            const feed = document.getElementById('live-feed');
            if(feed.innerText.includes('Henüz')) feed.innerHTML = "";
            feed.innerHTML += `<div><b>${d.q}:</b> ${d.a}</div>`;
            feed.scrollTop = feed.scrollHeight;
        });

        socket.on('finish', d => {
            SFX.tada();
            document.getElementById('screen-game').classList.add('hidden');
            document.getElementById('screen-final').classList.remove('hidden');
            document.getElementById('final-story').innerText = d.story;
        });

        socket.on('on_emoji', e => {
            const div = document.createElement('div');
            div.className = 'float-emoji text-4xl';
            div.style.left = Math.random() * 80 + 10 + "%";
            div.style.bottom = "20%";
            div.innerText = e;
            document.body.appendChild(div);
            setTimeout(() => div.remove(), 2000);
        });

        socket.on('err', m => alert(m));
    </script>
</body>
</html>
"""

# --- SERVER MANTIGI ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('create_room')
def on_create(d):
    code = ''.join(random.choices(string.ascii_uppercase, k=4))
    rooms[code] = {
        'host': request.sid, 
        'players': [{'n': d['name'], 'id': request.sid}], 
        'specs': [], 
        'ans': [], 
        'step': 0
    }
    join_room(code)
    emit('room_ready', {'room': code, 'role': 'oyuncu'})
    update_list(code)

@socketio.on('join_room')
def on_join(d):
    c = d['room']
    if c in rooms and len(rooms[c]['players']) < 7:
        rooms[c]['players'].append({'n': d['name'], 'id': request.sid})
        join_room(c)
        emit('room_ready', {'room': c, 'role': 'oyuncu'})
        update_list(c)
    else: 
        emit('err', 'Oda dolu veya bulunamadı!')

@socketio.on('req_spec')
def on_req_spec(d):
    c = d['room']
    if c in rooms:
        emit('spec_request', {'name': d['name'], 'sid': request.sid}, room=rooms[c]['host'])
    else:
        emit('err', 'İzlenecek oda bulunamadı!')

@socketio.on('acc_spec')
def on_acc_spec(d):
    c = d['room']
    if c in rooms and request.sid == rooms[c]['host']:
        rooms[c]['specs'].append({'n': d['name'], 'id': d['sid']})
        emit('room_ready', {'room': c, 'role': 'izleyici'}, room=d['sid'])
        socketio.server.enter_room(d['sid'], c)
        update_list(c)

def update_list(c):
    if c in rooms:
        p = [x['n'] for x in rooms[c]['players']]
        s = [x['n'] for x in rooms[c]['specs']]
        emit('update_list', (p, s), room=c)

@socketio.on('start_game')
def on_start(d):
    c = d['room']
    if c in rooms and request.sid == rooms[c]['host']:
        send_step(c)

def send_step(c):
    r = rooms[c]
    p = r['players'][r['step'] % len(r['players'])]
    emit('next_step', {
        'step': r['step'], 
        'question': QUESTIONS[r['step']], 
        'active_id': p['id'], 
        'active_name': p['n']
    }, room=c)

@socketio.on('submit_ans')
def on_submit(d):
    c = d['room']
    if c in rooms:
        r = rooms[c]
        r['ans'].append(d['answer'])
        emit('live_feed', {'q': QUESTIONS[r['step']], 'a': d['answer']}, room=c)
        r['step'] += 1
        if r['step'] < 7: 
            send_step(c)
        else:
            a = r['ans']
            story = f"{a[0]}, {a[1]} ile {a[2]}'da, {a[3]} {a[4]}. Bunu gören {a[5]}, '{a[6]}' dedi."
            emit('finish', {'story': story}, room=c)

@socketio.on('emoji')
def on_emoji(d):
    emit('on_emoji', d['emoji'], room=d['room'])

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
