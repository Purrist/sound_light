document.addEventListener('DOMContentLoaded', () => {
    // --- 1. DOM (Specific to generator.html) ---
    // The global 'state' object is in common.js
    const dom = {
        mainAudioList: document.getElementById('mainAudioList'),
        auxAudioList: document.getElementById('auxAudioList'),
        mixElementsList: document.getElementById('mixElementsList'),
        mixElementUpload: document.getElementById('mixElementUpload'),
        tabButtons: document.querySelectorAll('.tab-button'),
        tabContents: document.querySelectorAll('.tab-content'),
        // NEW Noise parameters
        lowShelfSlider: document.getElementById('lowShelfSlider'),
        midShelfSlider: document.getElementById('midShelfSlider'),
        highShelfSlider: document.getElementById('highShelfSlider'),
        modRateSlider: document.getElementById('modRateSlider'),
        modDepthSlider: document.getElementById('modDepthSlider'),
        generateMainBtn: document.getElementById('generateMainBtn'),
        previewLight: document.getElementById('preview-light-background'),
        previewText: document.getElementById('preview-guide-text'),
        previewAudio: document.getElementById('previewAudio'),
        previewToggleBtn: document.getElementById('previewToggleBtn'),
        previewBPM: document.getElementById('previewBPM'),
        previewMinVol: document.getElementById('previewMinVol'),
        previewMaxVol: document.getElementById('previewMaxVol'),
        previewInfo: document.getElementById('previewInfo'),
        saveTrackBtn: document.getElementById('saveTrackBtn'),
    };

    // Add page-specific state properties
    state.tempFilename = null;
    state.trackType = null;
    state.isPlaying = false;
    state.animationFrameId = null;

    let audioCtx, gainNode, sourceNode;

    // --- CORE FUNCTIONS (Specific to generator.html) ---

    function setupTabs() {
        dom.tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                dom.tabButtons.forEach(btn => btn.classList.remove('active'));
                dom.tabContents.forEach(content => content.classList.remove('active'));
                button.classList.add('active');
                document.getElementById(button.dataset.tab).classList.add('active');
            });
        });
    }

    async function generateMainTrack() {
        dom.generateMainBtn.textContent = '生成中...';
        dom.generateMainBtn.disabled = true;
        resetPreview();
        const params = {
            duration_s: 480, // Fixed 8 minutes for high quality
            low_shelf_gain_db: parseFloat(dom.lowShelfSlider.value),
            mid_shelf_gain_db: parseFloat(dom.midShelfSlider.value),
            high_shelf_gain_db: parseFloat(dom.highShelfSlider.value),
            modulation_rate_hz: parseFloat(dom.modRateSlider.value),
            modulation_depth_db: parseFloat(dom.modDepthSlider.value),
        };
        try {
            const result = await apiCall('/api/generate/main-noise', 'POST', params);
            if (result && result.filename) {
                state.tempFilename = result.filename;
                state.trackType = 'mainsound';
                dom.previewInfo.textContent = `预览: ${result.filename}`;
                const fileObj = { name: result.filename, tag: 'normal' };
                loadAudioForPreview(dom.previewAudio, fileObj, 'mainsound');
                dom.previewToggleBtn.disabled = false;
                dom.saveTrackBtn.disabled = false;
            } else { throw new Error("API did not return a valid filename."); }
        } catch (error) {
            dom.previewInfo.textContent = '生成失败!';
        } finally {
            dom.generateMainBtn.textContent = '重新生成';
            dom.generateMainBtn.disabled = false;
        }
    }
    
    const loadAudioForPreview = (audioElement, fileObj, type) => {
        if (fileObj && fileObj.name) {
            let path = `/media/database/${type}/${encodeURIComponent(fileObj.name)}`;
            console.log(`Loading preview audio from: ${path}`);
            audioElement.src = path;
            audioElement.load();
        }
    };

    function setupPreview() {
        let breathProgress = 0, lastFrameTime = 0, breathPhase = 'inhale';
        const warmColor = '#e48737', coolColor = '#9ea9d7'; // Example colors
        function previewLoop(timestamp) {
            if (!state.isPlaying) return;
            state.animationFrameId = requestAnimationFrame(previewLoop);
            const cycleDuration = (60 / parseInt(dom.previewBPM.value)) * 1000;
            const phaseDuration = cycleDuration / 2;
            breathProgress += (timestamp - (lastFrameTime || timestamp)) / phaseDuration;
            if (breathProgress >= 1) { breathProgress = 0; breathPhase = breathPhase === 'inhale' ? 'exhale' : 'inhale'; dom.previewText.textContent = breathPhase === 'inhale' ? '吸气' : '呼气'; }
            const currentProgress = breathPhase === 'inhale' ? breathProgress : 1 - breathProgress;
            // This is a simplified color interpolation, you might have this in common.js
            const interpolate = (c1, c2, f) => { const r1=parseInt(c1.slice(1,3),16), g1=parseInt(c1.slice(3,5),16), b1=parseInt(c1.slice(5,7),16); const r2=parseInt(c2.slice(1,3),16), g2=parseInt(c2.slice(3,5),16), b2=parseInt(c2.slice(5,7),16); const r=Math.round(r1+f*(r2-r1)), g=Math.round(g1+f*(g2-g1)), b=Math.round(b1+f*(b2-b1)); return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`; };
            dom.previewLight.style.backgroundColor = interpolate(coolColor, warmColor, currentProgress);
            if (gainNode) { const minVol = parseFloat(dom.previewMinVol.value); const maxVol = parseFloat(dom.previewMaxVol.value); const minGain = minVol <= -80 ? 0 : Math.pow(10, minVol / 20); const maxGain = maxVol <= -80 ? 0 : Math.pow(10, maxVol / 20); gainNode.gain.value = minGain + (maxGain - minGain) * currentProgress; }
            lastFrameTime = timestamp;
        }
        dom.previewToggleBtn.addEventListener('click', () => {
            if (audioCtx && audioCtx.state === 'closed') { audioCtx = null; }
            if (!audioCtx) {
                try {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    sourceNode = audioCtx.createMediaElementSource(dom.previewAudio);
                    gainNode = audioCtx.createGain();
                    sourceNode.connect(gainNode).connect(audioCtx.destination);
                } catch (e) { console.error("Error setting up AudioContext:", e); alert("无法初始化音频预览。"); return; }
            }
            if (state.isPlaying) {
                state.isPlaying = false; dom.previewAudio.pause(); dom.previewToggleBtn.textContent = '▶ 预览'; cancelAnimationFrame(state.animationFrameId);
            } else {
                state.isPlaying = true; if(audioCtx.state === 'suspended') audioCtx.resume();
                dom.previewAudio.play().catch(e => { console.error("Preview play failed:", e); state.isPlaying = false; });
                dom.previewToggleBtn.textContent = '❚❚ 暂停'; lastFrameTime = performance.now();
                requestAnimationFrame(previewLoop);
            }
        });
    }
    
    async function saveTrack() {
        const defaultName = `助眠噪音_${new Date().toLocaleDateString().replaceAll('/', '-')}.wav`;
        const final_filename = prompt("为新生成的音频命名:", defaultName);
        if (final_filename && state.tempFilename) {
            dom.saveTrackBtn.disabled = true; dom.saveTrackBtn.textContent = '保存中...';
            try {
                await apiCall('/api/audio/save-temp', 'POST', { temp_filename: state.tempFilename, final_filename: final_filename, track_type: state.trackType });
                alert('音频已成功保存到音乐库！');
                const listMap = { mainAudioList: dom.mainAudioList, auxAudioList: dom.auxAudioList, mixElementsList: dom.mixElementsList };
                renderAudioLists(listMap);
                resetPreview();
            } catch (error) {
                dom.saveTrackBtn.disabled = false;
            } finally {
                dom.saveTrackBtn.textContent = '💾 保存';
            }
        }
    }
    
    function resetPreview() {
        if(state.isPlaying) { dom.previewToggleBtn.click(); }
        state.tempFilename = null; state.trackType = null;
        dom.saveTrackBtn.disabled = true; dom.previewToggleBtn.disabled = true;
        dom.previewAudio.src = '';
        if (dom.previewInfo) { dom.previewInfo.textContent = '暂无音频可预览'; }
        dom.previewText.textContent = '预览';
    }

    async function initialize() {
        try {
            const authStatus = await apiCall('/auth/status');
            if(authStatus && authStatus.logged_in) {
                state.isLoggedIn = true;
                state.username = authStatus.username;
                state.isAdmin = authStatus.is_admin;
            } else {
                alert("您需要登录才能访问音乐生成器。");
                window.location.href = '/index.html';
                return;
            }
        } catch(e) {
            alert("无法验证用户身份，将返回主页。");
            window.location.href = '/index.html';
            return;
        }
        
        const listMap = { 
            mainAudioList: dom.mainAudioList,
            auxAudioList: dom.auxAudioList,
            mixElementsList: dom.mixElementsList,
        };
        renderAudioLists(listMap); // Use the shared function
        
        setupTabs();
        setupPreview();

        const localHandleUpload = async (file, trackType) => { await handleUpload(file, trackType, listMap); };

        if (dom.generateMainBtn) { dom.generateMainBtn.addEventListener('click', generateMainTrack); }
        if (dom.saveTrackBtn) { dom.saveTrackBtn.addEventListener('click', saveTrack); }
        if (dom.mixElementUpload) { dom.mixElementUpload.addEventListener('change', (e) => localHandleUpload(e.target.files[0], 'mix_elements')); }
    }

    initialize();
});