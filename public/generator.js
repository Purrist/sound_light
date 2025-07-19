document.addEventListener('DOMContentLoaded', () => {
    const state = {
        tempFilename: null,
        trackType: null,
        isPlaying: false,
        animationFrameId: null,
    };
    const dom = {
        mainAudioList: document.getElementById('mainAudioList'),
        auxAudioList: document.getElementById('auxAudioList'),
        mixElementsList: document.getElementById('mixElementsList'),
        tabButtons: document.querySelectorAll('.tab-button'),
        tabContents: document.querySelectorAll('.tab-content'),
        noiseDuration: document.getElementById('noiseDuration'),
        toneSlider: document.getElementById('toneSlider'),
        widthSlider: document.getElementById('widthSlider'),
        generateMainBtn: document.getElementById('generateMainBtn'),
        previewLight: document.getElementById('preview-light-background'),
        previewText: document.getElementById('preview-guide-text'),
        previewAudio: document.getElementById('previewAudio'),
        previewToggleBtn: document.getElementById('previewToggleBtn'),
        previewBPM: document.getElementById('previewBPM'),
        previewMinVol: document.getElementById('previewMinVol'),
        previewMaxVol: document.getElementById('previewMaxVol'),
        saveTrackBtn: document.getElementById('saveTrackBtn'),
    };
    let audioCtx, gainNode, sourceNode;

    async function apiCall(url, method = 'POST', body = null) {
        try {
            const options = { method, headers: { 'Content-Type': 'application/json' } };
            if (body) options.body = JSON.stringify(body);
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

    async function loadLibrary() {
        try {
            const audioFiles = await fetch('/api/get-audio-files').then(res => res.json());
            const populate = (list, files) => {
                list.innerHTML = '';
                if (!files) return;
                files.forEach(file => {
                    const li = document.createElement('li');
                    li.className = `preset-list-item ${file.is_global ? 'is-global' : 'is-user'}`;
                    const uploaderTag = file.uploader === 'system' ? '(内置)' : `(${file.uploader})`;
                    li.innerHTML = `<span class="preset-name">${file.name} <em class="owner-tag">${uploaderTag}</em></span>`;
                    li.title = `点击以添加到混音层 (即将推出)`;
                    list.appendChild(li);
                });
            };
            populate(dom.mainAudioList, audioFiles.mainsound);
            populate(dom.auxAudioList, audioFiles.plussound);
            populate(dom.mixElementsList, audioFiles.mix_elements);
        } catch (error) {
            console.error("Failed to load library:", error);
        }
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
        try {
            const params = {
                duration_s: parseInt(dom.noiseDuration.value),
                tone_cutoff_hz: parseInt(dom.toneSlider.value),
                stereo_width: parseFloat(dom.widthSlider.value),
                volume_db: -6, fade_in_ms: 1000, fade_out_ms: 2000
            };
            const result = await apiCall('/api/generate/main-noise', 'POST', params);
            state.tempFilename = result.filename;
            state.trackType = 'mainsound';
            dom.previewAudio.src = `/media/shared/mainsound/${result.filename}`;
            dom.previewToggleBtn.disabled = false;
            dom.saveTrackBtn.disabled = false;
        } catch (error) {
            // Error is already alerted in apiCall
        } finally {
            dom.generateMainBtn.textContent = '重新生成';
            dom.generateMainBtn.disabled = false;
        }
    }

    function setupPreview() {
        let breathProgress = 0, lastFrameTime = 0, breathPhase = 'inhale';
        const warmColor = '#e48737', coolColor = '#9ea9d7';
        function previewLoop(timestamp) {
            if (!state.isPlaying) return;
            state.animationFrameId = requestAnimationFrame(previewLoop);
            const cycleDuration = (60 / parseInt(dom.previewBPM.value)) * 1000;
            const phaseDuration = cycleDuration / 2;
            breathProgress += (timestamp - (lastFrameTime || timestamp)) / phaseDuration;
            if (breathProgress >= 1) {
                breathProgress = 0;
                breathPhase = breathPhase === 'inhale' ? 'exhale' : 'inhale';
                dom.previewText.textContent = breathPhase === 'inhale' ? '吸气' : '呼气';
            }
            const currentProgress = breathPhase === 'inhale' ? breathProgress : 1 - breathProgress;
            const r1=parseInt(coolColor.slice(1,3),16), g1=parseInt(coolColor.slice(3,5),16), b1=parseInt(coolColor.slice(5,7),16);
            const r2=parseInt(warmColor.slice(1,3),16), g2=parseInt(warmColor.slice(3,5),16), b2=parseInt(warmColor.slice(5,7),16);
            const r=Math.round(r1+currentProgress*(r2-r1)), g=Math.round(g1+currentProgress*(g2-g1)), b=Math.round(b1+currentProgress*(b2-b1));
            dom.previewLight.style.backgroundColor = `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;

            if (gainNode) {
                const minVol = parseFloat(dom.previewMinVol.value);
                const maxVol = parseFloat(dom.previewMaxVol.value);
                const minGain = minVol <= -80 ? 0 : Math.pow(10, minVol / 20);
                const maxGain = maxVol <= -80 ? 0 : Math.pow(10, maxVol / 20);
                gainNode.gain.value = minGain + (maxGain - minGain) * currentProgress;
            }
            lastFrameTime = timestamp;
        }

        dom.previewToggleBtn.addEventListener('click', () => {
            if (audioCtx && audioCtx.state === 'closed') {
                audioCtx = null;
            }
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                sourceNode = audioCtx.createMediaElementSource(dom.previewAudio);
                gainNode = audioCtx.createGain();
                sourceNode.connect(gainNode).connect(audioCtx.destination);
            }
            if (state.isPlaying) {
                state.isPlaying = false;
                dom.previewAudio.pause();
                dom.previewToggleBtn.textContent = '▶ 预览';
                cancelAnimationFrame(state.animationFrameId);
            } else {
                state.isPlaying = true;
                if(audioCtx.state === 'suspended') audioCtx.resume();
                dom.previewAudio.play();
                dom.previewToggleBtn.textContent = '❚❚ 暂停';
                lastFrameTime = performance.now();
                requestAnimationFrame(previewLoop);
            }
        });
    }
    
    async function saveTrack() {
        const defaultName = state.tempFilename
            .replace('temp_', '噪音_')
            .replace(/\.wav$/, '.mp3');
        const final_filename = prompt("请输入新音频的名称:", defaultName);
        if (final_filename && state.tempFilename) {
            dom.saveTrackBtn.disabled = true;
            dom.saveTrackBtn.textContent = '保存中...';
            try {
                await apiCall('/api/audio/save-temp', 'POST', {
                    temp_filename: state.tempFilename,
                    final_filename: final_filename,
                    track_type: state.trackType
                });
                alert('音频已成功保存到音乐库！');
                loadLibrary();
                state.tempFilename = null;
                state.trackType = null;
                dom.saveTrackBtn.disabled = true;
                dom.previewToggleBtn.disabled = true;
                dom.previewAudio.src = '';
            } catch (error) {
                dom.saveTrackBtn.disabled = false;
            } finally {
                dom.saveTrackBtn.textContent = '💾 保存到音乐库';
            }
        }
    }

    function initialize() {
        loadLibrary();
        setupTabs();
        setupPreview();
        dom.generateMainBtn.addEventListener('click', generateMainTrack);
        dom.saveTrackBtn.addEventListener('click', saveTrack);
    }

    initialize();
});