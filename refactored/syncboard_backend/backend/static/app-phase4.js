// =============================================================================
// PHASE 4 FRONTEND ENHANCEMENTS
// Document management, search filters, export, keyboard shortcuts, highlighting
// =============================================================================

// =============================================================================
// DOCUMENT MANAGEMENT (Phase 4)
// =============================================================================

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
            // Refresh current view
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

async function editDocument(docId) {
    // Fetch document details
    try {
        const res = await fetch(`${API_BASE}/documents/${docId}`, {
            headers: {'Authorization': `Bearer ${token}`}
        });

        if (!res.ok) {
            showToast('Failed to load document', 'error');
            return;
        }

        const doc = await res.json();
        showEditModal(doc);
    } catch (e) {
        showToast('Error loading document: ' + e.message, 'error');
    }
}

function showEditModal(doc) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h2>Edit Document ${doc.doc_id}</h2>
            <label>Primary Topic:</label>
            <input type="text" id="editTopic" value="${doc.metadata.primary_topic}" />

            <label>Skill Level:</label>
            <select id="editSkillLevel">
                <option value="beginner" ${doc.metadata.skill_level === 'beginner' ? 'selected' : ''}>Beginner</option>
                <option value="intermediate" ${doc.metadata.skill_level === 'intermediate' ? 'selected' : ''}>Intermediate</option>
                <option value="advanced" ${doc.metadata.skill_level === 'advanced' ? 'selected' : ''}>Advanced</option>
            </select>

            <label>Cluster:</label>
            <select id="editCluster">
                <option value="null">No Cluster</option>
            </select>

            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button onclick="saveDocumentEdit(${doc.doc_id})">Save Changes</button>
                <button class="secondary" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Load clusters for dropdown
    loadClustersForEdit(doc.cluster?.id);
}

async function loadClustersForEdit(currentClusterId) {
    try {
        const res = await fetch(`${API_BASE}/clusters`, {
            headers: {'Authorization': `Bearer ${token}`}
        });

        if (res.ok) {
            const data = await res.json();
            const select = document.getElementById('editCluster');

            data.clusters.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.name;
                if (c.id === currentClusterId) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
        }
    } catch (e) {
        console.error('Failed to load clusters:', e);
    }
}

async function saveDocumentEdit(docId) {
    const updates = {
        primary_topic: document.getElementById('editTopic').value,
        skill_level: document.getElementById('editSkillLevel').value,
        cluster_id: parseInt(document.getElementById('editCluster').value) || null
    };

    try {
        const res = await fetch(`${API_BASE}/documents/${docId}/metadata`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(updates)
        });

        if (res.ok) {
            showToast('Document updated', 'success');
            closeModal();
            // Refresh search
            const query = document.getElementById('searchQuery').value;
            if (query.trim()) {
                searchKnowledge();
            }
        } else {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Update failed: ' + e.message, 'error');
    }
}

function closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.remove();
    }
}

// =============================================================================
// SEARCH FILTERS (Phase 4)
// =============================================================================

function toggleSearchFilters() {
    const filters = document.getElementById('searchFilters');
    if (filters.style.display === 'none' || !filters.style.display) {
        filters.style.display = 'block';
    } else {
        filters.style.display = 'none';
    }
}

async function searchKnowledgeWithFilters() {
    const query = document.getElementById('searchQuery').value;

    if (!query.trim()) {
        showToast('Enter a search query', 'error');
        return;
    }

    // Get filter values
    const sourceType = document.getElementById('filterSourceType')?.value || '';
    const skillLevel = document.getElementById('filterSkillLevel')?.value || '';
    const dateFrom = document.getElementById('filterDateFrom')?.value || '';
    const dateTo = document.getElementById('filterDateTo')?.value || '';

    // Build query string
    let url = `${API_BASE}/search_full?q=${encodeURIComponent(query)}&top_k=20`;
    if (sourceType) url += `&source_type=${sourceType}`;
    if (skillLevel) url += `&skill_level=${skillLevel}`;
    if (dateFrom) url += `&date_from=${dateFrom}`;
    if (dateTo) url += `&date_to=${dateTo}`;

    try {
        const res = await fetch(url, {
            headers: {'Authorization': `Bearer ${token}`}
        });

        if (res.ok) {
            const data = await res.json();
            displaySearchResults(data.results, query);

            // Show filters applied
            if (data.filters_applied) {
                const activeFilters = Object.entries(data.filters_applied)
                    .filter(([k, v]) => v)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(', ');
                if (activeFilters) {
                    showToast(`Filters: ${activeFilters}`, 'info');
                }
            }
        } else {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Search failed: ' + e.message, 'error');
    }
}

function clearSearchFilters() {
    document.getElementById('filterSourceType').value = '';
    document.getElementById('filterSkillLevel').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    searchKnowledge();
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
// CLUSTER MANAGEMENT (Phase 4)
// =============================================================================

async function renameCluster(clusterId) {
    const newName = prompt('Enter new cluster name:');
    if (!newName || !newName.trim()) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/clusters/${clusterId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ name: newName.trim() })
        });

        if (res.ok) {
            showToast('Cluster renamed', 'success');
            loadClusters();
        } else {
            const errorMsg = await getErrorMessage(res);
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('Rename failed: ' + e.message, 'error');
    }
}

// =============================================================================
// SEARCH HIGHLIGHTING (Phase 4)
// =============================================================================

function highlightSearchTerms(text, query) {
    if (!query || !text) return text;

    // Split query into terms
    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
    if (terms.length === 0) return text;

    let highlighted = text;

    terms.forEach(term => {
        // Case-insensitive replace with highlighting
        const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
        highlighted = highlighted.replace(regex, '<mark>$1</mark>');
    });

    return highlighted;
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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

        // Esc: Close modals or clear search
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal');
            if (modal) {
                closeModal();
            } else {
                const searchInput = document.getElementById('searchQuery');
                if (searchInput && searchInput.value) {
                    searchInput.value = '';
                    document.getElementById('resultsArea').innerHTML = '';
                }
            }
        }

        // N: New upload (show upload section)
        if (e.key === 'n' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            // Only if not in an input field
            if (document.activeElement.tagName !== 'INPUT' &&
                document.activeElement.tagName !== 'TEXTAREA') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        }
    });

    console.log('Keyboard shortcuts enabled: Ctrl+K (search), Esc (close), N (scroll to top)');
}
