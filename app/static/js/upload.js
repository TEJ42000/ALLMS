/**
 * Document Upload Functionality for Admin Portal
 */

let selectedFiles = [];
let currentCourseId = null;

// Helper function to escape HTML special characters
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize upload functionality
function initUpload(courseId) {
    currentCourseId = courseId;
    
    // Set up event listeners
    const uploadBtn = document.getElementById('upload-material-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', openUploadModal);
    }
    
    const fileInput = document.getElementById('upload-files');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    const tierSelect = document.getElementById('upload-tier');
    if (tierSelect) {
        tierSelect.addEventListener('change', handleTierChange);
    }
    
    // Set up drag and drop
    const dropZone = document.getElementById('file-drop-zone');
    if (dropZone) {
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('dragleave', handleDragLeave);
        dropZone.addEventListener('drop', handleDrop);
    }
    
}

function openUploadModal() {
    if (!currentCourseId) {
        showToast('Please select a course first', 'error');
        return;
    }
    
    const modal = document.getElementById('upload-modal');
    modal.classList.remove('hidden');
    selectedFiles = [];
    updateFileList();
    
    // Reset form
    document.getElementById('upload-form').reset();
    document.getElementById('category-group').style.display = 'none';
    document.getElementById('upload-progress').classList.add('hidden');
}

function closeUploadModal() {
    const modal = document.getElementById('upload-modal');
    modal.classList.add('hidden');
    selectedFiles = [];
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    addFiles(files);
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
    
    const files = Array.from(event.dataTransfer.files);
    addFiles(files);
}

function addFiles(files) {
    for (const file of files) {
        // Check if file already added
        if (selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
            continue;
        }
        
        // Check file size (50MB limit)
        if (file.size > 50 * 1024 * 1024) {
            showToast(`File ${file.name} exceeds 50MB limit`, 'error');
            continue;
        }
        
        selectedFiles.push(file);
    }
    
    updateFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

function updateFileList() {
    const fileList = document.getElementById('file-list');
    
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        return;
    }
    
    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <div class="file-info">
                <span class="file-icon">${getFileIcon(file.name)}</span>
                <div class="file-details">
                    <div class="file-name">${escapeHtml(file.name)}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
            </div>
            <button type="button" class="file-remove" onclick="removeFile(${index})" title="Remove">×</button>
        </div>
    `).join('');
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': '📄',
        'docx': '📝',
        'pptx': '📊',
        'png': '🖼️',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'gif': '🖼️',
        'bmp': '🖼️',
        'txt': '📃',
        'md': '📃',
        'html': '🌐',
        'htm': '🌐'
    };
    return icons[ext] || '📎';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function handleTierChange(event) {
    const tier = event.target.value;
    const categoryGroup = document.getElementById('category-group');
    
    if (tier === 'course_materials') {
        categoryGroup.style.display = 'block';
    } else {
        categoryGroup.style.display = 'none';
        document.getElementById('upload-category').value = '';
    }
}

async function submitUpload() {
    if (selectedFiles.length === 0) {
        showToast('Please select at least one file', 'error');
        return;
    }
    
    const tier = document.getElementById('upload-tier').value;
    if (!tier) {
        showToast('Please select a material tier', 'error');
        return;
    }
    
    const category = document.getElementById('upload-category').value;
    const weekNumber = document.getElementById('upload-week').value;
    const description = document.getElementById('upload-description').value;
    const extractText = document.getElementById('upload-extract-text').checked;
    const generateSummary = document.getElementById('upload-generate-summary').checked;

    // Show progress
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    progressDiv.classList.remove('hidden');
    
    const submitBtn = document.getElementById('upload-submit-btn');
    submitBtn.disabled = true;
    
    let successCount = 0;
    let errorCount = 0;
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const progress = ((i + 1) / selectedFiles.length) * 100;
        
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `Uploading ${i + 1} of ${selectedFiles.length}: ${file.name}`;
        
        try {
            await uploadSingleFile(file, tier, category, weekNumber, description, extractText, generateSummary);
            successCount++;
        } catch (error) {
            console.error(`Failed to upload ${file.name}:`, error);
            errorCount++;
        }
    }
    
    // Reset
    submitBtn.disabled = false;
    progressDiv.classList.add('hidden');

    if (errorCount === 0) {
        showToast(`Successfully uploaded ${successCount} file(s)`, 'success');
        closeUploadModal();
        // Refresh the main materials list to include uploaded materials
        if (typeof renderCourseMaterialsList === 'function' && typeof currentCourse !== 'undefined') {
            renderCourseMaterialsList(currentCourse?.materials || null);
        }
    } else {
        showToast(`Uploaded ${successCount} file(s), ${errorCount} failed`, 'warning');
    }
}

async function uploadSingleFile(file, tier, category, weekNumber, description, extractText, generateSummary) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tier', tier);
    if (category) formData.append('category', category);
    if (weekNumber) formData.append('week_number', weekNumber);
    if (description) formData.append('description', description);
    formData.append('extract_text', extractText);
    formData.append('generate_summary', generateSummary);
    
    const response = await fetch(`/api/admin/courses/${currentCourseId}/materials/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
    }
    
    return await response.json();
}

async function viewMaterialText(materialId) {
    try {
        const response = await fetch(`/api/admin/courses/${currentCourseId}/materials/uploads/${materialId}/text`);
        if (!response.ok) throw new Error('Failed to load text');
        
        const data = await response.json();
        
        // Show in a modal or alert
        alert(`Extracted Text (${data.text_length} characters):\n\n${data.text.substring(0, 500)}...`);
    } catch (error) {
        showToast('Failed to load extracted text', 'error');
    }
}

async function deleteMaterial(materialId) {
    if (!confirm('Are you sure you want to delete this material? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/courses/${currentCourseId}/materials/uploads/${materialId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete material');

        showToast('Material deleted successfully', 'success');
        // Refresh the main materials list
        if (typeof renderCourseMaterialsList === 'function' && typeof currentCourse !== 'undefined') {
            renderCourseMaterialsList(currentCourse?.materials || null);
        }
    } catch (error) {
        showToast('Failed to delete material', 'error');
    }
}

// Make functions globally available
window.openUploadModal = openUploadModal;
window.closeUploadModal = closeUploadModal;
window.submitUpload = submitUpload;
window.removeFile = removeFile;
window.viewMaterialText = viewMaterialText;
window.deleteMaterial = deleteMaterial;
window.initUpload = initUpload;

