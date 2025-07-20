document.addEventListener('DOMContentLoaded', () => {
    // --- 1. DOM (Specific to index.html) ---
    // The global 'state' object is in common.js
    const dom = {
        authContainer: document.getElementById('auth-container'), appContainer: document.getElementById('app-container'),
        loginForm: document.getElementById('login-form'), registerForm: document.getElementById('register-form'),
        showRegister: document.getElementById('show-register'), showLogin: document.getElementById('show-login'),
        loginError: document.getElementById('login-error'), registerError: document.getElementById('register-error'),
        usernameDisplay: document.getElementById('username-display'), logoutBtn: document.getElementById('logout-btn'),
        addMusicBtn: document.getElementById('addMusicBtn'), addMusicModal: document.getElementById('addMusicModal'),
        openGeneratorBtn: document.getElementById('openGeneratorBtn'), mainAudioUpload: document.getElementById('mainAudioUpload'),
        auxAudioUpload: document.getElementById('auxAudioUpload'), mainAudioList: document.getElementById('mainAudioList'),
        auxAudioList: document.getElementById('auxAudioList'), lightBg: document.getElementById('light-background'),
        guideText: document.getElementById('guide-text-overlay'), mainAudio: document.getElementById('mainAudio'),
        auxAudio: document.getElementById('auxAudio'), consoleWrapper: document.querySelector('.console-wrapper'),
        toggleConsoleBtn: document.getElementById('toggle-console-btn'), presetsWrapper: document.querySelector('.presets-panel-wrapper'),
        togglePresetsBtn: document.getElementById('toggle-presets-btn'), statusDashboard: document.getElementById('status-dashboard'),
        runStatus: document.getElementById('run-status'), lightStatus: document.getElementById('light-status'),
        soundStatus: document.getElementById('sound-status'), startStopBtn: document.getElementById('startStopBtn'),
        resetBtn: document.getElementById('resetBtn'), saveConfigBtn: document.getElementById('saveConfigBtn'),
        breathsPerMin: document.getElementById('breathsPerMin'), masterKelvinStart: document.getElementById('masterKelvinStart'),
        masterHexStart: document.getElementById('masterHexStart'), masterKelvinEnd: document.getElementById('masterKelvinEnd'),
        masterHexEnd: document.getElementById('masterHexEnd'), masterGradientBar: document.getElementById('masterGradientBar'),
        kelvinSliderDefault: document.getElementById('kelvinSliderDefault'), kelvinDefault: document.getElementById('kelvinDefault'),
        defaultColor: document.getElementById('defaultColor'), kelvinSliderMin: document.getElementById('kelvinSliderMin'),
        kelvinMin: document.getElementById('kelvinMin'), warmColor: document.getElementById('warmColor'),
        kelvinSliderMax: document.getElementById('kelvinSliderMax'), kelvinMax: document.getElementById('kelvinMax'),
        coolColor: document.getElementById('coolColor'), soundscapeSelect: document.getElementById('soundscapeSelect'),
        panningEnable: document.getElementById('panningEnable'), panningPeriod: document.getElementById('panningPeriod'),
        mainTrackName: document.getElementById('mainTrackName'), editMainTrackBtn: document.getElementById('editMainTrackBtn'),
        mainVolDefault: document.getElementById('mainVolDefault'), mainVolMin: document.getElementById('mainVolMin'),
        mainVolMax: document.getElementById('mainVolMax'), auxTrackName: document.getElementById('auxTrackName'),
        editAuxTrackBtn: document.getElementById('editAuxTrackBtn'), auxEnable: document.getElementById('auxEnable'),
        auxVolume: document.getElementById('auxVolume'), lightDelay: document.getElementById('lightDelay'),
        lightDuration: document.getElementById('lightDuration'), soundDelay: document.getElementById('soundDelay'),
        soundDuration: document.getElementById('soundDuration'), configList: document.getElementById('configList'),
        currentDefaultConfig: document.getElementById('current-default-config'), soundscapeManagementList: document.getElementById('soundscapeManagementList'),
        addSoundscapeBtn: document.getElementById('addSoundscapeBtn'), saveConfigModal: document.getElementById('saveConfigModal'),
        configNameInput: document.getElementById('configNameInput'), confirmSaveConfigBtn: document.getElementById('confirmSaveConfigBtn'),
        soundscapeModal: document.getElementById('soundscapeModal'), soundscapeModalTitle: document.getElementById('soundscapeModalTitle'),
        soundscapeNameInput: document.getElementById('soundscapeNameInput'), mainTrackSelect: document.getElementById('mainTrackSelect'),
        auxTrackSelect: document.getElementById('auxTrackSelect'), confirmSaveSoundscapeBtn: document.getElementById('confirmSaveSoundscapeBtn'),
    };
    
    // Add page-specific state properties
    state.isRunning = false;
    state.isPaused = false;
    state.currentPhase = 'idle';
    state.breathPhase = 'inhale';
    state.animationFrameId = null;
    state.runTimerId = null;
    state.totalRunTime = 0;
    state.startTime = 0;
    state.syncStartTime = 0;
    state.mainAudioFile = null;
    state.auxAudioFile = null;
    state.soundscapes = [];

    let audioCtx, mainGainNode, auxGainNode, pannerNode, mainSource, auxSource;
    let kelvinLookupTable = [];
    const masterRange = { start: { k: 2000, hex: '#f57e0f' }, end: { k: 8000, hex: '#8cb1ff' } };
    
    // Auth functions are now page-specific to handle DOM elements
    function setupAuthEventListeners() {
        if (dom.showRegister) dom.showRegister.addEventListener('click', (e) => { e.preventDefault(); dom.loginForm.classList.add('hidden'); dom.registerForm.classList.remove('hidden'); dom.loginError.textContent = ''; dom.registerError.textContent = ''; });
        if (dom.showLogin) dom.showLogin.addEventListener('click', (e) => { e.preventDefault(); dom.registerForm.classList.add('hidden'); dom.loginForm.classList.remove('hidden'); dom.loginError.textContent = ''; dom.registerError.textContent = ''; });
        if (dom.loginForm) dom.loginForm.addEventListener('submit', async (e) => { e.preventDefault(); const u = document.getElementById('login-username').value; const p = document.getElementById('login-password').value; try { const d = await apiCall('/auth/login', 'POST', { username: u, password: p }); dom.loginError.textContent = ''; await handleSuccessfulLogin(d.username, d.is_admin); } catch (err) { dom.loginError.textContent = err.message; } });
        if (dom.registerForm) dom.registerForm.addEventListener('submit', async (e) => { e.preventDefault(); const u = document.getElementById('register-username').value; const p = document.getElementById('register-password').value; try { await apiCall('/auth/register', 'POST', { username: u, password: p }); dom.registerError.textContent = ''; alert('注册成功！请登录。'); document.getElementById('login-username').value = u; document.getElementById('login-password').value = ''; dom.showLogin.click(); } catch (err) { dom.registerError.textContent = err.message; } });
        if (dom.logoutBtn) dom.logoutBtn.addEventListener('click', async () => { try { await apiCall('/auth/logout', 'POST'); } catch (err) { console.error("Logout failed but proceeding:", err); } window.location.reload(); });
    }
    async function checkAuthStatus() { try { const data = await apiCall('/auth/status'); if (data && data.logged_in) { await handleSuccessfulLogin(data.username, data.is_admin); } else { showAuthUI(); } } catch (err) { showAuthUI(); } }
    function showAuthUI() { if (dom.authContainer) dom.authContainer.classList.remove('hidden'); if (dom.appContainer) dom.appContainer.classList.add('hidden'); }
    async function handleSuccessfulLogin(username, isAdmin) { state.isLoggedIn = true; state.username = username; state.isAdmin = isAdmin; if (dom.usernameDisplay) dom.usernameDisplay.textContent = username; if (dom.authContainer) dom.authContainer.classList.add('hidden'); if (dom.appContainer) dom.appContainer.classList.remove('hidden'); await initializeApp(); }

    // --- Core app logic (remains in script.js) ---
    function kelvinToHex(kelvin) { kelvin = Math.max(1000, Math.min(40000, kelvin)) / 100; let r, g, b; if (kelvin <= 66) { r = 255; g = 99.4708025861 * Math.log(kelvin) - 161.1195681661; } else { r = 329.698727446 * Math.pow(kelvin - 60, -0.1332047592); g = 288.1221695283 * Math.pow(kelvin - 60, -0.0755148492); } if (kelvin >= 66) b = 255; else if (kelvin <= 19) b = 0; else b = 138.5177312231 * Math.log(kelvin - 10) - 305.0447927307; const clamp = (v) => Math.max(0, Math.min(255, v)); const toHex = (c) => Math.round(clamp(c)).toString(16).padStart(2, '0'); return `#${toHex(r)}${toHex(g)}${toHex(b)}`; }
    function buildKelvinLookup() { if (kelvinLookupTable.length > 0) return; for (let k = 1000; k <= 40000; k += 100) { const hex = kelvinToHex(k); const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16); kelvinLookupTable.push({ k, r, g, b }); } }
    function hexToKelvin(hex) { const r = parseInt(hex.slice(1, 3), 16); const g = parseInt(hex.slice(3, 5), 16); const b = parseInt(hex.slice(5, 7), 16); const max = Math.max(r, g, b); const min = Math.min(r, g, b); if (max === min) { return 6500; } const r_norm = r / 255; const g_norm = g / 255; const b_norm = b / 255; let warmthFactor = (b_norm - r_norm); if (r_norm > b_norm) { warmthFactor -= g_norm * 0.2; } const minKelvin = 1000; const maxKelvin = 15000; const centerKelvin = 6500; let kelvin; if (warmthFactor > 0) { kelvin = centerKelvin + warmthFactor * (maxKelvin - centerKelvin); } else { kelvin = centerKelvin + warmthFactor * (centerKelvin - minKelvin); } return Math.round(Math.max(minKelvin, Math.min(maxKelvin, kelvin))); }
    const interpolateColor = (c1, c2, f) => { f = Math.max(0, Math.min(1, f)); const r1=parseInt(c1.slice(1,3),16), g1=parseInt(c1.slice(3,5),16), b1=parseInt(c1.slice(5,7),16); const r2=parseInt(c2.slice(1,3),16), g2=parseInt(c2.slice(3,5),16), b2=parseInt(c2.slice(5,7),16); const r=Math.round(r1+f*(r2-r1)), g=Math.round(g1+f*(g2-g1)), b=Math.round(b1+f*(b2-b1)); return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`; };
    function updateMasterGradient() { const gradient = `linear-gradient(90deg, ${masterRange.start.hex}, ${masterRange.end.hex})`; dom.masterGradientBar.style.background = gradient; [dom.kelvinSliderDefault, dom.kelvinSliderMin, dom.kelvinSliderMax].forEach(s => s.style.background = gradient); const min = Math.min(parseInt(masterRange.start.k), parseInt(masterRange.end.k)); const max = Math.max(parseInt(masterRange.start.k), parseInt(masterRange.end.k)); [dom.kelvinSliderDefault, dom.kelvinSliderMin, dom.kelvinSliderMax].forEach(slider => { slider.min = min; slider.max = max; slider.dispatchEvent(new Event('input', { bubbles: true })); }); }
    function setupAudioContext() { if (audioCtx && audioCtx.state !== 'closed') return; audioCtx = new (window.AudioContext || window.webkitAudioContext)(); mainGainNode = audioCtx.createGain(); auxGainNode = audioCtx.createGain(); pannerNode = audioCtx.createStereoPanner(); mainSource = audioCtx.createMediaElementSource(dom.mainAudio); auxSource = audioCtx.createMediaElementSource(dom.auxAudio); mainSource.connect(mainGainNode).connect(pannerNode).connect(audioCtx.destination); auxSource.connect(auxGainNode).connect(audioCtx.destination); mainGainNode.gain.setValueAtTime(0, audioCtx.currentTime); auxGainNode.gain.setValueAtTime(0, audioCtx.currentTime); }
    const formatTime = (s) => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;
    function startRunTimer() { if (state.runTimerId) clearInterval(state.runTimerId); state.totalRunTime = 0; updateStatusDisplay(); state.runTimerId = setInterval(() => { if (state.isRunning && !state.isPaused) { state.totalRunTime++; updateStatusDisplay(); } }, 1000); }
    function stopRunTimer() { if (state.runTimerId) clearInterval(state.runTimerId); state.runTimerId = null; }
    function updateStatusDisplay() { if (!state.isRunning) { dom.statusDashboard.classList.add('hidden'); return; } dom.statusDashboard.classList.remove('hidden'); dom.runStatus.textContent = `${state.isPaused ? '已暂停' : '运行中'}：${formatTime(state.totalRunTime)}`; const now = state.totalRunTime; const ld = parseInt(dom.lightDelay.value), durL = parseInt(dom.lightDuration.value); const sd = parseInt(dom.soundDelay.value), durS = parseInt(dom.soundDuration.value); switch (state.currentPhase) { case 'fadeIn': dom.lightStatus.textContent = now < ld ? `光：即将渐入 (剩 ${ld - now}s)` : now < ld + durL ? `光：正在渐入 (剩 ${ld + durL - now}s)` : '光：等待同步'; dom.soundStatus.textContent = now < sd ? `声：即将渐入 (剩 ${sd - now}s)` : now < sd + durS ? `声：正在渐入 (剩 ${sd + durS - now}s)` : '声：等待同步'; break; case 'syncing': dom.lightStatus.textContent = '光：正在同步...'; dom.soundStatus.textContent = '声：正在同步...'; break; case 'breathing': dom.lightStatus.textContent = '光：正在与呼吸同步'; dom.soundStatus.textContent = '声：正在与呼吸同步'; break; } }
    let breathProgress = 0, lastFrameTime = 0; const SYNC_DURATION = 2000;
    function mainLoop(timestamp) { if (!state.isRunning || state.isPaused) return; state.animationFrameId = requestAnimationFrame(mainLoop); const now = performance.now(); const elapsedTime = now - state.startTime; if (state.currentPhase === 'fadeIn') { const lightDelay = parseInt(dom.lightDelay.value) * 1000, lightDuration = parseInt(dom.lightDuration.value) * 1000 || 1; if (elapsedTime > lightDelay) dom.lightBg.style.backgroundColor = interpolateColor('#000000', dom.defaultColor.value, Math.min((elapsedTime - lightDelay) / lightDuration, 1)); const soundDelay = parseInt(dom.soundDelay.value) * 1000, soundDuration = parseInt(dom.soundDuration.value) * 1000 || 1; if (elapsedTime > soundDelay && audioCtx) { const soundProgress = Math.min((elapsedTime - soundDelay) / soundDuration, 1); mainGainNode.gain.value = (parseInt(dom.mainVolDefault.value) / 100) * soundProgress; if(dom.auxEnable.checked) auxGainNode.gain.value = (parseInt(dom.auxVolume.value) / 100) * soundProgress; } if (elapsedTime >= Math.max(lightDelay + lightDuration, soundDelay + soundDuration)) { state.currentPhase = 'syncing'; state.syncStartTime = now; dom.guideText.textContent = '准备...'; dom.guideText.style.opacity = 1; } } else if (state.currentPhase === 'syncing') { const syncProgress = Math.min((now - state.syncStartTime) / SYNC_DURATION, 1); dom.lightBg.style.backgroundColor = interpolateColor(dom.defaultColor.value, dom.warmColor.value, syncProgress); const volStart = parseInt(dom.mainVolDefault.value) / 100, volEnd = parseInt(dom.mainVolMin.value) / 100; if(audioCtx) mainGainNode.gain.value = volStart + (volEnd - volStart) * syncProgress; if (syncProgress >= 1) { state.currentPhase = 'breathing'; state.breathPhase = 'inhale'; breathProgress = 0; dom.guideText.textContent = '吸气'; } } else if (state.currentPhase === 'breathing') { const cycleDuration = (60 / parseInt(dom.breathsPerMin.value)) * 1000, phaseDuration = cycleDuration / 2; breathProgress += (timestamp - (lastFrameTime || timestamp)) / phaseDuration; if (breathProgress >= 1) { breathProgress = 0; state.breathPhase = state.breathPhase === 'inhale' ? 'exhale' : 'inhale'; dom.guideText.textContent = state.breathPhase === 'inhale' ? '吸气' : '呼气'; } const currentProgress = state.breathPhase === 'inhale' ? breathProgress : 1 - breathProgress; dom.lightBg.style.backgroundColor = interpolateColor(dom.warmColor.value, dom.coolColor.value, currentProgress); if (audioCtx) { const volMin = parseInt(dom.mainVolMin.value) / 100, volMax = parseInt(dom.mainVolMax.value) / 100; mainGainNode.gain.value = volMin + (volMax - volMin) * currentProgress; if (dom.panningEnable.checked) pannerNode.pan.value = Math.sin(Date.now() * 2 * Math.PI / (parseInt(dom.panningPeriod.value) * 1000)); } } lastFrameTime = timestamp; }

    async function applySettings(settings) {
        masterRange.start.k = parseInt(settings.masterKelvinStart) || 2000; masterRange.start.hex = settings.masterHexStart || '#f57e0f'; masterRange.end.k = parseInt(settings.masterKelvinEnd) || 8000; masterRange.end.hex = settings.masterHexEnd || '#8cb1ff'; dom.masterKelvinStart.value = masterRange.start.k; dom.masterHexStart.value = masterRange.start.hex; dom.masterKelvinStart.style.backgroundColor = masterRange.start.hex; dom.masterKelvinEnd.value = masterRange.end.k; dom.masterHexEnd.value = masterRange.end.hex; dom.masterKelvinEnd.style.backgroundColor = masterRange.end.hex; updateMasterGradient();
        for (const key in settings) { const el = dom[key]; if (el && !key.startsWith('master') && !key.startsWith('kelvin') && !key.endsWith('Color')) { if (el.type === 'checkbox') { el.checked = settings[key]; } else { el.value = settings[key]; } el.dispatchEvent(new Event('change')); } }
        dom.kelvinDefault.value = settings.kelvinSliderDefault || settings.kelvinDefault || 5000;
        dom.kelvinMin.value = settings.kelvinSliderMin || settings.kelvinMin || 3000;
        dom.kelvinMax.value = settings.kelvinSliderMax || settings.kelvinMax || 7000;
        dom.kelvinDefault.dispatchEvent(new Event('change', { bubbles: true })); dom.kelvinMin.dispatchEvent(new Event('change', { bubbles: true })); dom.kelvinMax.dispatchEvent(new Event('change', { bubbles: true }));
        await updateCurrentSoundscape(settings.soundscapeSelect);
    }

    async function renderConfigList() { try { const configs = await apiCall('/api/controlsets'); const { default: defaultName } = await apiCall('/api/controlsets/default'); dom.configList.innerHTML = ''; dom.currentDefaultConfig.textContent = defaultName || '无'; configs.forEach(item => { const li = document.createElement('li'); li.className = (item.name === defaultName) ? 'is-default' : ''; if(item.is_global) li.classList.add('is-global'); li.title = `上传者: ${item.uploader}`; li.innerHTML = `<span class="preset-name">${item.name}</span><div class="preset-actions"><button class="apply-btn" title="应用">✔</button><button class="default-btn" title="设为默认">⭐</button><button class="delete-btn" title="删除">✕</button></div>`; li.querySelector('.apply-btn').addEventListener('click', async () => applySettings(await apiCall(`/api/controlsets/${item.name}`))); li.querySelector('.default-btn').addEventListener('click', async () => { await apiCall('/api/controlsets/default', 'POST', { name: item.name }); renderConfigList(); }); const deleteBtn = li.querySelector('.delete-btn'); if (item.uploader === 'system' || (item.is_global && !state.isAdmin)) { deleteBtn.disabled = true; } else { deleteBtn.addEventListener('click', async () => { if (confirm(`确定删除配置 "${item.name}"?`)) { try { await apiCall('/api/controlsets', 'DELETE', { name: item.name }); await renderConfigList(); } catch (error) { alert(`删除失败: ${error.message}`); } } }); } dom.configList.appendChild(li); }); } catch (e) { console.error("Failed to render config list:", e); } }
    async function renderSoundscapeList() { try { state.soundscapes = await apiCall('/api/soundsets'); const currentVal = dom.soundscapeSelect.value; dom.soundscapeSelect.innerHTML = ''; state.soundscapes.forEach(item => dom.soundscapeSelect.innerHTML += `<option value="${item.name}">${item.name}</option>`); if (currentVal && state.soundscapes.some(s => s.name === currentVal)) dom.soundscapeSelect.value = currentVal; else if (state.soundscapes.length > 0) dom.soundscapeSelect.value = state.soundscapes[0].name; dom.soundscapeManagementList.innerHTML = ''; state.soundscapes.forEach(item => { const li = document.createElement('li'); if(item.is_global) li.classList.add('is-global'); li.title = `上传者: ${item.uploader}`; li.innerHTML = `<span class="preset-name">${item.name}</span><div class="preset-actions"><button class="delete-btn" title="删除">✕</button></div>`; const deleteBtn = li.querySelector('.delete-btn'); if (item.name === dom.soundscapeSelect.value) { deleteBtn.disabled = true; deleteBtn.title = '无法删除正在使用的声景'; } else if (item.uploader === 'system' || (item.is_global && !state.isAdmin)) { deleteBtn.disabled = true; } else { deleteBtn.addEventListener('click', async () => { if (confirm(`确定删除声景 "${item.name}"?`)) { try { await apiCall('/api/soundsets', 'DELETE', { name: item.name }); await renderSoundscapeList(); await renderConfigList(); } catch(error) { alert(`删除失败: ${error.message}`); } } }); } dom.soundscapeManagementList.appendChild(li); }); } catch(e) { console.error("Failed to render soundscape list:", e); } }
        
    async function updateCurrentSoundscape(name) {
        if (!name) { state.mainAudioFile = null; state.auxAudioFile = null; dom.mainTrackName.textContent = '无'; dom.auxTrackName.textContent = '无'; return; }
        try {
            const data = await apiCall(`/api/soundsets/${name}`);
            const mainFile = data.main || null;
            const auxFile = data.aux || null;
            state.mainAudioFile = state.audioFiles.mainsound.find(f => f.name === mainFile) || null;
            state.auxAudioFile = state.audioFiles.plussound.find(f => f.name === auxFile) || null;
            dom.mainTrackName.textContent = state.mainAudioFile ? state.mainAudioFile.name : '无';
            dom.auxTrackName.textContent = state.auxAudioFile ? state.auxAudioFile.name : '无';
            await renderSoundscapeList();
        } catch (error) { console.error(`Failed to update soundscape to ${name}`, error); await renderSoundscapeList(); }
    }

    function resetAll() { state.isRunning = false; state.isPaused = false; state.currentPhase = 'idle'; if (state.animationFrameId) cancelAnimationFrame(state.animationFrameId); stopRunTimer(); state.totalRunTime = 0; dom.mainAudio.pause(); dom.auxAudio.pause(); dom.mainAudio.src = ''; dom.auxAudio.src = ''; if (audioCtx) { mainGainNode.gain.setValueAtTime(0, audioCtx.currentTime); auxGainNode.gain.setValueAtTime(0, audioCtx.currentTime); } dom.lightBg.style.transition = 'background-color 0.5s'; dom.lightBg.style.backgroundColor = '#000'; dom.guideText.style.opacity = 0; dom.statusDashboard.classList.add('hidden'); dom.startStopBtn.textContent = '开始'; dom.startStopBtn.className = ''; }
    
    function setupAppEventListeners() {
        function setupMasterRangeBinding(kelvinInput, hexInput, rangeKey) {
            kelvinInput.addEventListener('change', () => { const kelvin = Math.round(Math.max(1000, Math.min(40000, parseInt(kelvinInput.value) || 6500))); const newHex = kelvinToHex(kelvin); masterRange[rangeKey].k = kelvin; masterRange[rangeKey].hex = newHex; kelvinInput.value = kelvin; hexInput.value = newHex; kelvinInput.style.backgroundColor = newHex; updateMasterGradient(); });
            hexInput.addEventListener('input', () => { const selectedHex = hexInput.value; const estimatedKelvin = hexToKelvin(selectedHex); masterRange[rangeKey].k = estimatedKelvin; masterRange[rangeKey].hex = selectedHex; kelvinInput.value = estimatedKelvin; kelvinInput.style.backgroundColor = selectedHex; updateMasterGradient(); });
        }
        function setupValueBinding(slider, numberDisplay, hiddenColorInput) {
            slider.addEventListener('input', () => { const currentKelvin = parseInt(slider.value); const startK = parseInt(masterRange.start.k); const endK = parseInt(masterRange.end.k); const minK = Math.min(startK, endK); const maxK = Math.max(startK, endK); const clampedKelvin = Math.max(minK, Math.min(maxK, currentKelvin)); const totalRange = endK - startK; const progress = totalRange === 0 ? 0.5 : (clampedKelvin - startK) / totalRange; const newHex = interpolateColor(masterRange.start.hex, masterRange.end.hex, progress); numberDisplay.value = clampedKelvin; slider.value = clampedKelvin; numberDisplay.style.backgroundColor = newHex; if(hiddenColorInput) hiddenColorInput.value = newHex; });
            numberDisplay.addEventListener('change', () => { slider.value = numberDisplay.value; slider.dispatchEvent(new Event('input', { bubbles: true })); });
        }
        setupMasterRangeBinding(dom.masterKelvinStart, dom.masterHexStart, 'start');
        setupMasterRangeBinding(dom.masterKelvinEnd, dom.masterHexEnd, 'end');
        setupValueBinding(dom.kelvinSliderDefault, dom.kelvinDefault, dom.defaultColor);
        setupValueBinding(dom.kelvinSliderMin, dom.kelvinMin, dom.warmColor);
        setupValueBinding(dom.kelvinSliderMax, dom.kelvinMax, dom.coolColor);

        dom.startStopBtn.addEventListener('click', () => {
            if (!state.isRunning) {
                setupAudioContext(); if (audioCtx.state === 'suspended') audioCtx.resume();
                state.isRunning = true; state.isPaused = false; state.currentPhase = 'fadeIn';
                state.startTime = performance.now(); lastFrameTime = 0;
                dom.lightBg.style.transition = 'none';
                
                const loadAndPlayAudio = (audioElement, fileObj, type) => {
                    if (fileObj && fileObj.name) {
                        let path;
                        if (fileObj.uploader === 'system') {
                            path = `/static-media/${type}/${encodeURIComponent(fileObj.name)}`;
                        } else {
                            path = `/media/database/${type}/${encodeURIComponent(fileObj.name)}`;
                        }
                        console.log(`Loading audio from: ${path}`);
                        audioElement.src = path;
                        audioElement.load();
                        audioElement.play().catch(e => console.error(`Audio play failed for ${path}:`, e));
                    }
                };
                loadAndPlayAudio(dom.mainAudio, state.mainAudioFile, 'mainsound');
                if (dom.auxEnable.checked) { loadAndPlayAudio(dom.auxAudio, state.auxAudioFile, 'plussound'); }
                startRunTimer();
                state.animationFrameId = requestAnimationFrame(mainLoop);
                dom.startStopBtn.textContent = '暂停'; dom.startStopBtn.className = 'running';
            } else if (state.isPaused) {
                state.isPaused = false; if(audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
                dom.mainAudio.play().catch(e => {}); dom.auxAudio.play().catch(e => {});
                lastFrameTime = performance.now(); state.animationFrameId = requestAnimationFrame(mainLoop);
                dom.startStopBtn.textContent = '暂停'; dom.startStopBtn.className = 'running';
            } else {
                state.isPaused = true; if(audioCtx) audioCtx.suspend();
                dom.mainAudio.pause(); dom.auxAudio.pause();
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
        dom.saveConfigBtn.addEventListener('click', () => { dom.configNameInput.value = ''; dom.saveConfigModal.classList.remove('hidden'); });
        
        [dom.saveConfigModal, dom.soundscapeModal, dom.addMusicModal].forEach(modal => { if(modal) { modal.addEventListener('click', e => { if (e.target.classList.contains('modal-overlay') || e.target.classList.contains('cancel-btn')) modal.classList.add('hidden'); }); const cancelBtn = modal.querySelector('.cancel-btn'); if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.add('hidden')); } });
        
        if (dom.confirmSaveConfigBtn) dom.confirmSaveConfigBtn.addEventListener('click', async () => { const name = dom.configNameInput.value.trim(); if (!name) return alert('请输入配置名称！'); const settings = { ...Object.fromEntries([...document.querySelectorAll('.console input, .console select')].map(el => [el.id, el.type === 'checkbox' ? el.checked : el.value])), kelvinSliderDefault: dom.kelvinSliderDefault.value, kelvinSliderMin: dom.kelvinSliderMin.value, kelvinSliderMax: dom.kelvinSliderMax.value, }; try { await apiCall('/api/controlsets', 'POST', { name, settings }); dom.saveConfigModal.classList.add('hidden'); renderConfigList(); } catch(err) { alert(`保存失败: ${err.message}`)}; });
        
        const openSoundscapeModal = (isEditing) => {
            dom.soundscapeModal.dataset.isEditing = isEditing;
            const currentName = dom.soundscapeSelect.value;
            const currentSoundscape = state.soundscapes.find(s => s.name === currentName);
            dom.soundscapeModalTitle.textContent = isEditing ? `修改声景: ${currentName}` : '创建新声景';
            dom.soundscapeNameInput.value = isEditing ? currentName : '';
            dom.soundscapeNameInput.disabled = isEditing && currentSoundscape?.is_global;
            dom.mainTrackSelect.value = state.mainAudioFile ? state.mainAudioFile.name : '';
            dom.auxTrackSelect.value = state.auxAudioFile ? state.auxAudioFile.name : '';
            dom.soundscapeModal.classList.remove('hidden');
        };
        if (dom.addSoundscapeBtn) dom.addSoundscapeBtn.addEventListener('click', () => openSoundscapeModal(false));
        if (dom.editMainTrackBtn) dom.editMainTrackBtn.addEventListener('click', () => openSoundscapeModal(true));
        if (dom.editAuxTrackBtn) dom.editAuxTrackBtn.addEventListener('click', () => openSoundscapeModal(true));
        if (dom.confirmSaveSoundscapeBtn) dom.confirmSaveSoundscapeBtn.addEventListener('click', async () => { const isEditing = dom.soundscapeModal.dataset.isEditing === 'true'; const name = dom.soundscapeNameInput.value.trim(); if (!name) return alert('请输入声景名称！'); const main = dom.mainTrackSelect.value; const aux = dom.auxTrackSelect.value; if (!main) return alert('请至少选择一个主轨音频！'); const payload = { name, main, aux }; try { await apiCall('/api/soundsets', 'POST', payload); dom.soundscapeModal.classList.add('hidden'); await renderSoundscapeList(); dom.soundscapeSelect.value = name; dom.soundscapeSelect.dispatchEvent(new Event('change')); } catch (error) { alert(`保存失败: ${error.message}`); } });
        
        const listMap = { mainAudioList: dom.mainAudioList, auxAudioList: dom.auxAudioList };
        const dropdowns = {};
        const localHandleUpload = async (file, trackType) => { await handleUpload(file, trackType, listMap, dropdowns); if(dom.addMusicModal) dom.addMusicModal.classList.add('hidden'); };
        if (dom.mainAudioUpload) dom.mainAudioUpload.addEventListener('change', (e) => localHandleUpload(e.target.files[0], 'mainsound'));
        if (dom.auxAudioUpload) dom.auxAudioUpload.addEventListener('change', (e) => localHandleUpload(e.target.files[0], 'plussound'));
        
        if (dom.addMusicBtn) dom.addMusicBtn.addEventListener('click', () => dom.addMusicModal.classList.remove('hidden'));
        if (dom.openGeneratorBtn) dom.openGeneratorBtn.addEventListener('click', () => { window.location.href = '/generator.html'; });
    }

    async function initializeApp() {
        buildKelvinLookup();
        setupAppEventListeners();
        try {
            const listMap = { mainAudioList: dom.mainAudioList, auxAudioList: dom.auxAudioList };
            const dropdowns = { mainTrackSelect: dom.mainTrackSelect, auxTrackSelect: dom.auxTrackSelect };
            await renderAudioLists(listMap, dropdowns);
            await renderConfigList();
            await renderSoundscapeList();
            const { default: defaultName } = await apiCall('/api/controlsets/default');
            const settings = await apiCall(`/api/controlsets/${defaultName || '默认配置'}`);
            await applySettings(settings);
        } catch (e) {
            console.error("Initialization failed:", e);
            alert("应用初始化失败。可能是因为没有默认配置。请尝试保存一个配置并设为默认。");
        }
    }
    
    // This check ensures that the script only tries to run its main logic on index.html
    if (document.getElementById('app-container')) {
        setupAuthEventListeners();
        checkAuthStatus();
    }
});