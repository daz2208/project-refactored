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
                        <button class="icon-btn" onclick="deleteDocument(${r.doc_id})" title="Delete" style="background: none; border: none; cursor: pointer; font-size: 1.2rem;">🗑️</button>
                    </div>
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
                    <pre>${highlightSearchTerms(escapeHtml(r.content), searchQuery)}</pre>
                </details>
            </div>
        `).join('');
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

    // Update content visibility
    document.getElementById('searchContent').classList.add('hidden');
    document.getElementById('analyticsContent').classList.add('hidden');

    if (tabName === 'search') {
        document.getElementById('searchTab').classList.add('active');
        document.getElementById('searchContent').classList.remove('hidden');
    } else if (tabName === 'analytics') {
        document.getElementById('analyticsTab').classList.add('active');
        document.getElementById('analyticsContent').classList.remove('hidden');
        // Load analytics when tab is shown
        loadAnalytics();
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
