document.addEventListener('DOMContentLoaded', () => {
    // --- 1. STATE AND DOM ---
    const state = { isRunning: false, isPaused: false, currentPhase: 'idle', breathPhase: 'inhale', animationFrameId: null, runTimerId: null, totalRunTime: 0, startTime: 0, syncStartTime: 0, mainAudioFile: null, auxAudioFile: null, };
    const dom = { lightBg: document.getElementById('light-background'), guideText: document.getElementById('guide-text-overlay'), mainAudio: document.getElementById('mainAudio'), auxAudio: document.getElementById('auxAudio'), consoleWrapper: document.querySelector('.console-wrapper'), toggleConsoleBtn: document.getElementById('toggle-console-btn'), presetsWrapper: document.querySelector('.presets-panel-wrapper'), togglePresetsBtn: document.getElementById('toggle-presets-btn'), statusDashboard: document.getElementById('status-dashboard'), runStatus: document.getElementById('run-status'), lightStatus: document.getElementById('light-status'), soundStatus: document.getElementById('sound-status'), startStopBtn: document.getElementById('startStopBtn'), resetBtn: document.getElementById('resetBtn'), saveConfigBtn: document.getElementById('saveConfigBtn'), breathsPerMin: document.getElementById('breathsPerMin'), masterKelvinStart: document.getElementById('masterKelvinStart'), masterHexStart: document.getElementById('masterHexStart'), masterKelvinEnd: document.getElementById('masterKelvinEnd'), masterHexEnd: document.getElementById('masterHexEnd'), masterGradientBar: document.getElementById('masterGradientBar'), kelvinSliderDefault: document.getElementById('kelvinSliderDefault'), kelvinDefault: document.getElementById('kelvinDefault'), defaultColor: document.getElementById('defaultColor'), kelvinSliderMin: document.getElementById('kelvinSliderMin'), kelvinMin: document.getElementById('kelvinMin'), warmColor: document.getElementById('warmColor'), kelvinSliderMax: document.getElementById('kelvinSliderMax'), kelvinMax: document.getElementById('kelvinMax'), coolColor: document.getElementById('coolColor'), soundscapeSelect: document.getElementById('soundscapeSelect'), panningEnable: document.getElementById('panningEnable'), panningPeriod: document.getElementById('panningPeriod'), mainTrackName: document.getElementById('mainTrackName'), editMainTrackBtn: document.getElementById('editMainTrackBtn'), mainVolDefault: document.getElementById('mainVolDefault'), mainVolMin: document.getElementById('mainVolMin'), mainVolMax: document.getElementById('mainVolMax'), auxTrackName: document.getElementById('auxTrackName'), editAuxTrackBtn: document.getElementById('editAuxTrackBtn'), auxEnable: document.getElementById('auxEnable'), auxVolume: document.getElementById('auxVolume'), lightDelay: document.getElementById('lightDelay'), lightDuration: document.getElementById('lightDuration'), soundDelay: document.getElementById('soundDelay'), soundDuration: document.getElementById('soundDuration'), configList: document.getElementById('configList'), currentDefaultConfig: document.getElementById('current-default-config'), soundscapeManagementList: document.getElementById('soundscapeManagementList'), addSoundscapeBtn: document.getElementById('addSoundscapeBtn'), saveConfigModal: document.getElementById('saveConfigModal'), configNameInput: document.getElementById('configNameInput'), confirmSaveConfigBtn: document.getElementById('confirmSaveConfigBtn'), soundscapeModal: document.getElementById('soundscapeModal'), soundscapeModalTitle: document.getElementById('soundscapeModalTitle'), soundscapeNameInput: document.getElementById('soundscapeNameInput'), mainTrackSelect: document.getElementById('mainTrackSelect'), auxTrackSelect: document.getElementById('auxTrackSelect'), confirmSaveSoundscapeBtn: document.getElementById('confirmSaveSoundscapeBtn'), };
    let audioCtx, mainGainNode, auxGainNode, pannerNode, mainSource, auxSource;
    let kelvinLookupTable = [];
    const masterRange = { start: { k: 2000, hex: '#f57e0f' }, end: { k: 8000, hex: '#8cb1ff' } };

    // --- 2. REAL API CALLS ---
    async function apiCall(url, method = 'GET', body = null) {
        try {
            const options = { method, headers: { 'Content-Type': 'application/json' } };
            if (body) options.body = JSON.stringify(body);
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: response.statusText }));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            if (response.headers.get("content-type")?.includes("application/json")) {
                 return await response.json();
            }
            return null;
        } catch (error) { console.error('API Call Failed:', url, error); throw error; }
    }

    // --- 3. HELPER AND CORE FUNCTIONS ---
    function kelvinToHex(kelvin) { kelvin = Math.max(1000, Math.min(40000, kelvin)) / 100; let r, g, b; if (kelvin <= 66) { r = 255; g = 99.4708025861 * Math.log(kelvin) - 161.1195681661; } else { r = 329.698727446 * Math.pow(kelvin - 60, -0.1332047592); } if (kelvin <= 66) { b = kelvin <= 19 ? 0 : 138.5177312231 * Math.log(kelvin - 10) - 305.0447927307; } else { b = 255; } const clamp = (v) => Math.max(0, Math.min(255, v)); const toHex = (c) => Math.round(clamp(c)).toString(16).padStart(2, '0'); return `#${toHex(r)}${toHex(g)}${toHex(b)}`; }
    function buildKelvinLookup() { if (kelvinLookupTable.length > 0) return; for (let k = 1000; k <= 12000; k += 50) { const hex = kelvinToHex(k); const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16); kelvinLookupTable.push({ k, r, g, b }); } }
    function hexToKelvin(hex) { const r1 = parseInt(hex.slice(1, 3), 16), g1 = parseInt(hex.slice(3, 5), 16), b1 = parseInt(hex.slice(5, 7), 16); let closestMatch = { k: 6500, dist: Infinity }; for (const entry of kelvinLookupTable) { const dist = Math.sqrt(Math.pow(r1 - entry.r, 2) + Math.pow(g1 - entry.g, 2) + Math.pow(b1 - entry.b, 2)); if (dist < closestMatch.dist) closestMatch = { k: entry.k, dist }; } return closestMatch.k; }
    const interpolateColor = (c1, c2, f) => { if (f < 0) f = 0; if (f > 1) f = 1; const r1=parseInt(c1.slice(1,3),16), g1=parseInt(c1.slice(3,5),16), b1=parseInt(c1.slice(5,7),16); const r2=parseInt(c2.slice(1,3),16), g2=parseInt(c2.slice(3,5),16), b2=parseInt(c2.slice(5,7),16); const r=Math.round(r1+f*(r2-r1)), g=Math.round(g1+f*(g2-g1)), b=Math.round(b1+f*(b2-b1)); return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`; };
    function updateMasterGradient() { const gradient = `linear-gradient(90deg, ${masterRange.start.hex}, ${masterRange.end.hex})`; dom.masterGradientBar.style.background = gradient; [dom.kelvinSliderDefault, dom.kelvinSliderMin, dom.kelvinSliderMax].forEach(s => s.style.background = gradient); const min = Math.min(parseInt(masterRange.start.k), parseInt(masterRange.end.k)); const max = Math.max(parseInt(masterRange.start.k), parseInt(masterRange.end.k)); [dom.kelvinSliderDefault, dom.kelvinSliderMin, dom.kelvinSliderMax].forEach(slider => { slider.min = min; slider.max = max; }); [dom.kelvinSliderDefault, dom.kelvinSliderMin, dom.kelvinSliderMax].forEach(slider => { slider.dispatchEvent(new Event('input', { bubbles: true })); }); }
    function setupMasterRangeBinding(kelvinInput, hexInput, rangeKey) { kelvinInput.addEventListener('change', () => { masterRange[rangeKey].k = parseInt(kelvinInput.value); masterRange[rangeKey].hex = kelvinToHex(kelvinInput.value); hexInput.value = masterRange[rangeKey].hex; kelvinInput.style.backgroundColor = masterRange[rangeKey].hex; updateMasterGradient(); }); hexInput.addEventListener('input', () => { masterRange[rangeKey].hex = hexInput.value; masterRange[rangeKey].k = hexToKelvin(hexInput.value); kelvinInput.value = masterRange[rangeKey].k; kelvinInput.style.backgroundColor = masterRange[rangeKey].hex; updateMasterGradient(); }); }
    function setupValueBinding(slider, numberDisplay, hiddenColorInput) { slider.addEventListener('input', () => { const currentKelvin = parseInt(slider.value); const startK = parseInt(masterRange.start.k); const endK = parseInt(masterRange.end.k); const minK = Math.min(startK, endK); const maxK = Math.max(startK, endK); const clampedKelvin = Math.max(minK, Math.min(maxK, currentKelvin)); const totalRange = endK - startK; const progress = totalRange === 0 ? 0.5 : (clampedKelvin - startK) / totalRange; const newHex = interpolateColor(masterRange.start.hex, masterRange.end.hex, progress); numberDisplay.value = clampedKelvin; slider.value = clampedKelvin; numberDisplay.style.backgroundColor = newHex; hiddenColorInput.value = newHex; }); numberDisplay.addEventListener('change', () => { slider.value = numberDisplay.value; slider.dispatchEvent(new Event('input', { bubbles: true })); }); }
    function setupAudioContext() { if (audioCtx && audioCtx.state !== 'closed') return; audioCtx = new (window.AudioContext || window.webkitAudioContext)(); mainGainNode = audioCtx.createGain(); auxGainNode = audioCtx.createGain(); pannerNode = audioCtx.createStereoPanner(); mainSource = audioCtx.createMediaElementSource(dom.mainAudio); auxSource = audioCtx.createMediaElementSource(dom.auxAudio); mainSource.connect(mainGainNode).connect(pannerNode).connect(audioCtx.destination); auxSource.connect(auxGainNode).connect(audioCtx.destination); mainGainNode.gain.setValueAtTime(0, audioCtx.currentTime); auxGainNode.gain.setValueAtTime(0, audioCtx.currentTime); }
    const formatTime = (s) => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;
    function startRunTimer() { if (state.runTimerId) clearInterval(state.runTimerId); state.totalRunTime = 0; updateStatusDisplay(); state.runTimerId = setInterval(() => { if (state.isRunning && !state.isPaused) { state.totalRunTime++; updateStatusDisplay(); } }, 1000); }
    function stopRunTimer() { if (state.runTimerId) clearInterval(state.runTimerId); state.runTimerId = null; }
    function updateStatusDisplay() { if (!state.isRunning) { dom.statusDashboard.classList.add('hidden'); return; } dom.statusDashboard.classList.remove('hidden'); dom.runStatus.textContent = `${state.isPaused ? '已暂停' : '运行中'}：${formatTime(state.totalRunTime)}`; const now = state.totalRunTime; const ld = parseInt(dom.lightDelay.value), durL = parseInt(dom.lightDuration.value); const sd = parseInt(dom.soundDelay.value), durS = parseInt(dom.soundDuration.value); switch (state.currentPhase) { case 'fadeIn': dom.lightStatus.textContent = now < ld ? `光：即将渐入 (剩 ${ld - now}s)` : now < ld + durL ? `光：正在渐入 (剩 ${ld + durL - now}s)` : '光：等待同步'; dom.soundStatus.textContent = now < sd ? `声：即将渐入 (剩 ${sd - now}s)` : now < sd + durS ? `声：正在渐入 (剩 ${sd + durS - now}s)` : '声：等待同步'; break; case 'syncing': dom.lightStatus.textContent = '光：正在同步...'; dom.soundStatus.textContent = '声：正在同步...'; break; case 'breathing': dom.lightStatus.textContent = '光：正在与呼吸同步'; dom.soundStatus.textContent = '声：正在与呼吸同步'; break; } }
    let breathProgress = 0, lastFrameTime = 0; const SYNC_DURATION = 2000;
    function mainLoop(timestamp) { if (!state.isRunning || state.isPaused) return; state.animationFrameId = requestAnimationFrame(mainLoop); const now = performance.now(); const elapsedTime = now - state.startTime; if (state.currentPhase === 'fadeIn') { const lightDelay = parseInt(dom.lightDelay.value) * 1000, lightDuration = parseInt(dom.lightDuration.value) * 1000 || 1; if (elapsedTime > lightDelay) dom.lightBg.style.backgroundColor = interpolateColor('#000000', dom.defaultColor.value, Math.min((elapsedTime - lightDelay) / lightDuration, 1)); const soundDelay = parseInt(dom.soundDelay.value) * 1000, soundDuration = parseInt(dom.soundDuration.value) * 1000 || 1; if (elapsedTime > soundDelay && audioCtx) { const soundProgress = Math.min((elapsedTime - soundDelay) / soundDuration, 1); mainGainNode.gain.value = (parseInt(dom.mainVolDefault.value) / 100) * soundProgress; if(dom.auxEnable.checked) auxGainNode.gain.value = (parseInt(dom.auxVolume.value) / 100) * soundProgress; } if (elapsedTime >= Math.max(lightDelay + lightDuration, soundDelay + soundDuration)) { state.currentPhase = 'syncing'; state.syncStartTime = now; dom.guideText.textContent = '准备...'; dom.guideText.style.opacity = 1; } } else if (state.currentPhase === 'syncing') { const syncProgress = Math.min((now - state.syncStartTime) / SYNC_DURATION, 1); dom.lightBg.style.backgroundColor = interpolateColor(dom.defaultColor.value, dom.warmColor.value, syncProgress); const volStart = parseInt(dom.mainVolDefault.value) / 100, volEnd = parseInt(dom.mainVolMin.value) / 100; if(audioCtx) mainGainNode.gain.value = volStart + (volEnd - volStart) * syncProgress; if (syncProgress >= 1) { state.currentPhase = 'breathing'; state.breathPhase = 'inhale'; breathProgress = 0; dom.guideText.textContent = '吸气'; } } else if (state.currentPhase === 'breathing') { const cycleDuration = (60 / parseInt(dom.breathsPerMin.value)) * 1000, phaseDuration = cycleDuration / 2; breathProgress += (timestamp - (lastFrameTime || timestamp)) / phaseDuration; if (breathProgress >= 1) { breathProgress = 0; state.breathPhase = state.breathPhase === 'inhale' ? 'exhale' : 'inhale'; dom.guideText.textContent = state.breathPhase === 'inhale' ? '吸气' : '呼气'; } const currentProgress = state.breathPhase === 'inhale' ? breathProgress : 1 - breathProgress; dom.lightBg.style.backgroundColor = interpolateColor(dom.warmColor.value, dom.coolColor.value, currentProgress); if (audioCtx) { const volMin = parseInt(dom.mainVolMin.value) / 100, volMax = parseInt(dom.mainVolMax.value) / 100; mainGainNode.gain.value = volMin + (volMax - volMin) * currentProgress; if (dom.panningEnable.checked) pannerNode.pan.value = Math.sin(Date.now() * 2 * Math.PI / (parseInt(dom.panningPeriod.value) * 1000)); } } lastFrameTime = timestamp; }
    async function applySettings(settings) { await updateCurrentSoundscape(settings.soundscapeSelect); masterRange.start.k = parseInt(settings.masterKelvinStart) || 2000; masterRange.start.hex = settings.masterHexStart || '#f57e0f'; masterRange.end.k = parseInt(settings.masterKelvinEnd) || 8000; masterRange.end.hex = settings.masterHexEnd || '#8cb1ff'; dom.masterKelvinStart.value = masterRange.start.k; dom.masterHexStart.value = masterRange.start.hex; dom.masterKelvinStart.style.backgroundColor = masterRange.start.hex; dom.masterKelvinEnd.value = masterRange.end.k; dom.masterHexEnd.value = masterRange.end.hex; dom.masterKelvinEnd.style.backgroundColor = masterRange.end.hex; updateMasterGradient(); for (const key in settings) { const el = dom[key]; if (el && !key.startsWith('master')) { if (el.type === 'checkbox') el.checked = settings[key]; else el.value = settings[key]; } } dom.kelvinSliderDefault.value = settings.kelvinSliderDefault || settings.kelvinDefault || 3000; dom.kelvinSliderMin.value = settings.kelvinSliderMin || settings.kelvinMin || 2000; dom.kelvinSliderMax.value = settings.kelvinSliderMax || settings.kelvinMax || 4000; [dom.kelvinSliderDefault, dom.kelvinSliderMin, dom.kelvinSliderMax].forEach(slider => { slider.dispatchEvent(new Event('input', { bubbles: true })); }); }
    async function renderConfigList() { try { const configs = await apiCall('/api/controlsets'); const { default: defaultName } = await apiCall('/api/controlsets/default'); dom.configList.innerHTML = ''; dom.currentDefaultConfig.textContent = defaultName || '无'; configs.forEach(name => { const li = document.createElement('li'); li.className = (name === defaultName) ? 'is-default' : ''; li.innerHTML = `<span class="preset-name">${name}</span><div class="preset-actions"><button class="apply-btn" title="应用">✔</button><button class="default-btn" title="设为默认">⭐</button><button class="delete-btn" title="删除">✕</button></div>`; li.querySelector('.apply-btn').addEventListener('click', async () => applySettings(await apiCall(`/api/controlsets/${name}`))); li.querySelector('.default-btn').addEventListener('click', async () => { await apiCall('/api/controlsets/default', 'POST', { name }); renderConfigList(); }); const deleteBtn = li.querySelector('.delete-btn'); if (name === '默认配置') deleteBtn.disabled = true; deleteBtn.addEventListener('click', async () => { if (confirm(`确定删除配置 "${name}"?`)) { await apiCall('/api/controlsets', 'DELETE', { name }); renderConfigList(); } }); dom.configList.appendChild(li); }); } catch (e) { console.error("Failed to render config list:", e); } }
    async function renderSoundscapeList() { try { const soundscapes = await apiCall('/api/soundsets'); const currentVal = dom.soundscapeSelect.value; dom.soundscapeSelect.innerHTML = ''; soundscapes.forEach(name => dom.soundscapeSelect.innerHTML += `<option value="${name}">${name}</option>`); if (currentVal && soundscapes.includes(currentVal)) dom.soundscapeSelect.value = currentVal; else if (soundscapes.length > 0) dom.soundscapeSelect.value = soundscapes[0]; dom.soundscapeManagementList.innerHTML = ''; soundscapes.forEach(name => { const li = document.createElement('li'); li.innerHTML = `<span class="preset-name">${name}</span><div class="preset-actions"><button class="delete-btn" title="删除">✕</button></div>`; const deleteBtn = li.querySelector('.delete-btn'); if (name === '海洋' || name === dom.soundscapeSelect.value) { deleteBtn.disabled = true; deleteBtn.title = (name === '海洋') ? '不可删除默认声景' : '无法删除正在使用的声景'; } deleteBtn.addEventListener('click', async () => { if (confirm(`确定删除声景 "${name}"?`)) { await apiCall('/api/soundsets', 'DELETE', { name }); await renderSoundscapeList(); await renderConfigList(); } }); dom.soundscapeManagementList.appendChild(li); }); } catch(e) { console.error("Failed to render soundscape list:", e); } }
    async function updateCurrentSoundscape(name) { if (!name) { state.mainAudioFile = null; state.auxAudioFile = null; dom.mainTrackName.textContent = '无'; dom.auxTrackName.textContent = '无'; return; } try { const data = await apiCall(`/api/soundsets/${name}`); state.mainAudioFile = data.main || null; state.auxAudioFile = data.aux || null; dom.mainTrackName.textContent = state.mainAudioFile || '无'; dom.auxTrackName.textContent = state.auxAudioFile || '无'; await renderSoundscapeList(); } catch (error) { await renderSoundscapeList(); } }
    function resetAll() { state.isRunning = false; state.isPaused = false; state.currentPhase = 'idle'; if (state.animationFrameId) cancelAnimationFrame(state.animationFrameId); stopRunTimer(); state.totalRunTime = 0; dom.mainAudio.pause(); dom.auxAudio.pause(); if (audioCtx) { mainGainNode.gain.setValueAtTime(0, audioCtx.currentTime); auxGainNode.gain.setValueAtTime(0, audioCtx.currentTime); } dom.lightBg.style.transition = 'background-color 0.5s'; dom.lightBg.style.backgroundColor = '#000'; dom.guideText.style.opacity = 0; dom.statusDashboard.classList.add('hidden'); dom.startStopBtn.textContent = '开始'; dom.startStopBtn.className = ''; }
    function setupEventListeners() {
        dom.startStopBtn.addEventListener('click', () => {
            if (!state.isRunning) {
                setupAudioContext(); if (audioCtx.state === 'suspended') audioCtx.resume();
                state.isRunning = true; state.isPaused = false; state.currentPhase = 'fadeIn';
                state.startTime = performance.now(); lastFrameTime = 0;
                dom.lightBg.style.transition = 'none';
                if (state.mainAudioFile) { dom.mainAudio.src = `/static/mainsound/${state.mainAudioFile}`; dom.mainAudio.play().catch(e=>console.error("Main audio play failed:", e)); }
                if (dom.auxEnable.checked && state.auxAudioFile) { dom.auxAudio.src = `/static/plussound/${state.auxAudioFile}`; dom.auxAudio.play().catch(e=>console.error("Aux audio play failed:", e)); }
                startRunTimer(); state.animationFrameId = requestAnimationFrame(mainLoop);
                dom.startStopBtn.textContent = '暂停'; dom.startStopBtn.className = 'running';
            } else if (state.isPaused) {
                state.isPaused = false; if(audioCtx) audioCtx.resume();
                lastFrameTime = performance.now(); state.animationFrameId = requestAnimationFrame(mainLoop);
                dom.startStopBtn.textContent = '暂停'; dom.startStopBtn.className = 'running';
            } else {
                state.isPaused = true; if(audioCtx) audioCtx.suspend();
                cancelAnimationFrame(state.animationFrameId);
                dom.startStopBtn.textContent = '继续'; dom.startStopBtn.className = 'paused';
            }
        });
        dom.resetBtn.addEventListener('click', () => { if(state.isRunning && !confirm("确定停止并重启?")) return; resetAll(); });
        dom.toggleConsoleBtn.addEventListener('click', () => dom.consoleWrapper.classList.toggle('collapsed'));
        dom.togglePresetsBtn.addEventListener('click', () => dom.presetsWrapper.classList.toggle('collapsed'));
        dom.auxEnable.addEventListener('change', e => { dom.auxVolume.disabled = !e.target.checked; });
        dom.panningEnable.addEventListener('change', e => { dom.panningPeriod.disabled = !e.target.checked; });
        dom.soundscapeSelect.addEventListener('change', (e) => updateCurrentSoundscape(e.target.value));
        dom.saveConfigBtn.addEventListener('click', () => dom.saveConfigModal.classList.remove('hidden'));
        [dom.saveConfigModal, dom.soundscapeModal].forEach(modal => {
             modal.addEventListener('click', e => { if (e.target.classList.contains('modal-overlay') || e.target.classList.contains('cancel-btn')) modal.classList.add('hidden'); });
             modal.querySelector('.cancel-btn').addEventListener('click', () => modal.classList.add('hidden'));
        });
        dom.confirmSaveConfigBtn.addEventListener('click', async () => {
            const name = dom.configNameInput.value.trim(); if (!name) return alert('请输入配置名称！');
            const settings = { ...Object.fromEntries([...document.querySelectorAll('.console input, .console select')].map(el => [el.id, el.type === 'checkbox' ? el.checked : el.value])), kelvinSliderDefault: dom.kelvinSliderDefault.value, kelvinSliderMin: dom.kelvinSliderMin.value, kelvinSliderMax: dom.kelvinSliderMax.value, };
            await apiCall('/api/controlsets', 'POST', { name, settings });
            dom.configNameInput.value = ''; dom.saveConfigModal.classList.add('hidden');
            renderConfigList();
        });
        const openSoundscapeModal = (isEditing) => {
            dom.soundscapeModal.dataset.isEditing = isEditing;
            const currentName = dom.soundscapeSelect.value;
            dom.soundscapeModalTitle.textContent = isEditing ? `修改声景: ${currentName}` : '创建新声景';
            dom.soundscapeNameInput.value = isEditing ? currentName : '';
            dom.soundscapeNameInput.disabled = isEditing;
            dom.mainTrackSelect.value = state.mainAudioFile || '';
            dom.auxTrackSelect.value = state.auxAudioFile || '';
            dom.soundscapeModal.classList.remove('hidden');
        };
        dom.addSoundscapeBtn.addEventListener('click', () => openSoundscapeModal(false));
        dom.editMainTrackBtn.addEventListener('click', () => openSoundscapeModal(true));
        dom.editAuxTrackBtn.addEventListener('click', () => openSoundscapeModal(true));
        dom.confirmSaveSoundscapeBtn.addEventListener('click', async () => {
            const isEditing = dom.soundscapeModal.dataset.isEditing === 'true';
            const name = dom.soundscapeNameInput.value.trim(); if (!name) return alert('请输入声景名称！');
            const main = dom.mainTrackSelect.value; const aux = dom.auxTrackSelect.value; if (!main) return alert('请至少选择一个主轨音频！');
            const payload = { name, main, aux };
            try {
                if (isEditing) { await apiCall(`/api/soundsets/${name}`, 'PUT', payload); }
                else { await apiCall('/api/soundsets', 'POST', payload); }
                dom.soundscapeModal.classList.add('hidden');
                await renderSoundscapeList();
                dom.soundscapeSelect.value = name;
                dom.soundscapeSelect.dispatchEvent(new Event('change'));
            } catch (error) { alert(`保存声景失败: ${error.message}`); }
        });
    }

    // --- 4. INITIALIZATION ---
    async function initializeApp() {
        buildKelvinLookup();
        setupEventListeners();
        setupMasterRangeBinding(dom.masterKelvinStart, dom.masterHexStart, 'start');
        setupMasterRangeBinding(dom.masterKelvinEnd, dom.masterHexEnd, 'end');
        setupValueBinding(dom.kelvinSliderDefault, dom.kelvinDefault, dom.defaultColor);
        setupValueBinding(dom.kelvinSliderMin, dom.kelvinMin, dom.warmColor);
        setupValueBinding(dom.kelvinSliderMax, dom.kelvinMax, dom.coolColor);
        try {
            const audioFiles = await apiCall('/api/get-audio-files');
            const populate = (sel, files, empty=false) => { sel.innerHTML = empty?'<option value="">无</option>':''; files.forEach(f => sel.innerHTML += `<option value="${f}">${f}</option>`); };
            populate(dom.mainTrackSelect, audioFiles.mainsound);
            populate(dom.auxTrackSelect, audioFiles.plussound, true);
            await renderConfigList();
            await renderSoundscapeList();
            const { default: defaultName } = await apiCall('/api/controlsets/default');
            const settings = await apiCall(`/api/controlsets/${defaultName}`);
            await applySettings(settings);
        } catch (e) {
            console.error("Initialization failed:", e);
            alert("应用初始化失败。请确保后端服务正在运行，或检查部署配置。");
        }
    }

    initializeApp();
});