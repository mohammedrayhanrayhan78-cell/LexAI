import { API_BASE } from './config.js';

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    const uploadBtn = document.getElementById('upload-doc-btn');
    const fileInput = document.getElementById('pdf-file-input');
    const documentListEl = document.getElementById('document-list');

    async function loadDocuments() {
        try {
            const res = await fetch(`${API_BASE}/api/v1/documents`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const docs = await res.json();
                renderDocuments(docs);
            }
        } catch (err) {
            console.error('Failed to load documents:', err);
        }
    }

    function renderDocuments(docs) {
        documentListEl.innerHTML = '';
        if (docs.length === 0) {
            documentListEl.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">No documents uploaded yet.</p>';
            return;
        }
        docs.forEach(doc => {
            const item = document.createElement('div');
            item.className = 'document-item';
            
            const titleSpan = document.createElement('span');
            titleSpan.textContent = doc.filename;
            titleSpan.title = doc.filename;

            const statusBadge = document.createElement('span');
            statusBadge.className = `doc-status doc-status-${doc.status}`;
            statusBadge.textContent = doc.status;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'doc-delete-btn';
            deleteBtn.textContent = '×';
            deleteBtn.title = 'Delete Document';
            deleteBtn.addEventListener('click', async () => {
                if (confirm(`Delete ${doc.filename}?`)) {
                    await deleteDocument(doc.id);
                }
            });

            item.appendChild(titleSpan);
            item.appendChild(statusBadge);
            item.appendChild(deleteBtn);
            documentListEl.appendChild(item);
        });
    }

    async function uploadPdf(file) {
        const formData = new FormData();
        formData.append('file', file);

        uploadBtn.textContent = 'Uploading...';
        uploadBtn.disabled = true;

        try {
            const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (res.ok) {
                await loadDocuments();
            } else {
                const data = await res.json();
                alert(data.detail || 'Upload failed.');
            }
        } catch (err) {
            console.error('Upload error:', err);
            alert('Network error during upload.');
        } finally {
            uploadBtn.textContent = '+ Upload PDF';
            uploadBtn.disabled = false;
            fileInput.value = '';
        }
    }

    async function deleteDocument(id) {
        try {
            const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                await loadDocuments();
            }
        } catch (err) {
            console.error('Delete error:', err);
        }
    }

    uploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                alert('Please select a valid PDF file.');
                return;
            }
            uploadPdf(file);
        }
    });

    loadDocuments();
});
