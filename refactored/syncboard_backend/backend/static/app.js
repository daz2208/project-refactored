const API_BASE = 'http://localhost:8000';
let token = null;

// =============================================================================
// HELPERS
// =============================================================================

async function getErrorMessage(response) {
    /**
     * Extract error message from API response.
     * Tries to parse JSON error detail, falls back to status text.
     */
    try {
        const data = await response.json();
        return data.detail || response.statusText || 'Operation failed';
    } catch {
        return response.statusText || 'Operation failed';
    }
}

function setButtonLoading(button, isLoading, originalText = null) {
    /**
     * Set loading state on a button.
     * Disables button and changes text when loading.
     */
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.textContent = 'Loading...';
        button.style.opacity = '0.6';
    } else {
        button.disabled = false;
        button.textContent = originalText || button.dataset.originalText || button.textContent;
        button.style.opacity = '1';
        delete button.dataset.originalText;
    }
}

// =============================================================================
// AUTH
// =============================================================================

async function login(event) {
    const button = event ? event.target : null;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (button) setButtonLoading(button, true);

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
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Login error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Login');
    }
}

async function register(event) {
    const button = event ? event.target : null;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (button) setButtonLoading(button, true);

    try {
        const res = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });

        if (res.ok) {
            showToast('Registered! Now login.');
        } else {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Registration error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Register');
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
            <button onclick="uploadText(event)">Upload Text</button>
        `;
    } else if (type === 'url') {
        forms.innerHTML = `
            <input type="text" id="urlInput" placeholder="https://youtube.com/... or https://example.com/article">
            <button onclick="uploadUrl(event)">Upload URL</button>
            <p style="color: #888; font-size: 0.9rem; margin-top: 5px;">YouTube videos may take 30-120 seconds</p>
        `;
    } else if (type === 'file') {
        forms.innerHTML = `
            <input type="file" id="fileInput" accept=".pdf,.txt,.docx,.mp3,.wav">
            <button onclick="uploadFile(event)">Upload File</button>
        `;
    } else if (type === 'image') {
        forms.innerHTML = `
            <input type="file" id="imageInput" accept="image/*">
            <input type="text" id="imageDesc" placeholder="Optional description (what is this image for?)">
            <button onclick="uploadImage(event)">Upload Image</button>
        `;
    }
}

async function uploadText(event) {
    const button = event ? event.target : null;
    const content = document.getElementById('textContent').value;

    if (!content.trim()) {
        showToast('Content cannot be empty', 'error');
        return;
    }

    if (button) setButtonLoading(button, true);

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
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Upload Text');
    }
}

async function uploadUrl(event) {
    const button = event ? event.target : null;
    const url = document.getElementById('urlInput').value;

    if (!url.trim()) {
        showToast('URL cannot be empty', 'error');
        return;
    }

    if (button) setButtonLoading(button, true);

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
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Upload URL');
    }
}

async function uploadFile(event) {
    const button = event ? event.target : null;
    const file = document.getElementById('fileInput').files[0];

    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }

    if (button) setButtonLoading(button, true);

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
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Upload File');
    }
}

async function uploadImage(event) {
    const button = event ? event.target : null;
    const file = document.getElementById('imageInput').files[0];
    const description = document.getElementById('imageDesc').value;

    if (!file) {
        showToast('Please select an image', 'error');
        return;
    }

    if (button) setButtonLoading(button, true);

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
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Upload error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Upload Image');
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
        <div class="cluster-card">
            <div onclick="loadCluster(${c.id})" style="cursor: pointer;">
                <h3>${c.name}</h3>
                <p>${c.doc_count} documents • ${c.skill_level}</p>
                <div class="concepts-list">
                    ${c.primary_concepts.slice(0, 3).map(concept =>
                        `<span class="concept-tag">${concept}</span>`
                    ).join('')}
                </div>
            </div>
            <div style="margin-top: 10px; display: flex; gap: 5px; font-size: 0.85rem;">
                <button onclick="event.stopPropagation(); exportCluster(${c.id}, 'json')" style="padding: 4px 8px; font-size: 0.8rem;" title="Export as JSON">📄 JSON</button>
                <button onclick="event.stopPropagation(); exportCluster(${c.id}, 'markdown')" style="padding: 4px 8px; font-size: 0.8rem;" title="Export as Markdown">📝 MD</button>
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

function displaySearchResults(results, searchQuery = '') {
    const area = document.getElementById('resultsArea');

    if (results.length === 0) {
        area.innerHTML = '<p style="color: #666;">No results found</p>';
        return;
    }

    area.innerHTML = `<h3>Search Results (${results.length})</h3>` +
        results.map(r => `
            <div class="search-result">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>Doc ${r.doc_id}</strong>
                    <div style="display: flex; gap: 8px;">
                        <span style="color: #888;">Score: ${r.score.toFixed(3)}</span>
                        <button class="icon-btn" onclick="showTagMenuForDocument(${r.doc_id})" title="Add Tag" style="background: none; border: none; cursor: pointer; font-size: 1.2rem;">🏷️</button>
                        <button class="icon-btn" onclick="deleteDocument(${r.doc_id})" title="Delete" style="background: none; border: none; cursor: pointer; font-size: 1.2rem;">🗑️</button>
                    </div>
                </div>
                <p style="font-size: 0.9rem; color: #aaa; margin: 5px 0;">
                    ${r.metadata.source_type} •
                    Cluster: ${r.cluster?.name || 'None'} •
                    ${r.metadata.skill_level}
                </p>
                <div id="doc-tags-${r.doc_id}" class="document-tags" style="margin: 8px 0;">
                    <!-- Tags will be loaded here -->
                </div>
                <div class="concepts-list">
                    ${r.metadata.concepts.slice(0, 5).map(c =>
                        `<span class="concept-tag">${c.name}</span>`
                    ).join('')}
                </div>
                <details style="margin-top: 10px;">
                    <summary>View Full Content (${r.content.length} chars)</summary>
                    <pre>${highlightSearchTerms(escapeHtml(r.content), searchQuery)}</pre>
                </details>
            </div>
        `).join('');

    // Load tags for each document
    results.forEach(r => {
        loadDocumentTags(r.doc_id);
    });
}

function highlightSearchTerms(text, query) {
    if (!query || !text) return text;
    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
    if (terms.length === 0) return text;

    let highlighted = text;
    terms.forEach(term => {
        const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
        highlighted = highlighted.replace(regex, '<mark style="background: #ffaa00; padding: 2px;">$1</mark>');
    });
    return highlighted;
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function deleteDocument(docId) {
    if (!confirm(`Delete document ${docId}? This cannot be undone.`)) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/documents/${docId}`, {
            method: 'DELETE',
            headers: {'Authorization': `Bearer ${token}`}
        });

        if (res.ok) {
            showToast(`Document ${docId} deleted`, 'success');
            const query = document.getElementById('searchQuery').value;
            if (query.trim()) {
                searchKnowledge();
            } else {
                loadClusters();
            }
        } else {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Delete failed: ' + e.message, 'error');
    }
}

// =============================================================================
// BUILD SUGGESTIONS
// =============================================================================

async function whatCanIBuild(event) {
    const button = event ? event.target : null;

    if (button) setButtonLoading(button, true);

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
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'What Can I Build?');
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
// AI GENERATION (RAG)
// =============================================================================

function showAIGenerator() {
    const panel = document.getElementById('aiGeneratorPanel');
    panel.classList.remove('hidden');
    document.getElementById('aiPrompt').focus();
}

function hideAIGenerator() {
    const panel = document.getElementById('aiGeneratorPanel');
    panel.classList.add('hidden');
    document.getElementById('aiResponseArea').style.display = 'none';
    document.getElementById('aiPrompt').value = '';
    document.getElementById('aiResponse').textContent = '';
}

async function generateWithAI(event) {
    const button = event ? event.target : null;
    const prompt = document.getElementById('aiPrompt').value.trim();
    const model = document.getElementById('aiModelSelect').value;

    if (!prompt) {
        showToast('Please enter a prompt', 'error');
        return;
    }

    if (button) setButtonLoading(button, true);

    try {
        const res = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ prompt, model })
        });

        if (res.ok) {
            const data = await res.json();
            displayAIResponse(data.response);
        } else {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('AI Generation error: ' + e.message, 'error');
    } finally {
        if (button) setButtonLoading(button, false, 'Generate');
    }
}

function displayAIResponse(response) {
    const responseArea = document.getElementById('aiResponseArea');
    const responseDiv = document.getElementById('aiResponse');

    responseDiv.textContent = response;
    responseArea.style.display = 'block';

    showToast('AI response generated successfully', 'success');
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
// EXPORT FUNCTIONALITY (Phase 4)
// =============================================================================

async function exportCluster(clusterId, format = 'json') {
    try {
        const res = await fetch(`${API_BASE}/export/cluster/${clusterId}?format=${format}`, {
            headers: {'Authorization': `Bearer ${token}`}
        });

        if (!res.ok) {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
            return;
        }

        const data = await res.json();

        // Download file
        if (format === 'markdown') {
            downloadFile(data.content, `cluster_${clusterId}_${data.cluster_name}.md`, 'text/markdown');
        } else {
            downloadFile(JSON.stringify(data, null, 2), `cluster_${clusterId}.json`, 'application/json');
        }

        showToast(`Cluster exported as ${format.toUpperCase()}`, 'success');
    } catch (e) {
        showToast('Export failed: ' + e.message, 'error');
    }
}

async function exportAll(format = 'json') {
    if (!confirm(`Export entire knowledge bank as ${format.toUpperCase()}?`)) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/export/all?format=${format}`, {
            headers: {'Authorization': `Bearer ${token}`}
        });

        if (!res.ok) {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
            return;
        }

        const data = await res.json();

        // Download file
        const timestamp = new Date().toISOString().split('T')[0];
        if (format === 'markdown') {
            downloadFile(data.content, `knowledge_bank_${timestamp}.md`, 'text/markdown');
        } else {
            downloadFile(JSON.stringify(data, null, 2), `knowledge_bank_${timestamp}.json`, 'application/json');
        }

        showToast('Full export complete!', 'success');
    } catch (e) {
        showToast('Export failed: ' + e.message, 'error');
    }
}

function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// =============================================================================
// KEYBOARD SHORTCUTS (Phase 4)
// =============================================================================

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+K or Cmd+K: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('searchQuery');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        // Esc: Clear search or close modals
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('searchQuery');
            if (searchInput && searchInput.value) {
                searchInput.value = '';
                document.getElementById('resultsArea').innerHTML = '';
            }
        }

        // N: Scroll to top (for new upload)
        if (e.key === 'n' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            // Only if not in an input field
            if (document.activeElement.tagName !== 'INPUT' &&
                document.activeElement.tagName !== 'TEXTAREA') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }
    });

    console.log('⌨️  Keyboard shortcuts enabled: Ctrl+K (search), Esc (clear), N (scroll to top)');
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

// Set up search input debouncing and keyboard shortcuts
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchQuery');
    if (searchInput) {
        searchInput.addEventListener('input', debounceSearch);
    }

    // Enable keyboard shortcuts (Phase 4)
    setupKeyboardShortcuts();
});

// =============================================================================
// Analytics Dashboard (Phase 7.1)
// =============================================================================

let analyticsCharts = {};

// Tab switching
function showTab(tabName) {
    // Update tab buttons
    document.getElementById('searchTab').classList.remove('active');
    document.getElementById('analyticsTab').classList.remove('active');
    document.getElementById('advancedTab').classList.remove('active');

    // Update content visibility
    document.getElementById('searchContent').classList.add('hidden');
    document.getElementById('analyticsContent').classList.add('hidden');
    document.getElementById('advancedContent').classList.add('hidden');

    if (tabName === 'search') {
        document.getElementById('searchTab').classList.add('active');
        document.getElementById('searchContent').classList.remove('hidden');
    } else if (tabName === 'analytics') {
        document.getElementById('analyticsTab').classList.add('active');
        document.getElementById('analyticsContent').classList.remove('hidden');
        // Load analytics when tab is shown
        loadAnalytics();
    } else if (tabName === 'advanced') {
        document.getElementById('advancedTab').classList.add('active');
        document.getElementById('advancedContent').classList.remove('hidden');
        // Load data for advanced features
        loadTags();
        loadSavedSearches();
    }
}

// Load analytics data
async function loadAnalytics() {
    const timePeriod = document.getElementById('timePeriodSelect').value;

    try {
        const response = await fetch(`http://localhost:8000/analytics?time_period=${timePeriod}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load analytics');
        }

        const data = await response.json();

        // Render all analytics sections
        renderOverviewStats(data.overview);
        renderTimeSeriesChart(data.time_series);
        renderClusterChart(data.cluster_distribution);
        renderSkillLevelChart(data.skill_level_distribution);
        renderSourceTypeChart(data.source_type_distribution);
        renderTopConcepts(data.top_concepts);
        renderRecentActivity(data.recent_activity);

    } catch (error) {
        console.error('Analytics error:', error);
        alert('Failed to load analytics: ' + error.message);
    }
}

// Render overview statistics
function renderOverviewStats(overview) {
    const container = document.getElementById('overviewStats');

    container.innerHTML = `
        <div class="stat-card">
            <h4>Total Documents</h4>
            <div class="stat-value">${overview.total_documents}</div>
            <div class="stat-change">+${overview.documents_today} today</div>
        </div>
        <div class="stat-card">
            <h4>Total Clusters</h4>
            <div class="stat-value">${overview.total_clusters}</div>
        </div>
        <div class="stat-card">
            <h4>Total Concepts</h4>
            <div class="stat-value">${overview.total_concepts}</div>
        </div>
        <div class="stat-card">
            <h4>This Week</h4>
            <div class="stat-value">${overview.documents_this_week}</div>
            <div class="stat-change">Documents added</div>
        </div>
        <div class="stat-card">
            <h4>This Month</h4>
            <div class="stat-value">${overview.documents_this_month}</div>
            <div class="stat-change">Documents added</div>
        </div>
    `;
}

// Render time series chart
function renderTimeSeriesChart(timeSeriesData) {
    const ctx = document.getElementById('timeSeriesChart');

    // Destroy existing chart if it exists
    if (analyticsCharts.timeSeries) {
        analyticsCharts.timeSeries.destroy();
    }

    analyticsCharts.timeSeries = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeSeriesData.labels,
            datasets: [{
                label: 'Documents Added',
                data: timeSeriesData.data,
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#e0e0e0'
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#888' },
                    grid: { color: '#333' }
                },
                y: {
                    ticks: { color: '#888' },
                    grid: { color: '#333' },
                    beginAtZero: true
                }
            }
        }
    });

    // Set canvas height
    ctx.style.height = '300px';
}

// Render cluster distribution chart
function renderClusterChart(clusterData) {
    const ctx = document.getElementById('clusterChart');

    if (analyticsCharts.cluster) {
        analyticsCharts.cluster.destroy();
    }

    analyticsCharts.cluster = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: clusterData.labels,
            datasets: [{
                label: 'Documents',
                data: clusterData.data,
                backgroundColor: '#00d4ff',
                borderColor: '#00a8cc',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#e0e0e0' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#888' },
                    grid: { color: '#333' }
                },
                y: {
                    ticks: { color: '#888' },
                    grid: { color: '#333' },
                    beginAtZero: true
                }
            }
        }
    });

    ctx.style.height = '250px';
}

// Render skill level distribution chart
function renderSkillLevelChart(skillLevelData) {
    const ctx = document.getElementById('skillLevelChart');

    if (analyticsCharts.skillLevel) {
        analyticsCharts.skillLevel.destroy();
    }

    analyticsCharts.skillLevel = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: skillLevelData.labels,
            datasets: [{
                data: skillLevelData.data,
                backgroundColor: [
                    '#00d4ff',
                    '#4ade80',
                    '#f59e0b',
                    '#ef4444'
                ],
                borderWidth: 2,
                borderColor: '#1a1a1a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e0e0e0' }
                }
            }
        }
    });

    ctx.style.height = '250px';
}

// Render source type distribution chart
function renderSourceTypeChart(sourceTypeData) {
    const ctx = document.getElementById('sourceTypeChart');

    if (analyticsCharts.sourceType) {
        analyticsCharts.sourceType.destroy();
    }

    analyticsCharts.sourceType = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: sourceTypeData.labels,
            datasets: [{
                data: sourceTypeData.data,
                backgroundColor: [
                    '#00d4ff',
                    '#4ade80',
                    '#f59e0b',
                    '#ef4444',
                    '#8b5cf6'
                ],
                borderWidth: 2,
                borderColor: '#1a1a1a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e0e0e0' }
                }
            }
        }
    });

    ctx.style.height = '250px';
}

// Render top concepts list
function renderTopConcepts(topConcepts) {
    const container = document.getElementById('topConceptsList');

    if (topConcepts.length === 0) {
        container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No concepts found</p>';
        return;
    }

    container.innerHTML = topConcepts.map(concept => `
        <div class="concept-item">
            <span class="concept-text">${concept.concept}</span>
            <span class="concept-count">${concept.count}</span>
        </div>
    `).join('');
}

// Render recent activity
function renderRecentActivity(recentActivity) {
    const container = document.getElementById('recentActivity');

    if (recentActivity.length === 0) {
        container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No recent activity</p>';
        return;
    }

    container.innerHTML = recentActivity.map(activity => {
        const date = new Date(activity.created_at);
        const timeAgo = getTimeAgo(date);

        return `
            <div class="activity-item">
                <div class="activity-info">
                    <div class="activity-type">${activity.source_type || 'Document'}</div>
                    <div class="activity-details">
                        Skill Level: ${activity.skill_level || 'Unknown'} •
                        Cluster ID: ${activity.cluster_id !== null ? activity.cluster_id : 'None'}
                    </div>
                </div>
                <div class="activity-time">${timeAgo}</div>
            </div>
        `;
    }).join('');
}

// Helper function to format time ago
function getTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
}

// =============================================================================
// Advanced Features (Phase 7.2-7.5)
// =============================================================================

// Switch between advanced feature sub-tabs
function showAdvancedFeature(featureName) {
    // Update sub-tab buttons
    const subTabs = ['duplicatesSubTab', 'tagsSubTab', 'savedSearchesSubTab', 'relationshipsSubTab'];
    subTabs.forEach(tabId => {
        document.getElementById(tabId).classList.remove('active');
    });

    // Hide all feature sections
    const sections = ['duplicatesFeature', 'tagsFeature', 'savedSearchesFeature', 'relationshipsFeature'];
    sections.forEach(sectionId => {
        document.getElementById(sectionId).classList.add('hidden');
    });

    // Show selected feature
    if (featureName === 'duplicates') {
        document.getElementById('duplicatesSubTab').classList.add('active');
        document.getElementById('duplicatesFeature').classList.remove('hidden');
    } else if (featureName === 'tags') {
        document.getElementById('tagsSubTab').classList.add('active');
        document.getElementById('tagsFeature').classList.remove('hidden');
        loadTags();
    } else if (featureName === 'savedSearches') {
        document.getElementById('savedSearchesSubTab').classList.add('active');
        document.getElementById('savedSearchesFeature').classList.remove('hidden');
        loadSavedSearches();
    } else if (featureName === 'relationships') {
        document.getElementById('relationshipsSubTab').classList.add('active');
        document.getElementById('relationshipsFeature').classList.remove('hidden');
    }
}

// =============================================================================
// Phase 7.2: Duplicate Detection
// =============================================================================

async function findDuplicates() {
    const threshold = document.getElementById('duplicateThreshold').value;
    const resultsDiv = document.getElementById('duplicatesResults');

    resultsDiv.innerHTML = '<p style="color: #888;">Searching for duplicates...</p>';

    try {
        const response = await fetch(`${API_BASE}/duplicates?threshold=${threshold}&limit=100`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        const data = await response.json();
        renderDuplicateGroups(data.duplicate_groups);

    } catch (error) {
        showToast('Failed to find duplicates: ' + error.message, 'error');
        resultsDiv.innerHTML = '<p style="color: #ff4444;">Error loading duplicates</p>';
    }
}

function renderDuplicateGroups(groups) {
    const resultsDiv = document.getElementById('duplicatesResults');

    if (groups.length === 0) {
        resultsDiv.innerHTML = '<p style="color: #888; padding: 20px;">No duplicate groups found at this threshold.</p>';
        return;
    }

    resultsDiv.innerHTML = `
        <h3>Found ${groups.length} Duplicate Groups</h3>
        ${groups.map((group, idx) => `
            <div class="duplicate-group">
                <h4>Group ${idx + 1} (${group.documents.length} documents, ${(group.avg_similarity * 100).toFixed(1)}% similar)</h4>
                ${group.documents.map(doc => `
                    <div class="duplicate-doc" style="background: #1a1a1a; padding: 10px; margin: 8px 0; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong>Doc ${doc.doc_id}</strong>
                            <div>
                                <span style="color: #888;">${doc.source_type} • ${doc.content.length} chars</span>
                            </div>
                        </div>
                        <details style="margin-top: 8px;">
                            <summary style="cursor: pointer; color: #00d4ff;">View Content</summary>
                            <pre style="background: #0a0a0a; padding: 10px; margin-top: 8px; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(doc.content.substring(0, 500))}${doc.content.length > 500 ? '...' : ''}</pre>
                        </details>
                    </div>
                `).join('')}
                <div style="margin-top: 10px;">
                    <button onclick="mergeDuplicateGroup(${idx}, ${JSON.stringify(group.documents.map(d => d.doc_id))})" style="background: #f59e0b; padding: 8px 16px;">
                        Merge Group (Keep First, Delete Others)
                    </button>
                </div>
            </div>
        `).join('')}
    `;
}

async function mergeDuplicateGroup(groupIdx, docIds) {
    const keepId = docIds[0];
    const deleteIds = docIds.slice(1);

    if (!confirm(`Keep document ${keepId} and delete ${deleteIds.length} duplicate(s)?\n\nThis cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/duplicates/merge`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                keep_doc_id: keepId,
                delete_doc_ids: deleteIds
            })
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast(`Merged successfully! Kept doc ${keepId}, deleted ${deleteIds.length} duplicate(s)`, 'success');

        // Refresh duplicate search
        findDuplicates();

    } catch (error) {
        showToast('Failed to merge duplicates: ' + error.message, 'error');
    }
}

// =============================================================================
// Phase 7.3: Tags System
// =============================================================================

async function createTag() {
    const name = document.getElementById('newTagName').value.trim();
    const color = document.getElementById('newTagColor').value;

    if (!name) {
        showToast('Tag name cannot be empty', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/tags`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name, color })
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast(`Tag "${name}" created successfully`, 'success');

        // Clear input and reload
        document.getElementById('newTagName').value = '';
        loadTags();

    } catch (error) {
        showToast('Failed to create tag: ' + error.message, 'error');
    }
}

async function loadTags() {
    try {
        const response = await fetch(`${API_BASE}/tags`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            console.error('Failed to load tags');
            return;
        }

        const data = await response.json();
        renderTags(data.tags);

    } catch (error) {
        console.error('Failed to load tags:', error);
    }
}

function renderTags(tags) {
    const container = document.getElementById('tagsListContainer');

    if (tags.length === 0) {
        container.innerHTML = '<p style="color: #888; padding: 20px;">No tags yet. Create one above!</p>';
        return;
    }

    container.innerHTML = `
        <h3>Your Tags (${tags.length})</h3>
        <div style="display: grid; gap: 10px; margin-top: 15px;">
            ${tags.map(tag => `
                <div class="tag-item" style="background: #1a1a1a; padding: 12px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="width: 20px; height: 20px; background: ${tag.color}; border-radius: 4px; display: inline-block;"></span>
                        <strong>${tag.name}</strong>
                        <span style="color: #888; font-size: 0.9rem;">(${tag.document_count} docs)</span>
                    </div>
                    <button onclick="deleteTag(${tag.id}, '${tag.name}')" style="background: #ff4444; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;">Delete</button>
                </div>
            `).join('')}
        </div>
    `;
}

async function deleteTag(tagId, tagName) {
    if (!confirm(`Delete tag "${tagName}"? This will remove it from all documents.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/tags/${tagId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast(`Tag "${tagName}" deleted`, 'success');
        loadTags();

    } catch (error) {
        showToast('Failed to delete tag: ' + error.message, 'error');
    }
}

// =============================================================================
// Document Tagging Functions
// =============================================================================

async function loadDocumentTags(docId) {
    try {
        const response = await fetch(`${API_BASE}/documents/${docId}/tags`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            console.error('Failed to load document tags');
            return;
        }

        const data = await response.json();
        renderDocumentTags(docId, data.tags || []);

    } catch (error) {
        console.error('Failed to load document tags:', error);
    }
}

function renderDocumentTags(docId, tags) {
    const container = document.getElementById(`doc-tags-${docId}`);
    if (!container) return;

    if (tags.length === 0) {
        container.innerHTML = '<span style="color: #666; font-size: 0.85rem;">No tags</span>';
        return;
    }

    container.innerHTML = tags.map(tag => `
        <span class="tag-badge" style="background: ${tag.color || '#00d4ff'}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; margin-right: 5px; display: inline-flex; align-items: center; gap: 5px;">
            ${tag.name}
            <button onclick="removeTagFromDocument(${docId}, ${tag.id}, '${tag.name}')" style="background: none; border: none; color: white; cursor: pointer; font-size: 1rem; padding: 0; line-height: 1;">×</button>
        </span>
    `).join('');
}

async function showTagMenuForDocument(docId) {
    try {
        const response = await fetch(`${API_BASE}/tags`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            showToast('Failed to load tags', 'error');
            return;
        }

        const data = await response.json();
        const tags = data.tags || [];

        if (tags.length === 0) {
            showToast('No tags available. Create tags first in the Advanced tab.', 'info');
            return;
        }

        // Create simple menu with available tags
        const tagOptions = tags.map(tag => `${tag.id}: ${tag.name}`).join('\n');
        const tagIdStr = prompt(`Select tag to add to document ${docId}:\n\n${tagOptions}\n\nEnter tag ID:`);

        if (tagIdStr) {
            const tagId = parseInt(tagIdStr);
            if (isNaN(tagId)) {
                showToast('Invalid tag ID', 'error');
                return;
            }

            await addTagToDocument(docId, tagId);
        }

    } catch (error) {
        showToast('Failed to show tag menu: ' + error.message, 'error');
    }
}

async function addTagToDocument(docId, tagId) {
    try {
        const response = await fetch(`${API_BASE}/documents/${docId}/tags/${tagId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast('Tag added to document', 'success');
        loadDocumentTags(docId);

    } catch (error) {
        showToast('Failed to add tag: ' + error.message, 'error');
    }
}

async function removeTagFromDocument(docId, tagId, tagName) {
    if (!confirm(`Remove tag "${tagName}" from document ${docId}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/documents/${docId}/tags/${tagId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast('Tag removed from document', 'success');
        loadDocumentTags(docId);

    } catch (error) {
        showToast('Failed to remove tag: ' + error.message, 'error');
    }
}

// =============================================================================
// Phase 7.4: Saved Searches
// =============================================================================

async function saveCurrentSearch() {
    const query = document.getElementById('searchQuery').value.trim();
    const name = prompt('Enter a name for this search:');

    if (!name) return;

    if (!query) {
        showToast('No search query to save', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/saved-searches`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                name,
                query,
                filters: {}
            })
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast(`Search "${name}" saved successfully`, 'success');
        loadSavedSearches();

    } catch (error) {
        showToast('Failed to save search: ' + error.message, 'error');
    }
}

async function loadSavedSearches() {
    try {
        const response = await fetch(`${API_BASE}/saved-searches`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            console.error('Failed to load saved searches');
            return;
        }

        const data = await response.json();
        renderSavedSearches(data.saved_searches);

    } catch (error) {
        console.error('Failed to load saved searches:', error);
    }
}

function renderSavedSearches(searches) {
    const container = document.getElementById('savedSearchesListContainer');

    if (searches.length === 0) {
        container.innerHTML = '<p style="color: #888; padding: 20px;">No saved searches yet. Save your frequent searches for quick access!</p>';
        return;
    }

    container.innerHTML = `
        <h3>Saved Searches (${searches.length})</h3>
        <div style="display: grid; gap: 10px; margin-top: 15px;">
            ${searches.map(search => `
                <div class="saved-search-item" style="background: #1a1a1a; padding: 12px; border-radius: 6px;">
                    <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 8px;">
                        <strong style="color: #00d4ff; flex-grow: 1; cursor: pointer;" onclick="useSavedSearch(${search.id})">${search.name}</strong>
                        <button onclick="deleteSavedSearch(${search.id}, '${search.name}')" style="background: #ff4444; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">Delete</button>
                    </div>
                    <div style="color: #888; font-size: 0.9rem; margin-bottom: 4px;">
                        Query: "${search.query}"
                    </div>
                    <div style="color: #666; font-size: 0.85rem;">
                        Used ${search.use_count} times
                        ${search.last_used_at ? ' • Last used ' + getTimeAgo(new Date(search.last_used_at)) : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function useSavedSearch(searchId) {
    try {
        const response = await fetch(`${API_BASE}/saved-searches/${searchId}/use`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        const data = await response.json();

        // Switch to search tab and execute the search
        showTab('search');
        document.getElementById('searchQuery').value = data.query;
        searchKnowledge();

    } catch (error) {
        showToast('Failed to use saved search: ' + error.message, 'error');
    }
}

async function deleteSavedSearch(searchId, searchName) {
    if (!confirm(`Delete saved search "${searchName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/saved-searches/${searchId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast(`Saved search "${searchName}" deleted`, 'success');
        loadSavedSearches();

    } catch (error) {
        showToast('Failed to delete saved search: ' + error.message, 'error');
    }
}

// =============================================================================
// Phase 7.5: Document Relationships
// =============================================================================

async function createRelationship() {
    const sourceDocId = parseInt(document.getElementById('relationshipSourceDoc').value);
    const targetDocId = parseInt(document.getElementById('relationshipTargetDoc').value);
    const relationType = document.getElementById('relationshipType').value;

    if (!sourceDocId || !targetDocId) {
        showToast('Please enter both document IDs', 'error');
        return;
    }

    if (sourceDocId === targetDocId) {
        showToast('Source and target must be different documents', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/documents/${sourceDocId}/relationships`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                target_doc_id: targetDocId,
                relationship_type: relationType
            })
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast(`Relationship created: ${sourceDocId} → ${targetDocId} (${relationType})`, 'success');

        // Clear inputs
        document.getElementById('relationshipSourceDoc').value = '';
        document.getElementById('relationshipTargetDoc').value = '';

    } catch (error) {
        showToast('Failed to create relationship: ' + error.message, 'error');
    }
}

async function viewDocumentRelationships() {
    const docId = parseInt(document.getElementById('viewRelationshipsDocId').value);

    if (!docId) {
        showToast('Please enter a document ID', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/documents/${docId}/relationships`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        const data = await response.json();
        renderDocumentRelationships(docId, data.related_documents);

    } catch (error) {
        showToast('Failed to load relationships: ' + error.message, 'error');
    }
}

function renderDocumentRelationships(docId, relationships) {
    const container = document.getElementById('relationshipsResultsContainer');

    if (relationships.length === 0) {
        container.innerHTML = `<p style="color: #888; padding: 20px;">Document ${docId} has no relationships.</p>`;
        return;
    }

    const relationshipColors = {
        'related': '#00d4ff',
        'prerequisite': '#4ade80',
        'followup': '#f59e0b',
        'alternative': '#8b5cf6',
        'supersedes': '#ef4444'
    };

    container.innerHTML = `
        <h3>Relationships for Document ${docId} (${relationships.length})</h3>
        <div style="display: grid; gap: 10px; margin-top: 15px;">
            ${relationships.map(rel => `
                <div style="background: #1a1a1a; padding: 12px; border-radius: 6px; border-left: 4px solid ${relationshipColors[rel.relationship_type] || '#666'};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>Doc ${rel.doc_id}</strong>
                            <span class="relationship-type-badge" style="background: ${relationshipColors[rel.relationship_type] || '#666'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px;">
                                ${rel.relationship_type}
                            </span>
                            <span style="color: #888; margin-left: 8px; font-size: 0.9rem;">
                                (${rel.direction})
                            </span>
                        </div>
                        <button onclick="deleteRelationship(${docId}, ${rel.doc_id})" style="background: #ff4444; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">Remove</button>
                    </div>
                    <div style="color: #888; font-size: 0.9rem; margin-top: 6px;">
                        ${rel.source_type} • ${rel.skill_level} • Cluster: ${rel.cluster_id !== null ? rel.cluster_id : 'None'}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function deleteRelationship(sourceDocId, targetDocId) {
    if (!confirm(`Delete relationship between documents ${sourceDocId} and ${targetDocId}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/documents/${sourceDocId}/relationships/${targetDocId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorMsg = await getErrorMessage(response);
            showToast(errorMsg, 'error');
            return;
        }

        showToast('Relationship deleted', 'success');

        // Refresh the view
        viewDocumentRelationships();

    } catch (error) {
        showToast('Failed to delete relationship: ' + error.message, 'error');
    }
}
