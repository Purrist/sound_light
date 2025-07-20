const state = {
    isLoggedIn: false,
    username: null,
    isAdmin: false,
    audioFiles: { mainsound: [], plussound: [], mix_elements: [] },
};

// --- API HELPER ---
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

// --- AUDIO LIST RENDERING ---
async function renderAudioLists(listMap, dropdowns = {}) {
    state.audioFiles = await apiCall('/api/get-audio-files');
    
    const populateList = (listElement, files, trackType) => {
        if (!listElement) return;
        listElement.innerHTML = '';
        if (!files) return;

        files.forEach(file => {
            const li = document.createElement('li');
            li.className = `tag-${file.tag}`;
            li.title = `类型: ${file.tag}, 上传者: ${file.uploader}`;

            let actionButtons = '';
            if (file.tag !== 'base') {
                if (file.tag === 'normal' || (state.isAdmin && file.tag === 'global')) {
                    actionButtons += `<button class="delete-btn" title="删除">✕</button>`;
                }
                if (state.isAdmin) {
                    if (file.tag === 'global') {
                        actionButtons += `<button class="unprotect-btn" title="解锁">🔓</button>`;
                    } else {
                        actionButtons += `<button class="protect-btn" title="锁定">🔒</button>`;
                    }
                }
            }
            
            li.innerHTML = `<span class="preset-name">${file.name}</span><div class="preset-actions">${actionButtons}</div>`;
            
            const deleteBtn = li.querySelector('.delete-btn');
            if (deleteBtn) { deleteBtn.addEventListener('click', async (e) => { e.stopPropagation(); if (confirm(`确定删除音频 "${file.name}"?`)) { try { await apiCall(`/api/delete-audio/${trackType}/${file.name}`, 'DELETE'); await renderAudioLists(listMap, dropdowns); } catch (err) { alert(`删除失败: ${err.message}`); } } }); }
            const protectBtn = li.querySelector('.protect-btn');
            if (protectBtn) { protectBtn.addEventListener('click', async (e) => { e.stopPropagation(); try { await apiCall(`/api/audio/protect/${trackType}/${file.name}`, 'POST'); await renderAudioLists(listMap, dropdowns); } catch (err) { alert(`操作失败: ${err.message}`); } }); }
            const unprotectBtn = li.querySelector('.unprotect-btn');
            if (unprotectBtn) { unprotectBtn.addEventListener('click', async (e) => { e.stopPropagation(); try { await apiCall(`/api/audio/unprotect/${trackType}/${file.name}`, 'POST'); await renderAudioLists(listMap, dropdowns); } catch (err) { alert(`操作失败: ${err.message}`); } }); }
            
            listElement.appendChild(li);
        });
    };

    for (const key in listMap) {
        populateList(listMap[key], state.audioFiles[key.replace('List', '')], key.replace('List', ''));
    }
    
    if(dropdowns.mainTrackSelect && dropdowns.auxTrackSelect) {
        const populateSelect = (sel, files, empty = false) => { sel.innerHTML = empty ? '<option value="">无</option>' : ''; if (!files) return; files.forEach(f => sel.innerHTML += `<option value="${f.name}">${f.name}</option>`); };
        populateSelect(dropdowns.mainTrackSelect, state.audioFiles.mainsound);
        populateSelect(dropdowns.auxTrackSelect, state.audioFiles.plussound, true);
    }
}

// --- FILE UPLOAD HELPER ---
async function handleUpload(file, trackType, listMap, dropdowns) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const response = await fetch(`/api/upload/${trackType}`, { method: 'POST', body: formData });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        await renderAudioLists(listMap, dropdowns);
    } catch (error) {
        alert(`上传失败: ${error.message}`);
    }
}