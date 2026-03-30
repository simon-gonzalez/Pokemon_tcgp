// ═══ Pokemon TCG Pocket Simulator - Frontend ═══

let deckData = {};

// ── Navigation ──────────────────────────────────────────────────
document.querySelectorAll('#sidebar li').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('#sidebar li').forEach(i => i.classList.remove('active'));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        item.classList.add('active');
        document.getElementById('page-' + item.dataset.page).classList.add('active');
    });
});

// ── Init ────────────────────────────────────────────────────────
async function init() {
    try {
        const res = await fetch('/api/decks');
        deckData = await res.json();
        populateSelectors();
        renderDecksPage();
        loadLogs();
    } catch (e) {
        console.error('Failed to load decks:', e);
    }
}

function populateSelectors() {
    const names = Object.keys(deckData);
    ['battle-deck1', 'battle-deck2', 'replay-deck1', 'replay-deck2'].forEach(id => {
        const sel = document.getElementById(id);
        sel.innerHTML = '';
        names.forEach((name, i) => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            if (id.includes('2') && i === 1) opt.selected = true;
            sel.appendChild(opt);
        });
    });

    // Deck info on battle page
    ['battle-deck1', 'battle-deck2'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => updateDeckInfo(id));
        updateDeckInfo(id);
    });
}

function updateDeckInfo(selectId) {
    const name = document.getElementById(selectId).value;
    const deck = deckData[name];
    if (!deck) return;
    const infoId = selectId + '-info';
    document.getElementById(infoId).innerHTML = `
        <span>${deck.energy_types.join(', ')}</span> ·
        <span>${deck.pokemon_count} Pokemon</span> ·
        <span>${deck.ex_pokemon.join(', ')}</span>
    `;
}

// ── Dashboard: Matchup Table ────────────────────────────────────
document.getElementById('btn-run-matchups').addEventListener('click', runMatchups);

async function runMatchups() {
    const btn = document.getElementById('btn-run-matchups');
    const games = parseInt(document.getElementById('dash-games').value);

    btn.disabled = true;
    show('dash-loading');
    hide('dash-rankings');
    hide('dash-matrix');

    try {
        const res = await fetch('/api/matchup-table', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ games }),
        });
        const data = await res.json();
        renderRankings(data.rankings);
        renderMatrix(data.deck_names, data.matrix, data.games_per_matchup);
    } catch (e) {
        alert('Error running simulation: ' + e.message);
    }

    hide('dash-loading');
    btn.disabled = false;
}

function renderRankings(rankings) {
    const container = document.getElementById('rankings-cards');
    container.innerHTML = rankings.map((r, i) => `
        <div class="rank-card rank-${i + 1}">
            <div class="rank-badge">#${i + 1}</div>
            <h4>${r.name}</h4>
            <div class="rank-wr">${r.win_rate}%</div>
            <div class="rank-record">${r.wins}W / ${r.games - r.wins}L</div>
        </div>
    `).join('');
    show('dash-rankings');
}

function renderMatrix(names, matrix, gamesPerMatchup) {
    const table = document.getElementById('matchup-table');
    let html = '<thead><tr><th></th>';
    names.forEach(n => html += `<th>${n}</th>`);
    html += '</tr></thead><tbody>';

    names.forEach(n1 => {
        html += `<tr><td class="row-name">${n1}</td>`;
        names.forEach(n2 => {
            if (n1 === n2) {
                html += '<td class="win-self">-</td>';
            } else {
                const key = n1 + '|' + n2;
                const wr = matrix[key];
                let cls = 'win-mid';
                if (wr >= 60) cls = 'win-high';
                else if (wr < 40) cls = 'win-low';
                html += `<td class="${cls}">${wr}%</td>`;
            }
        });
        html += '</tr>';
    });

    html += '</tbody>';
    table.innerHTML = html;
    show('dash-matrix');
}

// ── Battle ──────────────────────────────────────────────────────
document.getElementById('btn-battle').addEventListener('click', runBattle);

async function runBattle() {
    const btn = document.getElementById('btn-battle');
    const deck1 = document.getElementById('battle-deck1').value;
    const deck2 = document.getElementById('battle-deck2').value;
    const games = parseInt(document.getElementById('battle-games').value);
    const mode = document.getElementById('battle-mode').value;

    btn.disabled = true;
    show('battle-loading');
    hide('battle-results');

    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deck1, deck2, games, mode }),
        });
        const data = await res.json();
        renderBattleResults(data);
    } catch (e) {
        alert('Error: ' + e.message);
    }

    hide('battle-loading');
    btn.disabled = false;
}

function renderBattleResults(data) {
    document.getElementById('result-name1').textContent = data.deck1;
    document.getElementById('result-name2').textContent = data.deck2;
    document.getElementById('result-wr1').textContent = data.deck1_win_rate + '%';
    document.getElementById('result-wr2').textContent = data.deck2_win_rate + '%';
    document.getElementById('result-wins1').textContent = data.deck1_wins;
    document.getElementById('result-wins2').textContent = data.deck2_wins;
    document.getElementById('result-total').textContent = data.games;
    document.getElementById('result-draws').textContent = data.draws;
    document.getElementById('result-turns').textContent = data.avg_turns;
    document.getElementById('result-log').textContent = data.log_file || '-';

    const total = data.deck1_wins + data.deck2_wins + data.draws;
    document.getElementById('win-bar-1').style.width = (data.deck1_wins / total * 100) + '%';
    document.getElementById('win-bar-2').style.width = (data.deck2_wins / total * 100) + '%';

    show('battle-results');
}

// ── Replay ──────────────────────────────────────────────────────
let replayData = null;
let replayIndex = 0;

document.getElementById('btn-replay').addEventListener('click', startReplay);
document.getElementById('btn-replay-next').addEventListener('click', nextTurn);
document.getElementById('btn-replay-all').addEventListener('click', showAllTurns);

async function startReplay() {
    const deck1 = document.getElementById('replay-deck1').value;
    const deck2 = document.getElementById('replay-deck2').value;

    show('replay-loading');
    hide('game-board');
    hide('btn-replay-next');
    hide('btn-replay-all');

    try {
        const res = await fetch('/api/play-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deck1, deck2 }),
        });
        replayData = await res.json();
        replayIndex = 0;

        document.getElementById('board-p1-name').textContent = deck1;
        document.getElementById('board-p2-name').textContent = deck2;
        document.getElementById('board-turn').textContent = '0';
        document.getElementById('board-p1-prizes').textContent = '3';
        document.getElementById('board-p2-prizes').textContent = '3';
        document.getElementById('game-log').innerHTML = '';
        hide('game-winner');

        // Show setup events
        const setupTurn = replayData.turns.find(t => t.turn === 0);
        if (setupTurn) {
            renderTurnEvents(setupTurn, true);
            replayIndex = 1;
        }

        show('game-board');
        show('btn-replay-next');
        show('btn-replay-all');
    } catch (e) {
        alert('Error: ' + e.message);
    }

    hide('replay-loading');
}

function nextTurn() {
    if (!replayData || replayIndex >= replayData.turns.length) {
        showWinner();
        return;
    }

    const turn = replayData.turns[replayIndex];
    renderTurnEvents(turn, false);
    document.getElementById('board-turn').textContent = turn.turn;
    replayIndex++;

    if (replayIndex >= replayData.turns.length) {
        showWinner();
    }
}

async function showAllTurns() {
    const speed = parseInt(document.getElementById('replay-speed').value);
    hide('btn-replay-next');
    hide('btn-replay-all');

    while (replayIndex < replayData.turns.length) {
        const turn = replayData.turns[replayIndex];
        renderTurnEvents(turn, false);
        document.getElementById('board-turn').textContent = turn.turn;
        replayIndex++;
        await sleep(speed);
    }
    showWinner();
}

function renderTurnEvents(turn, isSetup) {
    const log = document.getElementById('game-log');

    if (!isSetup) {
        const turnDiv = document.createElement('div');
        turnDiv.className = 'log-turn';
        const playerColor = turn.player === 0 ? 'p1' : 'p2';
        turnDiv.textContent = `═══ Turno ${turn.turn} - Jugador ${turn.player + 1} ═══`;
        log.appendChild(turnDiv);
    }

    turn.events.forEach(evt => {
        const div = document.createElement('div');
        div.className = 'log-event ' + classifyEvent(evt);
        div.textContent = evt;
        log.appendChild(div);
    });

    log.scrollTop = log.scrollHeight;
}

function classifyEvent(text) {
    if (text.includes('uses ') || text.includes('usa ')) return 'log-attack';
    if (text.includes('takes ') && text.includes('damage')) return 'log-damage';
    if (text.includes('knocked out') || text.includes('wins')) return 'log-ko';
    if (text.includes('evolves')) return 'log-evolve';
    if (text.includes('Attach') || text.includes('energy')) return 'log-energy';
    if (text.includes('Plays') && text.includes('supporter')) return 'log-supporter';
    if (text.includes('Plays ')) return 'log-item';
    return '';
}

function showWinner() {
    if (!replayData) return;
    const winner = document.getElementById('game-winner');
    if (replayData.winner !== null) {
        const name = replayData.winner === 0
            ? document.getElementById('replay-deck1').value
            : document.getElementById('replay-deck2').value;
        winner.textContent = `🏆 ${name} GANA en ${replayData.total_turns} turnos!`;
    } else {
        winner.textContent = 'Empate!';
    }
    show('game-winner');
    hide('btn-replay-next');
    hide('btn-replay-all');
}

// ── Decks Page ──────────────────────────────────────────────────
function renderDecksPage() {
    const container = document.getElementById('decks-container');
    container.innerHTML = '';

    Object.values(deckData).forEach(deck => {
        const div = document.createElement('div');
        div.className = 'deck-card';
        div.innerHTML = `
            <div class="deck-card-header">
                <div>
                    <h3>${deck.name}</h3>
                    <div style="font-size:12px;color:var(--text-dim);margin-top:4px">
                        ${deck.total_cards} cartas · ${deck.pokemon_count} Pokemon · ${deck.item_count} Items
                    </div>
                </div>
                <div class="energy-badges">
                    ${deck.energy_types.map(t => `<span class="energy-badge ${t}">${t}</span>`).join('')}
                </div>
            </div>
            <div class="deck-card-body">
                <ul class="card-list">
                    ${deck.cards.map(c => `
                        <li>
                            <div class="card-name">
                                <span class="card-type-badge ${c.type.toLowerCase()}">${c.type}</span>
                                <span>${c.name}${c.is_ex ? ' ★' : ''}</span>
                                ${c.hp ? `<span style="color:var(--text-dim);font-size:11px">${c.hp}HP</span>` : ''}
                            </div>
                            <span class="card-count">x${c.count}</span>
                        </li>
                        ${c.attacks ? c.attacks.map(a => `
                            <li class="card-detail" style="padding-left:40px;border:none;padding-top:0">
                                ⚡ ${a.name}: ${a.damage || '?'} dmg [${a.energy_cost.join('+')}]
                                ${a.description ? `<br><em>${a.description}</em>` : ''}
                            </li>
                        `).join('') : ''}
                    `).join('')}
                </ul>
            </div>
        `;

        div.querySelector('.deck-card-header').addEventListener('click', () => {
            div.classList.toggle('expanded');
        });

        container.appendChild(div);
    });
}

// ── Logs Page ───────────────────────────────────────────────────
document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);
document.getElementById('btn-close-log').addEventListener('click', () => hide('log-viewer'));

async function loadLogs() {
    try {
        const res = await fetch('/api/logs');
        const logs = await res.json();
        const container = document.getElementById('logs-list');

        if (logs.length === 0) {
            container.innerHTML = '<p style="color:var(--text-dim);padding:20px">No hay registros todavia. Ejecuta una simulacion primero.</p>';
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="log-entry" data-file="${log.log_filename}">
                <div>
                    <span class="log-type">${formatLogType(log.type)}</span>
                    <span style="margin-left:10px">${log.log_filename}</span>
                </div>
                <span class="log-time">${formatTime(log.timestamp)}</span>
            </div>
        `).join('');

        container.querySelectorAll('.log-entry').forEach(entry => {
            entry.addEventListener('click', () => viewLog(entry.dataset.file));
        });
    } catch (e) {
        console.error('Failed to load logs:', e);
    }
}

async function viewLog(filename) {
    try {
        const res = await fetch('/api/logs/' + filename);
        const data = await res.json();
        document.getElementById('log-content').textContent = data.content || JSON.stringify(data, null, 2);
        show('log-viewer');
    } catch (e) {
        alert('Error loading log: ' + e.message);
    }
}

function formatLogType(type) {
    if (type.includes('matchup')) return 'Matchup Table';
    if (type.includes('random')) return 'AI vs Random';
    if (type.includes('match')) return 'Batalla';
    return type;
}

function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleString('es');
}

// ── Utilities ───────────────────────────────────────────────────
function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Start ───────────────────────────────────────────────────────
init();
