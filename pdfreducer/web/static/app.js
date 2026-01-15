// PDF Reducer Web Interface

class PDFReducerApp {
    constructor() {
        this.jobs = new Map();
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.mode = 'reduce'; // 'reduce' or 'extract'

        // Default option values
        this.defaults = {
            dpi: 150,
            quality: 80,
            aggressive: false,
            grayscale: false,
            removeImages: false,
            stripMetadata: false,
        };

        this.initElements();
        this.initEventListeners();
        this.connectWebSocket();
    }

    initElements() {
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.queueList = document.getElementById('queueList');
        this.clearCompletedBtn = document.getElementById('clearCompleted');
        this.downloadAllBtn = document.getElementById('downloadAll');
        this.processAllBtn = document.getElementById('processAll');
        this.resetOptionsBtn = document.getElementById('resetOptions');

        // Options
        this.dpiSlider = document.getElementById('dpi');
        this.dpiValue = document.getElementById('dpiValue');
        this.dpiGroup = this.dpiSlider.closest('.option-group');

        this.qualitySlider = document.getElementById('quality');
        this.qualityValue = document.getElementById('qualityValue');
        this.qualityGroup = this.qualitySlider.closest('.option-group');

        this.aggressiveCheckbox = document.getElementById('aggressive');
        this.grayscaleCheckbox = document.getElementById('grayscale');
        this.removeImagesCheckbox = document.getElementById('removeImages');
        this.stripMetadataCheckbox = document.getElementById('stripMetadata');

        // Mode toggle
        this.modeButtons = document.querySelectorAll('.mode-btn');
        this.reduceOptions = document.getElementById('reduceOptions');
        this.extractOptions = document.getElementById('extractOptions');
    }

    initEventListeners() {
        // Drop zone events
        this.dropZone.addEventListener('click', () => this.fileInput.click());
        this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Slider events
        this.dpiSlider.addEventListener('input', () => {
            this.dpiValue.textContent = this.dpiSlider.value;
        });
        this.qualitySlider.addEventListener('input', () => {
            this.qualityValue.textContent = this.qualitySlider.value;
        });

        // Remove images checkbox - disables image-related options
        this.removeImagesCheckbox.addEventListener('change', () => {
            this.updateImageOptionsState();
        });

        // Reset button
        this.resetOptionsBtn.addEventListener('click', () => this.resetOptions());

        // Clear completed button
        this.clearCompletedBtn.addEventListener('click', () => this.clearCompleted());

        // Download all button
        this.downloadAllBtn.addEventListener('click', () => this.downloadAll());

        // Process all button
        this.processAllBtn.addEventListener('click', () => this.processAll());

        // Mode toggle buttons
        this.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.setMode(btn.dataset.mode));
        });
    }

    setMode(mode) {
        this.mode = mode;

        // Update button states
        this.modeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Show/hide options
        this.reduceOptions.style.display = mode === 'reduce' ? 'grid' : 'none';
        this.extractOptions.style.display = mode === 'extract' ? 'grid' : 'none';
    }

    updateImageOptionsState() {
        const disabled = this.removeImagesCheckbox.checked;

        // Disable/enable DPI slider
        this.dpiSlider.disabled = disabled;
        this.dpiGroup.classList.toggle('disabled', disabled);

        // Disable/enable quality slider
        this.qualitySlider.disabled = disabled;
        this.qualityGroup.classList.toggle('disabled', disabled);

        // Disable/enable grayscale checkbox
        this.grayscaleCheckbox.disabled = disabled;
        this.grayscaleCheckbox.closest('.checkbox-label').style.opacity = disabled ? '0.4' : '1';
        this.grayscaleCheckbox.closest('.checkbox-label').style.cursor = disabled ? 'not-allowed' : 'pointer';
    }

    resetOptions() {
        // Reset sliders
        this.dpiSlider.value = this.defaults.dpi;
        this.dpiValue.textContent = this.defaults.dpi;

        this.qualitySlider.value = this.defaults.quality;
        this.qualityValue.textContent = this.defaults.quality;

        // Reset checkboxes
        this.aggressiveCheckbox.checked = this.defaults.aggressive;
        this.grayscaleCheckbox.checked = this.defaults.grayscale;
        this.removeImagesCheckbox.checked = this.defaults.removeImages;
        this.stripMetadataCheckbox.checked = this.defaults.stripMetadata;

        // Update disabled states
        this.updateImageOptionsState();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connectWebSocket(), 1000 * this.reconnectAttempts);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'initial_jobs':
                data.jobs.forEach(job => {
                    this.jobs.set(job.id, job);
                });
                this.renderQueue();
                break;

            case 'job_update':
                this.jobs.set(data.job.id, data.job);
                this.renderQueue();
                break;
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropZone.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropZone.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropZone.classList.remove('drag-over');

        const files = Array.from(e.dataTransfer.files).filter(
            file => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
        );

        files.forEach(file => this.uploadFile(file));
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        files.forEach(file => this.uploadFile(file));
        this.fileInput.value = '';
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', this.mode);
        formData.append('dpi', this.dpiSlider.value);
        formData.append('quality', this.qualitySlider.value);
        // Send boolean values as strings "true" or "false"
        formData.append('aggressive', this.aggressiveCheckbox.checked.toString());
        formData.append('grayscale', this.grayscaleCheckbox.checked.toString());
        formData.append('remove_images', this.removeImagesCheckbox.checked.toString());
        formData.append('strip_metadata', this.stripMetadataCheckbox.checked.toString());

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.error) {
                console.error('Upload error:', data.error);
                alert(`Error: ${data.error}`);
                return;
            }

            // Job will be added via WebSocket
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Upload failed. Please try again.');
        }
    }

    async clearCompleted() {
        try {
            await fetch('/api/jobs/clear-completed', { method: 'POST' });

            // Remove completed jobs from local state
            for (const [id, job] of this.jobs) {
                if (job.status === 'completed' || job.status === 'failed') {
                    this.jobs.delete(id);
                }
            }

            this.renderQueue();
        } catch (error) {
            console.error('Failed to clear completed:', error);
        }
    }

    async deleteJob(jobId) {
        try {
            await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
            this.jobs.delete(jobId);
            this.renderQueue();
        } catch (error) {
            console.error('Failed to delete job:', error);
        }
    }

    downloadJob(jobId) {
        window.location.href = `/api/download/${jobId}`;
    }

    downloadAll() {
        window.location.href = '/api/download-all';
    }

    async processAll() {
        try {
            await fetch('/api/process', { method: 'POST' });
            // Jobs will be updated via WebSocket
        } catch (error) {
            console.error('Failed to start processing:', error);
        }
    }

    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    renderQueue() {
        // Count jobs by status
        const completedCount = Array.from(this.jobs.values())
            .filter(job => job.status === 'completed').length;
        const pendingCount = Array.from(this.jobs.values())
            .filter(job => job.status === 'pending').length;

        // Show/hide Process button (when there are pending jobs)
        this.processAllBtn.style.display = pendingCount > 0 ? 'inline-block' : 'none';

        // Show/hide Download All button
        this.downloadAllBtn.style.display = completedCount >= 2 ? 'inline-block' : 'none';

        if (this.jobs.size === 0) {
            this.queueList.innerHTML = '<div class="queue-empty">No files in queue</div>';
            return;
        }

        const sortedJobs = Array.from(this.jobs.values()).sort((a, b) => {
            return new Date(b.created_at) - new Date(a.created_at);
        });

        this.queueList.innerHTML = sortedJobs.map(job => this.renderJobItem(job)).join('');

        // Add event listeners
        this.queueList.querySelectorAll('.btn-download').forEach(btn => {
            btn.addEventListener('click', () => this.downloadJob(btn.dataset.jobId));
        });

        this.queueList.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', () => this.deleteJob(btn.dataset.jobId));
        });
    }

    renderJobItem(job) {
        const statusIcon = this.getStatusIcon(job.status);
        const details = this.getJobDetails(job);
        const actions = this.getJobActions(job);
        const progressBar = job.status === 'processing' ? this.getProgressBar(job.progress) : '';

        return `
            <div class="queue-item" data-job-id="${job.id}">
                <div class="queue-item-status ${this.getStatusClass(job.status)}">
                    ${statusIcon}
                </div>
                <div class="queue-item-info">
                    <div class="queue-item-filename">${this.escapeHtml(job.filename)}</div>
                    <div class="queue-item-details">${details}</div>
                    ${progressBar}
                </div>
                <div class="queue-item-actions">
                    ${actions}
                </div>
            </div>
        `;
    }

    getStatusIcon(status) {
        switch (status) {
            case 'pending':
                return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>';
            case 'processing':
                return '<div class="spinner"></div>';
            case 'completed':
                return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
            case 'failed':
                return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
            default:
                return '';
        }
    }

    getStatusClass(status) {
        return `status-${status}`;
    }

    getJobDetails(job) {
        switch (job.status) {
            case 'pending':
                const modeLabel = job.mode === 'extract' ? 'Extract text' : 'Reduce';
                return `${this.formatSize(job.original_size)} - ${modeLabel} - Waiting...`;
            case 'processing':
                return job.message || 'Processing...';
            case 'completed':
                if (job.mode === 'extract') {
                    return `${this.formatSize(job.original_size)} → ${this.formatSize(job.reduced_size)} text extracted`;
                }
                const reduction = ((job.original_size - job.reduced_size) / job.original_size * 100).toFixed(0);
                const isPositive = job.reduced_size < job.original_size;
                return `${this.formatSize(job.original_size)} → ${this.formatSize(job.reduced_size)} <span class="queue-item-size ${isPositive ? '' : 'negative'}">(${isPositive ? '-' : '+'}${Math.abs(reduction)}%)</span>`;
            case 'failed':
                return `<span class="status-failed">${job.error || 'Processing failed'}</span>`;
            default:
                return '';
        }
    }

    getProgressBar(progress) {
        return `
            <div class="progress-bar">
                <div class="progress-bar-fill" style="width: ${progress}%"></div>
            </div>
        `;
    }

    getJobActions(job) {
        const actions = [];

        if (job.status === 'completed') {
            actions.push(`
                <button class="btn-icon btn-download" data-job-id="${job.id}" title="Download">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                </button>
            `);
        }

        if (job.status === 'completed' || job.status === 'failed') {
            actions.push(`
                <button class="btn-icon btn-delete" data-job-id="${job.id}" title="Remove">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            `);
        }

        return actions.join('');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PDFReducerApp();
});
