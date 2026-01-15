from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, emit
import random, string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'party_secret_v5_share'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- OYUN KONFİGÜRASYONU ---
GAME_MODES = {
    'classic': {
        'label': 'Klasik Parti',
        'theme': 'theme-indigo',
        'questions': ["Kim?", "Kiminle?", "Nerede?", "Ne zaman?", "Ne yapıyor?", "Kim gördü?", "Ne dedi?"],
        'story_template': "{0}, {1} ile {2}'da, {3} {4}. Bunu gören {5}, '{6}' dedi."
    },
    'horror': {
        'label': 'Korku Evi 👻',
        'theme': 'theme-red',
        'questions': ["Hangi kurban?", "Kimin cesediyle?", "Hangi lanetli yerde?", "Gece saat kaçta?",
                      "Nasıl öldürüyor?", "Hangi yaratık gördü?", "Son sözü neydi?"],
        'story_template': "{0}, {1} cesediyle {2}'da, {3} {4}. {5} aniden belirdi ve fısıldadı: '{6}'"
    },
    'scifi': {
        'label': 'Cyberpunk 2077 🤖',
        'theme': 'theme-cyan',
        'questions': ["Hangi Cyborg?", "Hangi yapay zekayla?", "Hangi gezegende?", "Hangi yılda?",
                      "Hangi hack'i yapıyor?", "Hangi drone kaydetti?", "Sistem hatası neydi?"],
        'story_template': "{0}, {1} model android ile {2}'da, {3} yılında {4}. {5} verileri işledi ve kod çıktı: '{6}'"
    },
    'parallel': {
        'label': 'PARALEL EVREN 🌌',
        'theme': 'theme-parallel',
        'questions': ["Kim?", "Kiminle?", "Nerede?", "Ne zaman?", "Ne yapıyor?", "Kim gördü?", "Ne dedi?"],
        'story_template': "{0}, {1} ile {2}'da, {3} {4}. Olayı {5} izliyordu ve bağırdı: '{6}'"
    },
    'absurd': {
        'label': 'Tamamen Kaos 🌀',
        'theme': 'theme-purple',
        'questions': ["Ne dedi?", "Nerede?", "Kim?", "Ne zaman?", "Kiminle?", "Ne yapıyor?", "Kim gördü?"],
        'story_template': "Önce '{0}' dedi. Sonra {1}'da, {2}, {3} vakti {4} ile {5}. En son {6} şahit oldu."
    }
}

rooms = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Kim Kimle? - Ultimate</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;900&family=Plus+Jakarta+Sans:wght@300;700&display=swap" rel="stylesheet">
    <style>
        /* TEMALAR */
        :root { --primary: #6366f1; --bg-grad: radial-gradient(circle, rgba(99,102,241,0.15), transparent); }
        
        body.theme-red { --primary: #ef4444; --bg-grad: radial-gradient(circle, rgba(239,68,68,0.2), transparent); }
        body.theme-cyan { --primary: #06b6d4; --bg-grad: radial-gradient(circle, rgba(6,182,212,0.15), transparent); font-family: 'Courier New', monospace; }
        body.theme-purple { --primary: #d946ef; --bg-grad: radial-gradient(circle, rgba(217,70,239,0.2), transparent); }
        body.theme-parallel { --primary: #10b981; --bg-grad: repeating-linear-gradient(45deg, #022c22 0px, #022c22 10px, #064e3b 10px, #064e3b 20px); }

        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: #020617; color: #f8fafc; margin: 0; min-height: 100dvh;
            display: flex; align-items: center; justify-content: center; overflow-x: hidden;
            transition: background 0.5s ease;
        }

        #main-app { width: 100%; max-width: 600px; min-height: 100vh; display: flex; flex-direction: column; transition: all 0.3s ease; }
        @media (min-width: 640px) { #main-app { height: 90dvh; min-height: 600px; border-radius: 2rem; border: 1px solid rgba(255,255,255,0.1); background: rgba(15,23,42,0.9); backdrop-filter: blur(20px); } }

        .accent-text { color: var(--primary); }
        .accent-bg { background-color: var(--primary); }
        .bg-glow { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 150vw; height: 150vh; background: var(--bg-grad); z-index: -1; pointer-events: none; }
        
        .paper-sheet { background: #fff; color: #1e293b; border-radius: 12px; padding: 1.5rem; transform-origin: bottom center; }
        .paper-fly { animation: flyAway 0.8s forwards ease-in; }
        @keyframes flyAway { to { transform: translateY(-800px) rotate(-10deg); opacity: 0; } }
        
        .no-scrollbar::-webkit-scrollbar { display: none; }

        /* Custom Checkbox */
        .toggle-checkbox:checked { right: 0; border-color: #68D391; }
        .toggle-checkbox:checked + .toggle-label { background-color: #68D391; }
    </style>
</head>
<body class="theme-indigo">
    <div class="bg-glow"></div>

    <div id="main-app" class="p-6 relative overflow-y-auto no-scrollbar">

        <div id="ui-header" class="hidden flex justify-between items-center mb-6">
            <div>
                <span class="text-[8px] text-slate-500 font-bold tracking-widest block">ODA KODU</span>
                <span id="room-display" class="accent-text font-mono text-2xl font-black">----</span>
            </div>
            <div class="text-right">
                <span id="mode-badge" class="text-[9px] bg-white/10 px-2 py-1 rounded-md uppercase font-bold tracking-wider">Klasik</span>
            </div>
        </div>

        <div id="screen-login" class="space-y-8 mt-10">
            <div class="text-center">
                <h1 class="text-5xl font-black font-['Unbounded'] tracking-tighter bg-gradient-to-br from-white to-slate-600 bg-clip-text text-transparent">KİM KİMLE?</h1>
                <p class="text-slate-500 text-[10px] font-bold tracking-[0.4em] uppercase mt-2">V5 Social Edition</p>
            </div>
            <div class="flex justify-center gap-4 py-4">
                <div id="avatar-display" class="w-24 h-24 rounded-full bg-slate-800 border-4 border-transparent flex items-center justify-center text-4xl shadow-2xl transition-colors accent-border">🐱</div>
            </div>
            <div class="flex justify-center gap-2 overflow-x-auto pb-2">
                <button onclick="setAvatar('🐱')" class="p-2 text-2xl bg-white/5 rounded-lg hover:bg-white/10">🐱</button>
                <button onclick="setAvatar('👽')" class="p-2 text-2xl bg-white/5 rounded-lg hover:bg-white/10">👽</button>
                <button onclick="setAvatar('👹')" class="p-2 text-2xl bg-white/5 rounded-lg hover:bg-white/10">👹</button>
                <button onclick="setAvatar('🤖')" class="p-2 text-2xl bg-white/5 rounded-lg hover:bg-white/10">🤖</button>
            </div>
            <div class="space-y-3">
                <input type="text" id="in-name" placeholder="İsmin" class="w-full bg-slate-900 border border-slate-700 p-4 rounded-xl text-center font-bold text-lg focus:border-indigo-500 outline-none">
                <button onclick="createRoom()" class="w-full accent-bg p-4 rounded-xl font-black text-white shadow-lg">ODA KUR</button>
                <div class="flex gap-2">
                    <input type="text" id="in-room" placeholder="KOD" class="w-24 bg-slate-900 border border-slate-700 p-4 rounded-xl text-center font-mono font-bold uppercase">
                    <button onclick="joinRoom()" class="flex-1 bg-slate-800 p-4 rounded-xl font-bold hover:bg-slate-700">KATIL</button>
                </div>
            </div>
        </div>

        <div id="screen-lobby" class="hidden space-y-6">
            <div class="bg-white/5 p-4 rounded-2xl border border-white/5">
                <div class="flex justify-between items-center mb-3">
                    <span class="text-xs font-bold text-slate-400">OYUNCULAR</span>
                    <span id="player-count" class="accent-text font-bold text-xs">1/7</span>
                </div>
                <div id="list-players" class="space-y-2 max-h-[150px] overflow-y-auto no-scrollbar"></div>
            </div>

            <div id="host-controls" class="hidden space-y-4">
                <div class="bg-slate-900/80 p-5 rounded-2xl border border-dashed border-slate-700 space-y-4">
                    <p class="text-[10px] text-slate-400 font-black uppercase tracking-widest text-center">⚙️ HOST AYARLARI</p>
                    
                    <div class="grid grid-cols-2 gap-2">
                        <button onclick="setMode('classic')" id="btn-mode-classic" class="mode-btn p-2 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-600/50 text-xs font-bold">Klasik</button>
                        <button onclick="setMode('parallel')" id="btn-mode-parallel" class="mode-btn p-2 rounded-lg bg-slate-800 text-slate-400 border border-transparent text-xs font-bold">PARALEL 🌌</button>
                        <button onclick="setMode('horror')" id="btn-mode-horror" class="mode-btn p-2 rounded-lg bg-slate-800 text-slate-400 border border-transparent text-xs font-bold">Korku</button>
                        <button onclick="setMode('scifi')" id="btn-mode-scifi" class="mode-btn p-2 rounded-lg bg-slate-800 text-slate-400 border border-transparent text-xs font-bold">Cyberpunk</button>
                        <button onclick="setMode('absurd')" id="btn-mode-absurd" class="mode-btn p-2 rounded-lg bg-slate-800 text-slate-400 border border-transparent text-xs font-bold">Kaos</button>
                    </div>

                    <div class="flex items-center justify-between bg-black/20 p-3 rounded-lg">
                        <span class="text-xs font-bold text-slate-300">👤 Yazarları Göster</span>
                        <div class="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                            <input type="checkbox" name="toggle" id="chk-names" class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer border-slate-700" onchange="toggleSetting('show_author', this.checked)"/>
                            <label for="chk-names" class="toggle-label block overflow-hidden h-5 rounded-full bg-slate-700 cursor-pointer"></label>
                        </div>
                    </div>
                </div>
                <button onclick="startGame()" class="w-full accent-bg py-4 rounded-xl font-black text-lg shadow-xl shadow-indigo-500/20 hover:scale-[1.02] transition">OYUNU BAŞLAT</button>
            </div>
            
            <div id="guest-waiting" class="hidden text-center py-8">
                <p class="text-slate-400 text-sm">Host ayarları yapıyor...</p>
                <div class="mt-4 flex flex-col gap-2 items-center text-xs text-slate-500">
                    <span class="border border-white/5 p-2 rounded-lg">Mod: <span id="display-mode" class="accent-text font-bold">Klasik</span></span>
                    <span id="display-visibility" class="border border-white/5 p-2 rounded-lg opacity-50">İsimler Gizli 🕵️</span>
                </div>
            </div>
        </div>

        <div id="screen-game" class="hidden space-y-6">
            <div id="turn-active" class="hidden text-center space-y-6 py-6">
                <div>
                    <span id="step-badge" class="text-[9px] border border-white/20 px-2 py-1 rounded text-white/50">SORU 1</span>
                    <h2 id="q-text" class="text-3xl font-black mt-2 font-['Unbounded']">SORU</h2>
                </div>
                <div id="paper" class="paper-sheet text-left shadow-2xl relative">
                    <label class="text-[9px] font-bold text-slate-400 uppercase">CEVABIN:</label>
                    <input type="text" id="in-ans" class="w-full bg-slate-100 text-slate-900 text-lg font-bold p-2 mt-2 rounded border-b-2 border-slate-300 outline-none" autocomplete="off">
                    <button onclick="submitAns()" class="accent-bg text-white w-full py-3 mt-4 rounded-xl font-bold shadow-lg">GÖNDER</button>
                </div>
            </div>
            <div id="turn-wait" class="hidden text-center py-20">
                <div id="wait-avatar" class="text-6xl animate-bounce"></div>
                <p id="wait-text" class="text-slate-400 font-bold mt-4 animate-pulse">...</p>
            </div>
        </div>

        <div id="screen-parallel" class="hidden space-y-6">
            <div id="p-answering" class="hidden text-center space-y-6">
                <h2 id="p-q-text" class="text-3xl font-black font-['Unbounded'] text-green-400">SORU</h2>
                <div id="p-paper" class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-sm text-slate-400 mb-2">Cevabını yaz:</p>
                    <input type="text" id="in-p-ans" class="w-full bg-slate-900 text-white text-lg font-bold p-4 rounded-xl border border-slate-600 focus:border-green-500 outline-none mb-4" autocomplete="off">
                    <button onclick="submitParallelAns()" class="w-full bg-green-600 text-white py-4 rounded-xl font-black hover:bg-green-500">GÖNDER</button>
                </div>
            </div>
            <div id="p-waiting" class="hidden text-center py-20">
                <p class="text-2xl">⏳</p>
                <p class="text-slate-400 font-bold mt-2">Diğerleri bekleniyor...</p>
            </div>
            <div id="p-voting" class="hidden space-y-4">
                <div class="text-center">
                    <h3 class="text-xl font-bold text-white">OYLAMA</h3>
                    <p id="vote-info" class="text-xs text-slate-400">En iyi cevabı seç!</p>
                </div>
                <div id="vote-list" class="grid grid-cols-1 gap-3 max-h-[60vh] overflow-y-auto pb-10"></div>
            </div>
        </div>

        <div id="screen-final" class="hidden flex flex-col h-[90vh]">
            <div class="flex-1 overflow-y-auto no-scrollbar p-1 flex items-center justify-center">
                <div id="story-card" class="bg-gradient-to-b from-slate-900 to-black border border-white/10 p-8 rounded-[2rem] text-center shadow-2xl w-full">
                    <div class="mb-4">
                        <span class="text-[9px] accent-bg text-white px-2 py-1 rounded">HİKAYE SONUCU</span>
                    </div>
                    <p id="final-text" class="text-lg sm:text-2xl font-medium leading-relaxed font-serif text-slate-100 whitespace-pre-wrap"></p>
                    <div class="mt-6 text-[10px] text-slate-600 tracking-widest uppercase font-bold">kimkimle.com</div>
                </div>
            </div>

            <div class="mt-4 space-y-3 shrink-0">
                <p class="text-center text-[10px] text-slate-500 uppercase font-bold">Arkadaşlarınla Paylaş</p>
                
                <div class="grid grid-cols-4 gap-2">
                    <button onclick="shareWhatsapp()" class="bg-[#25D366] p-3 rounded-xl hover:brightness-110 flex items-center justify-center">
                        <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.017-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
                    </button>
                    <button onclick="shareTwitter()" class="bg-[#1DA1F2] p-3 rounded-xl hover:brightness-110 flex items-center justify-center">
                        <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/></svg>
                    </button>
                    <button onclick="saveImage()" class="bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-500 p-3 rounded-xl hover:brightness-110 flex items-center justify-center relative">
                        <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                        <span class="absolute -top-2 -right-2 bg-white text-black text-[8px] px-1 rounded font-bold">STORY</span>
                    </button>
                    <button onclick="saveImage()" class="bg-slate-700 p-3 rounded-xl hover:bg-slate-600 flex items-center justify-center">
                        <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                    </button>
                </div>

                <button onclick="location.reload()" class="w-full bg-white/5 py-4 rounded-xl font-bold text-xs text-slate-400 mt-2">
                    YENİ OYUN
                </button>
            </div>
        </div>

    </div>

    <script>
        const socket = io();
        let myAvatar = '🐱';
        let myRoom = '';
        let isHost = false;
        let currentMode = 'classic';

        // UI Helpers
        const $ = id => document.getElementById(id);
        const hide = id => $(id).classList.add('hidden');
        const show = id => $(id).classList.remove('hidden');

        function setAvatar(c) { myAvatar = c; $('avatar-display').innerText = c; }
        
        function createRoom() {
            const name = $('in-name').value;
            if(!name) return alert("İsim yaz!");
            socket.emit('create_room', {name, avatar: myAvatar});
            isHost = true;
        }
        function joinRoom() {
            const name = $('in-name').value;
            const room = $('in-room').value.toUpperCase();
            if(!name || !room) return alert("Eksik bilgi!");
            socket.emit('join_room', {name, room, avatar: myAvatar});
        }

        // --- AYARLAR ---
        function setMode(mode) {
            document.querySelectorAll('.mode-btn').forEach(b => {
                b.className = "mode-btn p-2 rounded-lg bg-slate-800 text-slate-400 border border-transparent text-xs font-bold";
            });
            $(`btn-mode-${mode}`).className = "mode-btn p-2 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-600/50 text-xs font-bold";
            socket.emit('update_settings', {room: myRoom, key: 'mode', val: mode});
        }

        function toggleSetting(key, val) {
            socket.emit('update_settings', {room: myRoom, key: key, val: val});
        }

        function startGame() { socket.emit('start_game', {room: myRoom}); }

        // --- SHARE LOGIC ---
        function getStoryText() {
            return document.getElementById('final-text').innerText;
        }

        function shareWhatsapp() {
            const txt = encodeURIComponent(`Kim Kimle oynadık, bak ne çıktı: \n\n"${getStoryText()}"\n\nSen de oyna!`);
            window.open(`https://wa.me/?text=${txt}`, '_blank');
        }

        function shareTwitter() {
            const txt = encodeURIComponent(`Kim Kimle? oyununda çıkan absürt hikaye: \n\n"${getStoryText()}"\n\n#KimKimle`);
            window.open(`https://twitter.com/intent/tweet?text=${txt}`, '_blank');
        }

        function saveImage() {
            const card = document.getElementById('story-card');
            // Geçici olarak scale artırıp kaliteyi yükseltelim
            html2canvas(card, { backgroundColor: null, scale: 3 }).then(canvas => {
                const link = document.createElement('a');
                link.download = `kim-kimle-${myRoom}.png`;
                link.href = canvas.toDataURL();
                link.click();
            });
        }

        // --- OYUN AKIŞI ---
        function submitAns() {
            const ans = $('in-ans').value;
            if(!ans) return;
            $('paper').classList.add('paper-fly');
            setTimeout(() => {
                socket.emit('submit_ans', {room: myRoom, ans});
                $('in-ans').value = '';
                $('paper').classList.remove('paper-fly');
            }, 600);
        }

        function submitParallelAns() {
            const ans = $('in-p-ans').value;
            if(!ans) return;
            hide('p-answering');
            show('p-waiting');
            socket.emit('submit_parallel_ans', {room: myRoom, ans});
            $('in-p-ans').value = '';
        }

        function castVote(candidateId) {
            hide('p-voting');
            show('p-waiting');
            socket.emit('cast_vote', {room: myRoom, candidate_id: candidateId});
        }

        // --- SOCKET LISTENERS ---
        socket.on('room_created', d => {
            myRoom = d.room;
            $('room-display').innerText = myRoom;
            hide('screen-login');
            show('screen-lobby');
            show('ui-header');
            isHost ? show('host-controls') : show('guest-waiting');
        });

        socket.on('update_list', list => {
            $('player-count').innerText = list.length + '/7';
            $('list-players').innerHTML = list.map(p => `
                <div class="flex items-center gap-3 bg-white/5 p-2 rounded-lg">
                    <span class="text-xl">${p.avatar}</span>
                    <span class="text-sm font-bold ${p.id === socket.id ? 'accent-text' : ''}">${p.name}</span>
                </div>
            `).join('');
        });

        socket.on('settings_changed', d => {
            // Ayarlar değiştiğinde UI güncelle
            if(d.key === 'mode') {
                currentMode = d.val;
                $('mode-badge').innerText = d.config.label;
                $('display-mode').innerText = d.config.label;
                document.body.className = d.config.theme;
            } else if (d.key === 'show_author') {
                const txt = d.val ? "İsimler Açık 👁️" : "İsimler Gizli 🕵️";
                $('display-visibility').innerText = txt;
                $('display-visibility').style.opacity = d.val ? "1" : "0.5";
            }
        });

        socket.on('game_start', mode => {
            hide('screen-lobby');
            mode === 'parallel' ? show('screen-parallel') : show('screen-game');
        });

        socket.on('turn_data', d => {
            if(socket.id === d.active_id) {
                show('turn-active'); hide('turn-wait');
                $('step-badge').innerText = `SORU ${d.step + 1}/7`;
                $('q-text').innerText = d.q;
            } else {
                hide('turn-active'); show('turn-wait');
                $('wait-avatar').innerText = d.active_avatar;
                $('wait-text').innerText = `${d.active_name} düşünüyor...`;
            }
        });

        socket.on('p_round_start', d => {
            hide('p-waiting'); hide('p-voting'); show('p-answering');
            $('p-q-text').innerText = d.q;
        });

        socket.on('p_vote_start', d => {
            hide('p-answering'); hide('p-waiting'); show('p-voting');
            const list = $('vote-list');
            list.innerHTML = '';
            
            if(d.is_tie) $('vote-info').innerHTML = "<span class='text-red-500 font-bold'>BERABERLİK! TEKRAR SEÇ!</span>";
            else $('vote-info').innerText = "En iyi cevabı seç!";

            d.candidates.forEach(c => {
                const btn = document.createElement('button');
                const isMine = c.owner_id === socket.id;
                
                // İsim gösterme mantığı (Server'dan name verisi gelmişse göster)
                const authorHTML = c.name ? `<span class="text-[10px] text-slate-400 font-normal">(${c.name})</span>` : '';
                
                btn.className = `w-full p-4 rounded-xl text-left font-bold text-sm flex justify-between items-center transition 
                    ${isMine ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-dashed border-slate-600' : 'bg-white/10 hover:bg-white/20 text-white border border-white/10'}`;
                
                btn.innerHTML = `<div><span>${c.text}</span> ${authorHTML}</div> ${isMine ? '<span class="text-[10px] uppercase tracking-wider">(SEN)</span>' : ''}`;
                
                if(!isMine) btn.onclick = () => castVote(c.owner_id);
                list.appendChild(btn);
            });
        });

        socket.on('game_over', d => {
            hide('screen-game'); hide('screen-parallel'); show('screen-final');
            $('final-text').innerText = d.story;
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# --- SOCKET ---

@socketio.on('create_room')
def create(d):
    code = ''.join(random.choices(string.ascii_uppercase, k=4))
    rooms[code] = {
        'players': [{'id': request.sid, 'name': d['name'], 'avatar': d['avatar']}],
        'answers': [],
        'step': 0,
        'settings': {'mode': 'classic', 'show_author': False}, # Default Gizli
        'parallel_state': {'phase': 'idle', 'round_answers': {}, 'round_votes': {}, 'candidates': []}
    }
    join_room(code)
    emit('room_created', {'room': code})
    emit('update_list', rooms[code]['players'], room=code)

@socketio.on('join_room')
def join(d):
    c = d['room']
    if c in rooms and len(rooms[c]['players']) < 7:
        rooms[c]['players'].append({'id': request.sid, 'name': d['name'], 'avatar': d['avatar']})
        join_room(c)
        emit('room_created', {'room': c})
        emit('update_list', rooms[c]['players'], room=c)
        
        # Mevcut ayarları gönder
        s = rooms[c]['settings']
        emit('settings_changed', {'key': 'mode', 'val': s['mode'], 'config': GAME_MODES[s['mode']]}, room=request.sid)
        emit('settings_changed', {'key': 'show_author', 'val': s['show_author']}, room=request.sid)
    else:
        emit('err', 'Oda yok veya dolu')

@socketio.on('update_settings')
def upd_set(d):
    c = d['room']
    if c in rooms:
        rooms[c]['settings'][d['key']] = d['val']
        # Herkese bildir
        payload = {'key': d['key'], 'val': d['val']}
        if d['key'] == 'mode':
            payload['config'] = GAME_MODES[d['val']]
        emit('settings_changed', payload, room=c)

@socketio.on('start_game')
def start(d):
    c = d['room']
    mode = rooms[c]['settings']['mode']
    emit('game_start', mode, room=c)
    if mode == 'parallel': start_parallel_round(c)
    else: send_classic_turn(c)

# --- CLASSIC ---
def send_classic_turn(c):
    r = rooms[c]
    questions = GAME_MODES[r['settings']['mode']]['questions']
    p_idx = r['step'] % len(r['players'])
    p = r['players'][p_idx]
    emit('turn_data', {
        'step': r['step'], 'q': questions[r['step']], 
        'active_id': p['id'], 'active_name': p['name'], 'active_avatar': p['avatar']
    }, room=c)

@socketio.on('submit_ans')
def classic_ans(d):
    c = d['room']
    rooms[c]['answers'].append(d['ans'])
    rooms[c]['step'] += 1
    if rooms[c]['step'] < 7: send_classic_turn(c)
    else: finish_game(c)

# --- PARALLEL ---
def start_parallel_round(c):
    r = rooms[c]
    r['parallel_state']['phase'] = 'answering'
    r['parallel_state']['round_answers'] = {}
    r['parallel_state']['round_votes'] = {}
    r['parallel_state']['candidates'] = []
    emit('p_round_start', {'step': r['step'], 'q': GAME_MODES[r['settings']['mode']]['questions'][r['step']]}, room=c)

@socketio.on('submit_parallel_ans')
def p_ans(d):
    c = d['room']
    r = rooms[c]
    r['parallel_state']['round_answers'][request.sid] = d['ans']
    if len(r['parallel_state']['round_answers']) >= len(r['players']):
        prepare_voting(c)

def prepare_voting(c, tie_candidates=None):
    r = rooms[c]
    r['parallel_state']['phase'] = 'voting'
    r['parallel_state']['round_votes'] = {}
    
    show_names = r['settings'].get('show_author', False)
    
    candidates = []
    if tie_candidates:
        candidates = tie_candidates
    else:
        # Tüm cevapları hazırla
        for pid, text in r['parallel_state']['round_answers'].items():
            # Yazar ismini bul
            author_name = next((p['name'] for p in r['players'] if p['id'] == pid), "???")
            cand_obj = {'owner_id': pid, 'text': text}
            # Eğer ayar açıksa ismi ekle, yoksa null
            if show_names: cand_obj['name'] = author_name
            else: cand_obj['name'] = None
            
            candidates.append(cand_obj)
            
    r['parallel_state']['candidates'] = candidates
    random.shuffle(candidates)
    emit('p_vote_start', {'candidates': candidates, 'is_tie': (tie_candidates is not None)}, room=c)

@socketio.on('cast_vote')
def p_vote(d):
    c = d['room']
    r = rooms[c]
    r['parallel_state']['round_votes'][request.sid] = d['candidate_id']
    if len(r['parallel_state']['round_votes']) >= len(r['players']):
        calculate_results(c)

def calculate_results(c):
    r = rooms[c]
    votes = r['parallel_state']['round_votes']
    candidates = r['parallel_state']['candidates']
    
    tally = {cand['owner_id']: 0 for cand in candidates}
    for target in votes.values():
        if target in tally: tally[target] += 1
            
    max_votes = max(tally.values()) if tally else 0
    winners = [cid for cid, count in tally.items() if count == max_votes]
    
    if len(winners) == 1:
        winner_text = r['parallel_state']['round_answers'][winners[0]]
        r['answers'].append(winner_text)
        r['step'] += 1
        if r['step'] < 7: start_parallel_round(c)
        else: finish_game(c)
    else:
        tied_cands = [cand for cand in candidates if cand['owner_id'] in winners]
        prepare_voting(c, tie_candidates=tied_cands)

def finish_game(c):
    r = rooms[c]
    ans = r['answers']
    # Eksik varsa doldur
    if len(ans) < 7: ans += ["..."] * (7 - len(ans))
    story = GAME_MODES[r['settings']['mode']]['story_template'].format(*ans)
    emit('game_over', {'story': story}, room=c)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
