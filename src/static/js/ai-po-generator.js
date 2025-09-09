/**
 * AI PO Generator - Handles AI-powered purchase order generation
 */

class AIPOGenerator {
    constructor() {
        this.isGenerating = false;
        this.currentSession = null;
        this.pollTimer = null;
        console.log('[AIPOGenerator] Initialized');
    }

    /**
     * Generate PO using AI agents
     */
    async generatePO(medicationIds) {
        console.log('[AIPOGenerator] Starting generation for medications:', medicationIds);

        if (this.isGenerating) {
            console.warn('[AIPOGenerator] Generation already in progress');
            return;
        }

        if (!medicationIds || medicationIds.length === 0) {
            console.error('[AIPOGenerator] No medications selected');
            this.showToast('Please select medications first', 'warning');
            return;
        }

        console.log(`[AIPOGenerator] Processing ${medicationIds.length} medications`);

        // Check AI configuration first
        console.log('[AIPOGenerator] Checking AI configuration...');
        const configStatus = await this.checkAIConfig();
        console.log('[AIPOGenerator] Config status:', configStatus);

        if (!configStatus.configured) {
            console.error('[AIPOGenerator] AI not configured - missing OpenAI API key');
            this.showToast('AI not configured. Please set OpenAI API key in .env file', 'error');
            return;
        }

        this.isGenerating = true;
        this.showProgressModal();

        try {
            // Kick off async AI generation
            console.log('[AIPOGenerator] Sending request to backend API (async kickoff)...');
            const requestPayload = { medication_ids: medicationIds };

            const response = await fetch('/api/purchase-orders/generate-ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestPayload)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'AI generation failed to start');
            }

            const kick = await response.json();
            this.currentSession = kick.session_id;
            console.log('[AIPOGenerator] Session ID:', this.currentSession);

            // Begin polling for status until result is ready
            await this.pollUntilComplete(this.currentSession);
        } catch (error) {
            console.error('[AIPOGenerator] Error during generation:', error);
            this.showToast(`AI generation failed: ${error.message}`, 'error');
            this.hideProgressModal();
            this.isGenerating = false;
        }
    }

    async pollUntilComplete(sessionId) {
        const poll = async () => {
            try {
                const res = await fetch(`/api/purchase-orders/ai-status/${sessionId}`);
                const status = await res.json();
                // Update progress UI
                if (status.progress) this.updateProgress(status.progress);

                if (status.status === 'failed') {
                    throw new Error(status.error || 'Generation failed');
                }

                if (status.has_result) {
                    // Fetch the final result
                    const resultRes = await fetch(`/api/purchase-orders/ai-result/${sessionId}`);
                    if (resultRes.status === 202) return; // still processing
                    const result = await resultRes.json();
                    this.handleGenerationComplete(result);
                    this.isGenerating = false;
                    clearInterval(this.pollTimer);
                    this.pollTimer = null;
                }
            } catch (e) {
                console.error('[AIPOGenerator] Polling error:', e);
                this.showToast(e.message || 'An error occurred while polling status', 'error');
                this.hideProgressModal();
                this.isGenerating = false;
                clearInterval(this.pollTimer);
                this.pollTimer = null;
            }
        };

        // poll immediately and then every 1.5s
        await poll();
        this.pollTimer = setInterval(poll, 1500);
    }

    /**
     * Check if AI is configured
     */
    async checkAIConfig() {
        try {
            const response = await fetch('/api/ai/config-status');
            const status = await response.json();
            return status;
        } catch (error) {
            console.error('[AIPOGenerator] Failed to check AI config:', error);
            return { configured: false };
        }
    }

    /**
     * Show progress modal
     */
    showProgressModal() {
        // Remove existing modal if any
        this.hideProgressModal();

        const modal = document.createElement('div');
        modal.id = 'aiProgressModal';
        modal.className = 'ai-modal-overlay';
        modal.innerHTML = `
            <div class="ai-modal">
                <div class="ai-modal-header">
                    <h3>AI Purchase Order Generation</h3>
                    <div class="ai-badge">AI</div>
                </div>
                <div class="ai-modal-body">
                    <div class="ai-progress-container">
                        <div class="ai-progress-bar">
                            <div class="ai-progress-fill" id="aiProgressFill"></div>
                        </div>
                        <div class="ai-progress-text" id="aiProgressText">Initializing...</div>
                    </div>
                    <div class="ai-steps">
                        <div class="ai-step" id="step-forecast">
                            <div class="ai-step-icon">DF</div>
                            <div class="ai-step-content">
                                <div class="ai-step-title">Demand Forecasting</div>
                                <div class="ai-step-desc">Analyzing consumption patterns</div>
                            </div>
                        </div>
                        <div class="ai-step" id="step-adjustment">
                            <div class="ai-step-icon">CA</div>
                            <div class="ai-step-content">
                                <div class="ai-step-title">Context Adjustment</div>
                                <div class="ai-step-desc">Applying market and seasonal factors</div>
                            </div>
                        </div>
                        <div class="ai-step" id="step-supplier">
                            <div class="ai-step-icon">SO</div>
                            <div class="ai-step-content">
                                <div class="ai-step-title">Supplier Optimization</div>
                                <div class="ai-step-desc">Selecting suppliers and allocations</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * Hide progress modal
     */
    hideProgressModal() {
        const modal = document.getElementById('aiProgressModal');
        if (modal) modal.remove();
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    /**
     * Update progress display
     */
    updateProgress(progress) {
        if (!progress) return;
        const fill = document.getElementById('aiProgressFill');
        const text = document.getElementById('aiProgressText');

        if (fill && typeof progress.percent_complete === 'number') {
            fill.style.width = `${progress.percent_complete}%`;
        }
        if (text) {
            text.textContent = progress.current_action || 'Processing...';
        }

        // Update step status
        if (progress.steps_completed) {
            progress.steps_completed.forEach(step => {
                const stepEl = document.getElementById(`step-${step}`);
                if (stepEl) stepEl.classList.add('completed');
            });
        }

        // Highlight current step
        if (progress.current_agent) {
            const agentMap = {
                'forecast_agent': 'forecast',
                'adjustment_agent': 'adjustment',
                'supplier_agent': 'supplier'
            };
            const stepId = agentMap[progress.current_agent];
            if (stepId) {
                document.querySelectorAll('.ai-step').forEach(el => el.classList.remove('active'));
                const currentStep = document.getElementById(`step-${stepId}`);
                if (currentStep && !currentStep.classList.contains('completed')) {
                    currentStep.classList.add('active');
                }
            }
        }
    }

    /**
     * Handle generation completion
     */
    handleGenerationComplete(result) {
        this.hideProgressModal();

        // Store result for create-po page
        sessionStorage.setItem('aiPOResult', JSON.stringify(result));

        // Show completion modal with reasoning
        this.showCompletionModal(result);
    }

    /**
     * Show completion modal with reasoning
     */
    showCompletionModal(result) {
        const modal = document.createElement('div');
        modal.id = 'aiCompletionModal';
        modal.className = 'ai-modal-overlay';

        // Build reasoning HTML (expanded accordions)
        let reasoningHTML = '';
        if (result.reasoning) {
            for (const [agent, data] of Object.entries(result.reasoning)) {
                const agentName = agent.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const decisions = (data.decision_points || []).map(point => `<li>${this.escapeHtml(point)}</li>`).join('');
                reasoningHTML += `
                    <div class="ai-reasoning-section expanded">
                        <div class="ai-reasoning-header" onclick="this.parentElement.classList.toggle('expanded')">
                            <span>${agentName}</span>
                            <span class="ai-confidence">Confidence: ${(Number(data.confidence) * 100).toFixed(0)}%</span>
                        </div>
                        <div class="ai-reasoning-content">
                            ${data.summary ? `<p>${this.escapeHtml(data.summary)}</p>` : ''}
                            ${decisions ? `<ul>${decisions}</ul>` : ''}
                        </div>
                    </div>
                `;
            }
        }

        // Build summary
        const metadata = result.metadata || {};
        const itemCount = metadata.total_items || 0;
        const totalCost = metadata.total_cost || 0;
        const avgLeadTime = metadata.avg_lead_time || 0;

        modal.innerHTML = `
            <div class="ai-modal large">
                <div class="ai-modal-header">
                    <h3>AI Generation Complete</h3>
                    <button class="ai-modal-close" onclick="document.getElementById('aiCompletionModal').remove()">×</button>
                </div>
                <div class="ai-modal-body">
                    <div class="ai-summary">
                        <div class="ai-summary-card">
                            <div class="ai-summary-value">${itemCount}</div>
                            <div class="ai-summary-label">Items</div>
                        </div>
                        <div class="ai-summary-card">
                            <div class="ai-summary-value">$${Number(totalCost).toFixed(2)}</div>
                            <div class="ai-summary-label">Total Cost</div>
                        </div>
                        <div class="ai-summary-card">
                            <div class="ai-summary-value">${Number(avgLeadTime).toFixed(1)}d</div>
                            <div class="ai-summary-label">Avg Lead Time</div>
                        </div>
                    </div>
                    
                    <div class="ai-reasoning">
                        <h4>AI Agent Reasoning</h4>
                        ${reasoningHTML || '<div class="text-muted">No reasoning available</div>'}
                    </div>
                    
                    <div class="ai-actions">
                        <button class="btn btn-secondary" onclick="document.getElementById('aiCompletionModal').remove()">
                            Cancel
                        </button>
                        <button class="btn btn-primary" onclick="window.aiPOGenerator.proceedToCreatePO()">
                            Proceed to Create PO
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * Proceed to create PO page with AI result
     */
    proceedToCreatePO() {
        const modal = document.getElementById('aiCompletionModal');
        if (modal) modal.remove();
        window.location.href = '/create-po?ai=true';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        if (window.app && window.app.showToast) {
            window.app.showToast(message, type);
        } else {
            // Fallback toast
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;

            let container = document.getElementById('toastContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toastContainer';
                document.body.appendChild(container);
            }

            container.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }
    }

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return (text || '').toString().replace(/[&<>"']/g, m => map[m]);
    }
}

// Create global instance
window.aiPOGenerator = new AIPOGenerator();