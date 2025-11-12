const API_BASE = 'http://localhost:8000';
let token = null;

// =============================================================================
// AUTH
// =============================================================================

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const res = await fetch(`${API_BASE}/token`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        
        if (res.ok) {
            const data = await res.json();
            token = data.access_token;
            localStorage.setItem('token', token);
            document.getElementById('authSection').classList.add('hidden');
            document.getElementById('mainContent').classList.remove('hidden');
            showToast('Logged in successfully');
            loadClusters();
        } else {
            showToast('Login failed', 'error');
        }
    } catch (e) {
        showToast('Login error: ' + e.message, 'error');
    }
}

async function register() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const res = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        
        if (res.ok) {
            showToast('Registered! Now login.');
        } else {
            showToast('Registration failed', 'error');
        }
    } catch (e) {
        showToast('Registration error: ' + e.message, 'error');
    }
}

// =============================================================================
// UPLOADS (NO BOARD_ID)
// =============================================================================

function showUploadType(type) {
    const forms = document.getElementById('uploadForms');
    
    if (type === 'text') {
        forms.innerHTML = `
            <textarea id="textContent" rows="8" placeholder="Paste your content..."></textarea>
            <button onclick="uploadText()">Upload Text</button>
        `;
    } else if (type === 'url') {
        forms.innerHTML = `
            <input type="text" id="urlInput" placeholder="https://youtube.com/... or https://example.com/article">
            <button onclick="uploadUrl()">Upload URL</button>
            <p style="color: #888; font-size: 0.9rem; margin-top: 5px;">YouTube videos may take 30-120 seconds</p>
        `;
    } else if (type === 'file') {
        forms.innerHTML = `
            <input type="file" id="fileInput" accept=".pdf,.txt,.docx,.mp3,.wav">
            <button onclick="uploadFile()">Upload File</button>
        `;
    } else if (type === 'image') {
        forms.innerHTML = `
            <input type="file" id="imageInput" accept="image/*">
            <input type="text" id="imageDesc" placeholder="Optional description (what is this image for?)">
            <button onclick="uploadImage()">Upload Image</button>
        `;
    }
}

async function uploadText() {
    const content = document.getElementById('textContent').value;
    
    if (!content.trim()) {
        showToast('Content cannot be empty', 'error');
        return;
    }
    
    showToast('Uploading...', 'info');
    
    try {
        const res = await fetch(`${API_BASE}/upload_text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({content})
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast(`Uploaded! Doc ${data.document_id} → Cluster ${data.cluster_id}`);
            document.getElementById('textContent').value = '';
            loadClusters();
        } else {
            showToast('Upload failed', 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    }
}

async function uploadUrl() {
    const url = document.getElementById('urlInput').value;
    
    if (!url.trim()) {
        showToast('URL cannot be empty', 'error');
        return;
    }
    
    showToast('Uploading URL... (may take 30-120s for videos)', 'info');
    
    try {
        const res = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({url})
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast(`Uploaded! Doc ${data.document_id} → Cluster ${data.cluster_id}`);
            document.getElementById('urlInput').value = '';
            loadClusters();
        } else {
            showToast('Upload failed', 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    }
}

async function uploadFile() {
    const file = document.getElementById('fileInput').files[0];
    
    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }
    
    showToast('Processing file...', 'info');
    
    try {
        const base64 = await fileToBase64(file);
        
        const res = await fetch(`${API_BASE}/upload_file`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                filename: file.name,
                content: base64
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast(`Uploaded! Doc ${data.document_id} → Cluster ${data.cluster_id}`);
            document.getElementById('fileInput').value = '';
            loadClusters();
        } else {
            showToast('Upload failed', 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    }
}

async function uploadImage() {
    const file = document.getElementById('imageInput').files[0];
    const description = document.getElementById('imageDesc').value;
    
    if (!file) {
        showToast('Please select an image', 'error');
        return;
    }
    
    showToast('Processing image with OCR...', 'info');
    
    try {
        const base64 = await fileToBase64(file);
        
        const res = await fetch(`${API_BASE}/upload_image`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                filename: file.name,
                content: base64,
                description: description || null
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast(`Uploaded! OCR extracted ${data.ocr_text_length} chars`);
            document.getElementById('imageInput').value = '';
            document.getElementById('imageDesc').value = '';
            loadClusters();
        } else {
            showToast('Upload failed', 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    }
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// =============================================================================
// CLUSTERS
// =============================================================================

async function loadClusters() {
    try {
        const res = await fetch(`${API_BASE}/clusters`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        
        if (res.ok) {
            const data = await res.json();
            displayClusters(data.clusters);
        }
    } catch (e) {
        console.error('Failed to load clusters:', e);
    }
}

function displayClusters(clusters) {
    const list = document.getElementById('clustersList');
    
    if (clusters.length === 0) {
        list.innerHTML = '<p style="color: #666;">No clusters yet. Upload some content!</p>';
        return;
    }
    
    list.innerHTML = clusters.map(c => `
        <div class="cluster-card" onclick="loadCluster(${c.id})">
            <h3>${c.name}</h3>
            <p>${c.doc_count} documents • ${c.skill_level}</p>
            <div class="concepts-list">
                ${c.primary_concepts.slice(0, 3).map(concept => 
                    `<span class="concept-tag">${concept}</span>`
                ).join('')}
            </div>
        </div>
    `).join('');
}

async function loadCluster(clusterId) {
    const query = document.getElementById('searchQuery').value || '*';
    
    try {
        const res = await fetch(
            `${API_BASE}/search_full?q=${encodeURIComponent(query)}&cluster_id=${clusterId}&top_k=20`,
            {headers: {'Authorization': `Bearer ${token}`}}
        );
        
        if (res.ok) {
            const data = await res.json();
            displaySearchResults(data.results);
        }
    } catch (e) {
        showToast('Failed to load cluster', 'error');
    }
}

// =============================================================================
// SEARCH (FULL CONTENT)
// =============================================================================

async function searchKnowledge() {
    const query = document.getElementById('searchQuery').value;
    
    if (!query.trim()) {
        showToast('Enter a search query', 'error');
        return;
    }
    
    try {
        const res = await fetch(
            `${API_BASE}/search_full?q=${encodeURIComponent(query)}&top_k=20`,
            {headers: {'Authorization': `Bearer ${token}`}}
        );
        
        if (res.ok) {
            const data = await res.json();
            displaySearchResults(data.results);
        }
    } catch (e) {
        showToast('Search failed', 'error');
    }
}

function displaySearchResults(results) {
    const area = document.getElementById('resultsArea');
    
    if (results.length === 0) {
        area.innerHTML = '<p style="color: #666;">No results found</p>';
        return;
    }
    
    area.innerHTML = `<h3>Search Results (${results.length})</h3>` +
        results.map(r => `
            <div class="search-result">
                <div style="display: flex; justify-content: space-between;">
                    <strong>Doc ${r.doc_id}</strong>
                    <span style="color: #888;">Score: ${r.score.toFixed(3)}</span>
                </div>
                <p style="font-size: 0.9rem; color: #aaa; margin: 5px 0;">
                    ${r.metadata.source_type} • 
                    Cluster: ${r.cluster?.name || 'None'} • 
                    ${r.metadata.skill_level}
                </p>
                <div class="concepts-list">
                    ${r.metadata.concepts.slice(0, 5).map(c => 
                        `<span class="concept-tag">${c.name}</span>`
                    ).join('')}
                </div>
                <details style="margin-top: 10px;">
                    <summary>View Full Content (${r.content.length} chars)</summary>
                    <pre>${escapeHtml(r.content)}</pre>
                </details>
            </div>
        `).join('');
}

// =============================================================================
// BUILD SUGGESTIONS
// =============================================================================

async function whatCanIBuild() {
    showToast('Analyzing your knowledge...', 'info');
    
    try {
        const res = await fetch(`${API_BASE}/what_can_i_build`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({max_suggestions: 5})
        });
        
        if (res.ok) {
            const data = await res.json();
            displayBuildSuggestions(data.suggestions, data.knowledge_summary);
        } else {
            showToast('Failed to generate suggestions', 'error');
        }
    } catch (e) {
        showToast('Error: ' + e.message, 'error');
    }
}

function displayBuildSuggestions(suggestions, summary) {
    const area = document.getElementById('resultsArea');
    
    if (suggestions.length === 0) {
        area.innerHTML = `
            <p style="color: #666;">
                Not enough knowledge yet to suggest builds. 
                Upload more content (${summary.total_docs} docs so far).
            </p>
        `;
        return;
    }
    
    area.innerHTML = `
        <h3>💡 Build Suggestions</h3>
        <p style="color: #aaa; margin-bottom: 20px;">
            Based on ${summary.total_docs} documents across ${summary.total_clusters} clusters
        </p>
    ` + suggestions.map((s, i) => `
        <div class="build-suggestion feasibility-${s.feasibility}">
            <h3>${i + 1}. ${s.title}</h3>
            <p style="margin: 10px 0;">${s.description}</p>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0;">
                <div>
                    <strong>Feasibility:</strong> 
                    <span class="concept-tag">${s.feasibility}</span>
                </div>
                <div>
                    <strong>Effort:</strong> ${s.effort_estimate}
                </div>
            </div>
            
            <div style="margin: 15px 0;">
                <strong>Required Skills:</strong>
                <div class="concepts-list">
                    ${s.required_skills.map(skill => 
                        `<span class="concept-tag">${skill}</span>`
                    ).join('')}
                </div>
            </div>
            
            ${s.missing_knowledge.length > 0 ? `
                <div style="margin: 15px 0;">
                    <strong style="color: #ffaa00;">Missing Knowledge:</strong>
                    <ul style="margin-left: 20px; color: #aaa;">
                        ${s.missing_knowledge.map(gap => `<li>${gap}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: #00d4ff; font-weight: 600;">
                    View Starter Steps & File Structure
                </summary>
                <div style="background: #111; padding: 15px; border-radius: 4px; margin-top: 10px;">
                    <h4>First Steps:</h4>
                    <ol style="margin-left: 20px;">
                        ${s.starter_steps.map(step => `<li>${step}</li>`).join('')}
                    </ol>
                    
                    ${s.file_structure ? `
                        <h4 style="margin-top: 15px;">File Structure:</h4>
                        <pre style="background: #0a0a0a; padding: 10px; border-radius: 4px;">${s.file_structure}</pre>
                    ` : ''}
                </div>
            </details>
        </div>
    `).join('');
}

// =============================================================================
// HELPERS
// =============================================================================

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    
    if (type === 'error') {
        toast.style.borderLeftColor = '#ff4444';
    } else if (type === 'info') {
        toast.style.borderLeftColor = '#ffaa00';
    }
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =============================================================================
// DEBOUNCING
// =============================================================================

let searchDebounceTimeout;

function debounceSearch() {
    /**
     * Debounce search input to avoid excessive API calls.
     * Waits 300ms after user stops typing before triggering search.
     */
    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(() => {
        const query = document.getElementById('searchQuery').value;
        if (query.trim()) {
            searchKnowledge();
        }
    }, 300);
}

// =============================================================================
// INIT
// =============================================================================

// Check if already logged in
const savedToken = localStorage.getItem('token');
if (savedToken) {
    token = savedToken;
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    loadClusters();
}

// Set up search input debouncing
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchQuery');
    if (searchInput) {
        searchInput.addEventListener('input', debounceSearch);
    }
});
