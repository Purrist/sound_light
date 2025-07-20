document.addEventListener('DOMContentLoaded', () => {
    // --- 1. STATE AND DOM ---
    const state = {
        isLoggedIn: false,
        username: null,
        isAdmin: false,
        tempFilename: null,
        trackType: null,
        isPlaying: false,
        animationFrameId: null,
        audioFiles: { mainsound: [], plussound: [], mix_elements: [] },
    };
    const dom = {
        libraryPanel: document.querySelector('.library-panel'),
        mainAudioList: document.getElementById('mainAudioList'),
        auxAudioList: document.getElementById('auxAudioList'),
        mixElementsList: document.getElementById('mixElementsList'),
        mixElementUpload: document.getElementById('mixElementUpload'),
        tabButtons: document.querySelectorAll('.tab-button'),
        tabContents: document.querySelectorAll('.tab-content'),
        noiseDuration: document.getElementById('noiseDuration'),
        toneSlider: document.getElementById('toneSlider'),
        resonanceSlider: document.getElementById('resonanceSlider'),
        widthSlider: document.getElementById('widthSlider'),
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
    let audioCtx, gainNode, sourceNode;

    // --- 2. API HELPER ---
    async function apiCall(url, method = 'GET', body = null) {
        try {
            const options = { method, headers: {} };
            if (body) {
                options.body = JSON.stringify(body);
                options.headers['Content-Type'] = 'application/json';
            }
            const response = await fetch(url, options);
            const responseData = await response.json().catch(() => null);
            if (!response.ok) {
                const errorMessage = responseData?.error || `HTTP error! status: ${response.status}`;
                throw new Error(errorMessage);
            }
            return responseData;
        } catch (error) {
            console.error('API Call Failed:', url, error);
            alert(`操作失败: ${error.message}`);
            throw error;
        }
    }

    // --- 3. CORE FUNCTIONS ---
    async function renderAudioLists() {
        state.audioFiles = await apiCall('/api/get-audio-files');
        const populateList = (listElement, files, trackType) => {
            listElement.innerHTML = '';
            if (!files) return;
            files.forEach(file => {
                const li = document.createElement('li');
                li.className = `tag-${file.tag || (file.is_global ? 'global' : 'normal')}`;
                li.title = `类型: ${file.tag || (file.is_global ? 'global' : 'normal')}, 上传者: ${file.uploader}`;

                let actionButtons = '';
                if (file.tag !== 'base') {
                    if (file.tag === 'normal' || (file.uploader === state.username && !file.is_global) ) {
                        actionButtons += `<button class="delete-btn" title="删除">✕</button>`;
                    }
                    if (state.isAdmin) {
                        if (file.tag === 'global' || file.is_global) {
                            actionButtons += `<button class="delete-btn" title="删除受保护文件">✕</button>`;
                            actionButtons += `<button class="unprotect-btn" title="解锁">🔓</button>`;
                        } else {
                            actionButtons += `<button class="protect-btn" title="锁定">🔒</button>`;
                        }
                    }
                }
                const uploaderTag = file.uploader === '内置' ? '' : `(${file.uploader})`;
                li.innerHTML = `<span class="preset-name">${file.name}</span><em class="owner-tag">${uploaderTag}</em><div class="preset-actions">${actionButtons}</div>`;

                const deleteBtn = li.querySelector('.delete-btn');
                if (deleteBtn) { deleteBtn.addEventListener('click', async (e) => { e.stopPropagation(); if (confirm(`确定删除音频 "${file.name}"?`)) { try { await apiCall(`/api/delete-audio/${trackType}/${file.name}`, 'DELETE'); await renderAudioLists(); } catch (err) { alert(`删除失败: ${err.message}`); } } }); }
                const protectBtn = li.querySelector('.protect-btn');
                if (protectBtn) { protectBtn.addEventListener('click', async (e) => { e.stopPropagation(); try { await apiCall(`/api/audio/protect/${trackType}/${file.name}`, 'POST'); await renderAudioLists(); } catch (err) { alert(`操作失败: ${err.message}`); } }); }
                const unprotectBtn = li.querySelector('.unprotect-btn');
                if (unprotectBtn) { unprotectBtn.addEventListener('click', async (e) => { e.stopPropagation(); try { await apiCall(`/api/audio/unprotect/${trackType}/${file.name}`, 'POST'); await renderAudioLists(); } catch (err) { alert(`操作失败: ${err.message}`); } }); }
                
                listElement.appendChild(li);
            });
        };
        populateList(dom.mainAudioList, state.audioFiles.mainsound, 'mainsound');
        populateList(dom.auxAudioList, state.audioFiles.plussound, 'plussound');
        populateList(dom.mixElementsList, state.audioFiles.mix_elements, 'mix_elements');
    }

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
            duration_s: parseInt(dom.noiseDuration.value),
            tone_cutoff_hz: parseInt(dom.toneSlider.value),
            resonance: parseFloat(dom.resonanceSlider.value),
            stereo_width: parseFloat(dom.widthSlider.value),
        };
        try {
            const result = await apiCall('/api/generate/main-noise', 'POST', params);
            if (result && result.filename) {
                state.tempFilename = result.filename;
                state.trackType = 'mainsound';
                dom.previewInfo.textContent = `预览: ${result.filename}`;
                // This creates a "temporary" file object for the player
                const tempFileObj = { name: result.filename, uploader: state.username, tag: 'normal' };
                loadAndPlayAudio(dom.previewAudio, tempFileObj, 'mainsound', true); // true for isPreview
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

    // --- NEWLY ADDED: The missing player function ---
    const loadAndPlayAudio = (audioElement, fileObj, type, isPreview = false) => {
        if (fileObj && fileObj.name) {
            let path;
            if (fileObj.tag === 'base' || fileObj.uploader === '内置' || fileObj.uploader === 'system') {
                path = `/static-media/${type}/${encodeURIComponent(fileObj.name)}`;
            } else {
                 path = `/media/database/${type}/${encodeURIComponent(fileObj.name)}`;
            }
            console.log(`Loading audio from: ${path}`);
            audioElement.src = path;
            if (isPreview) {
                // For preview, we want to ensure it's ready before enabling the button
                audioElement.addEventListener('canplaythrough', () => {
                     console.log("Preview audio is ready.");
                }, { once: true });
            }
            audioElement.load();
            if(state.isPlaying || isPreview) {
                audioElement.play().catch(e => console.error(`Audio play failed for ${path}:`, e));
            }
        }
    };

    function setupPreview() {
        let breathProgress = 0, lastFrameTime = 0, breathPhase = 'inhale';
        const warmColor = '#e48737', coolColor = '#9ea9d7';
        function previewLoop(timestamp) {
            if (!state.isPlaying) return;
            state.animationFrameId = requestAnimationFrame(previewLoop);
            const cycleDuration = (60 / parseInt(dom.previewBPM.value)) * 1000;
            const phaseDuration = cycleDuration / 2;
            breathProgress += (timestamp - (lastFrameTime || timestamp)) / phaseDuration;
            if (breathProgress >= 1) { breathProgress = 0; breathPhase = breathPhase === 'inhale' ? 'exhale' : 'inhale'; dom.previewText.textContent = breathPhase === 'inhale' ? '吸气' : '呼气'; }
            const currentProgress = breathPhase === 'inhale' ? breathProgress : 1 - breathProgress;
            const r1=parseInt(coolColor.slice(1,3),16), g1=parseInt(coolColor.slice(3,5),16), b1=parseInt(coolColor.slice(5,7),16); const r2=parseInt(warmColor.slice(1,3),16), g2=parseInt(warmColor.slice(3,5),16), b2=parseInt(warmColor.slice(5,7),16); const r=Math.round(r1+currentProgress*(r2-r1)), g=Math.round(g1+currentProgress*(g2-g1)), b=Math.round(b1+currentProgress*(b2-b1)); dom.previewLight.style.backgroundColor = `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
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
        const defaultName = `粉红噪音_${new Date().toLocaleDateString().replaceAll('/', '')}.wav`;
        const final_filename = prompt("为新生成的音频命名:", defaultName);
        if (final_filename && state.tempFilename) {
            dom.saveTrackBtn.disabled = true; dom.saveTrackBtn.textContent = '保存中...';
            try {
                await apiCall('/api/audio/save-temp', 'POST', { temp_filename: state.tempFilename, final_filename: final_filename, track_type: state.trackType });
                alert('音频已成功保存到音乐库！');
                renderAudioLists();
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
        
        renderAudioLists();
        setupTabs();
        setupPreview();

        const handleUpload = async (file, trackType) => {
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);
            try {
                const response = await fetch(`/api/upload/${trackType}`, { method: 'POST', body: formData });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error);
                await renderAudioLists();
            } catch (error) {
                alert(`上传失败: ${error.message}`);
            }
        };
        
        if (dom.generateMainBtn) { dom.generateMainBtn.addEventListener('click', generateMainTrack); }
        if (dom.saveTrackBtn) { dom.saveTrackBtn.addEventListener('click', saveTrack); }
        if (dom.mixElementUpload) { dom.mixElementUpload.addEventListener('change', (e) => handleUpload(e.target.files[0], 'mix_elements')); }
    }

    initialize();
});