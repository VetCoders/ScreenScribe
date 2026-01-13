const reportState = {
    findings: {},
    reviewer: '',
    modified: false,
    reportId: ''
};

function initReviewState() {
    reportState.reportId = document.body.dataset.reportId || '';

    try {
        const savedDraft = localStorage.getItem('screenscribe_draft_' + reportState.reportId);
        if (savedDraft) {
            const parsed = JSON.parse(savedDraft);
            reportState.findings = parsed.findings || {};
            reportState.reviewer = parsed.reviewer || '';
            restoreUIFromState();
            showNotification(i18n[currentLang].draftRestored);
        }
    } catch (e) {
        console.warn('localStorage not available:', e);
    }

    document.addEventListener('input', handleInputEvent);
    document.addEventListener('change', handleChangeEvent);

    document.querySelectorAll('.finding').forEach(article => {
        const findingId = article.dataset.findingId;
        if (!reportState.findings[findingId]) {
            reportState.findings[findingId] = {
                confirmed: null,
                severity: null,
                notes: '',
                actionItems: ''
            };
        }
    });

    const reviewerInput = document.getElementById('reviewer-name');
    if (reviewerInput) {
        reviewerInput.value = reportState.reviewer;
    }

    setInterval(saveDraft, 30000);

    window.addEventListener('beforeunload', (e) => {
        if (reportState.modified) {
            e.preventDefault();
            e.returnValue = 'Masz niezapisane zmiany.';
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeLightbox();
    });

    document.querySelectorAll('.thumbnail').forEach(img => {
        img.addEventListener('click', () => openLightbox(img));
    });

    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.addEventListener('click', closeLightbox);
    }
}

function handleInputEvent(e) {
    const target = e.target;
    const article = target.closest('.finding');

    if (target.id === 'reviewer-name') {
        reportState.reviewer = target.value;
        reportState.modified = true;
        return;
    }

    if (!article) return;
    const findingId = article.dataset.findingId;
    if (!reportState.findings[findingId]) {
        reportState.findings[findingId] = { confirmed: null, severity: null, notes: '', actionItems: '' };
    }

    if (target.matches('.notes textarea')) {
        reportState.findings[findingId].notes = target.value;
        reportState.modified = true;
    }
}

function handleChangeEvent(e) {
    const target = e.target;
    const article = target.closest('.finding');

    if (!article) return;
    const findingId = article.dataset.findingId;
    if (!reportState.findings[findingId]) {
        reportState.findings[findingId] = { confirmed: null, severity: null, notes: '', actionItems: '' };
    }

    if (target.matches('input[type="radio"]') && target.name.startsWith('confirmed-')) {
        const value = target.value === 'true';
        reportState.findings[findingId].confirmed = value;
        article.dataset.confirmed = value.toString();
        reportState.modified = true;
    }

    if (target.matches('.severity-select')) {
        reportState.findings[findingId].severity = target.value;
        reportState.modified = true;
    }
}

let currentLightboxFindingId = null;
let lightboxAnnotationTool = null;

function openLightbox(img) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxSvg = document.getElementById('lightbox-svg');
    const lightboxToolbar = document.getElementById('lightbox-toolbar');

    // Get finding ID from parent annotation container
    const container = img.closest('.annotation-container');
    currentLightboxFindingId = container ? container.dataset.findingId : null;

    lightboxImg.src = img.dataset.full || img.src;
    lightbox.classList.add('active');

    const setupTool = () => {
        if (lightboxAnnotationTool) {
            lightboxAnnotationTool.destroy();
        }
        lightboxAnnotationTool = new LightboxAnnotationTool(
            lightboxSvg,
            lightboxImg,
            lightboxToolbar,
            currentLightboxFindingId
        );
        lightboxToolbar.style.display = 'flex';
    };

    if (lightboxImg.complete && lightboxImg.naturalWidth > 0) {
        setupTool();
    } else {
        lightboxImg.onload = setupTool;
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    const lightboxToolbar = document.getElementById('lightbox-toolbar');

    // Save annotations before closing
    if (lightboxAnnotationTool && currentLightboxFindingId) {
        lightboxAnnotationTool.saveAnnotations();

        // Update thumbnail canvas with new annotations
        const thumbnailTool = annotationTools.get(currentLightboxFindingId);
        if (thumbnailTool) {
            thumbnailTool.loadAnnotations();
        }
        lightboxAnnotationTool.destroy();
    }

    lightbox.classList.remove('active');
    lightboxToolbar.style.display = 'none';
    lightboxAnnotationTool = null;
    currentLightboxFindingId = null;
}

function saveDraft() {
    if (!reportState.modified) return;
    try {
        const data = {
            findings: reportState.findings,
            reviewer: reportState.reviewer,
            savedAt: new Date().toISOString()
        };
        localStorage.setItem('screenscribe_draft_' + reportState.reportId, JSON.stringify(data));
        showNotification(i18n[currentLang].draftSaved);
        reportState.modified = false;
    } catch (e) {
        console.warn('Could not save draft:', e);
    }
}

function restoreUIFromState() {
    Object.entries(reportState.findings).forEach(([findingId, state]) => {
        const article = document.querySelector(`[data-finding-id="${findingId}"]`);
        if (!article) return;

        if (state.confirmed !== null) {
            article.dataset.confirmed = state.confirmed.toString();
            const radio = article.querySelector(`input[value="${state.confirmed}"]`);
            if (radio) radio.checked = true;
        }

        if (state.severity) {
            const select = article.querySelector('.severity-select');
            if (select) select.value = state.severity;
        }

        if (state.notes || state.actionItems) {
            const textarea = article.querySelector('.notes textarea');
            if (textarea) {
                // Merge notes and actionItems for backwards compatibility
                const combined = [state.notes, state.actionItems].filter(Boolean).join('\n');
                textarea.value = combined;
            }
        }
    });
}

// Shared function to build review data - used by both JSON and ZIP export
function buildReviewData() {
    const originalFindings = JSON.parse(document.getElementById('original-findings').textContent);
    const reviewedFindings = [];

    for (const f of originalFindings) {
        const review = reportState.findings[f.id] || {};
        // Remove base64 screenshot - keep it lightweight
        const { screenshot, ...findingWithoutBase64 } = f;
        const annotations = review.annotations || [];

        const result = {
            ...findingWithoutBase64,
            human_review: {
                confirmed: review.confirmed,
                severity_override: review.severity || null,
                notes: review.notes || '',
                annotations: annotations,
                reviewer: reportState.reviewer,
                reviewed_at: new Date().toISOString()
            }
        };

        // Keep original screenshot path reference (not base64)
        if (f.screenshot_path) {
            result.screenshot_path = f.screenshot_path;
        }

        reviewedFindings.push(result);
    }

    return {
        video: document.body.dataset.videoName,
        reviewed_at: new Date().toISOString(),
        reviewer: reportState.reviewer,
        findings: reviewedFindings
    };
}

function buildTodoMarkdown(originalFindings, videoName, reviewer) {
    let md = `# TODO: ${videoName}\n`;
    md += `> Recenzent: ${reviewer} | Data: ${new Date().toISOString().split('T')[0]}\n\n`;

    const bySeverity = { critical: [], high: [], medium: [], low: [] };

    originalFindings.forEach((f, idx) => {
        const review = reportState.findings[f.id] || {};
        const unified = f.unified_analysis || {};
        const severity = review.severity || unified.severity || 'medium';
        const confirmed = review.confirmed;

        if (confirmed === false) return;

        const checkbox = '[ ]';
        const summary = unified.summary || f.text || 'No description';
        const notes = review.notes || '';
        const actionItems = unified.action_items || [];

        let item = `- ${checkbox} **#${idx + 1}** [${severity.toUpperCase()}] ${summary}`;
        if (notes) item += `\n  - 📝 ${notes}`;
        if (actionItems.length > 0) {
            item += `\n  - Actions: ${actionItems.slice(0, 3).join(', ')}`;
        }

        if (bySeverity[severity]) {
            bySeverity[severity].push(item);
        } else {
            bySeverity.medium.push(item);
        }
    });

    if (bySeverity.critical.length > 0) {
        md += `## 🔴 Critical\n${bySeverity.critical.join('\n')}\n\n`;
    }
    if (bySeverity.high.length > 0) {
        md += `## 🟠 High\n${bySeverity.high.join('\n')}\n\n`;
    }
    if (bySeverity.medium.length > 0) {
        md += `## 🟡 Medium\n${bySeverity.medium.join('\n')}\n\n`;
    }
    if (bySeverity.low.length > 0) {
        md += `## 🟢 Low\n${bySeverity.low.join('\n')}\n\n`;
    }

    md += `---\n_Generated by ScreenScribe Pro_\n`;
    return md;
}

async function exportReviewedJSON() {
    if (!reportState.reviewer.trim()) {
        showNotification(i18n[currentLang].enterName);
        document.getElementById('reviewer-name').focus();
        return;
    }

    const reviewedCount = Object.values(reportState.findings).filter(f => f.confirmed !== null).length;
    if (reviewedCount === 0) {
        if (!confirm(i18n[currentLang].noReviewed)) {
            return;
        }
    }

    const output = buildReviewData();
    const videoName = document.body.dataset.videoName || 'report';
    const baseName = videoName.replace(/\.[^.]+$/, '');
    const filename = 'report_reviewed_' + baseName + '.json';
    const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Copy assumed download path to clipboard
    const downloadPath = '~/Downloads/' + filename;
    navigator.clipboard.writeText(downloadPath).then(() => {
        showNotification(i18n[currentLang].exportDone + ' ' + downloadPath);
    }).catch(() => {
        showNotification(i18n[currentLang].exportDoneSimple + ' ' + filename);
    });

    try {
        localStorage.removeItem('screenscribe_draft_' + reportState.reportId);
    } catch (e) {}
    reportState.modified = false;
}

async function exportReviewedZIP() {
    if (!reportState.reviewer.trim()) {
        showNotification(i18n[currentLang].enterName);
        document.getElementById('reviewer-name').focus();
        return;
    }

    const reviewedCount = Object.values(reportState.findings).filter(f => f.confirmed !== null).length;
    if (reviewedCount === 0) {
        if (!confirm(i18n[currentLang].noReviewed)) {
            return;
        }
    }

    showNotification(i18n[currentLang].generatingZip);

    try {
        const zip = new JSZip();
        const originalFindings = JSON.parse(document.getElementById('original-findings').textContent);
        const videoName = document.body.dataset.videoName || 'report';
        const baseName = videoName.replace(/\.[^.]+$/, '');
        const annotatedFolder = zip.folder('annotated');

        const reviewedFindings = [];

        for (const f of originalFindings) {
            const review = reportState.findings[f.id] || {};
            const { screenshot, ...findingWithoutBase64 } = f;
            const annotations = review.annotations || [];

            const result = {
                ...findingWithoutBase64,
                human_review: {
                    confirmed: review.confirmed,
                    severity_override: review.severity || null,
                    notes: review.notes || '',
                    annotations: annotations,
                    reviewer: reportState.reviewer,
                    reviewed_at: new Date().toISOString()
                }
            };

            // Generate annotated screenshot if there are annotations
            if (annotations.length > 0) {
                try {
                    const tool = annotationTools.get(String(f.id));
                    const thumb = document.querySelector(`[data-finding-id="${f.id}"] .thumbnail`);
                    let dataUrl = null;
                    if (tool && typeof tool.getMergedDataURL === 'function') {
                        dataUrl = await tool.getMergedDataURL();
                    } else if (thumb) {
                        dataUrl = await mergeImageAndAnnotations(thumb, annotations);
                    }
                    if (!dataUrl && thumb) {
                        const fallbackW = thumb.naturalWidth || 1920;
                        const fallbackH = thumb.naturalHeight || 1080;
                        dataUrl = await annotationsToPng(annotations, fallbackW, fallbackH);
                    }
                    // Extract base64 data (remove data:image/png;base64, prefix)
                    if (dataUrl && dataUrl.startsWith('data:image')) {
                        const base64Data = dataUrl.split(',')[1];
                        const filename = baseName + '_' + f.timestamp_formatted.replace(':', '-') + '_' + f.category + '_annotated.png';
                        annotatedFolder.file(filename, base64Data, {base64: true});
                        result.screenshot_annotated = 'annotated/' + filename;
                    }
                } catch (e) {
                    console.error('Failed to generate annotated screenshot for finding', f.id, e);
                }
            }

            // Keep original screenshot path reference (not base64)
            if (f.screenshot_path) {
                result.screenshot_original = f.screenshot_path;
            }

            reviewedFindings.push(result);
        }

        const output = {
            video: document.body.dataset.videoName,
            reviewed_at: new Date().toISOString(),
            reviewer: reportState.reviewer,
            findings: reviewedFindings
        };

        const reviewedJsonName = 'report_reviewed_' + baseName + '.json';
        const todoFilename = 'TODO_' + baseName + '.md';
        const todoMarkdown = buildTodoMarkdown(originalFindings, videoName, reportState.reviewer);

        zip.file(reviewedJsonName, JSON.stringify(output, null, 2));
        zip.file(todoFilename, todoMarkdown);

        // Generate and download ZIP
        const zipFilename = baseName + '_review.zip';

        const blob = await zip.generateAsync({type: 'blob'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = zipFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showNotification(i18n[currentLang].zipExported + ' ' + zipFilename);

        try {
            localStorage.removeItem('screenscribe_draft_' + reportState.reportId);
        } catch (e) {}
        reportState.modified = false;

    } catch (e) {
        console.error('ZIP export failed:', e);
        showNotification(i18n[currentLang].zipError + ' ' + e.message);
    }
}

function seekToTimestamp(seconds) {
    if (window.player) {
        window.player.seekTo(seconds);
    }
}

function exportTodoList() {
    const originalFindings = JSON.parse(document.getElementById('original-findings').textContent);
    const videoName = document.body.dataset.videoName || 'report';
    const reviewer = reportState.reviewer || 'Anonymous';
    const baseName = videoName.replace(/\.[^.]+$/, '');
    const md = buildTodoMarkdown(originalFindings, videoName, reviewer);

    // Download
    const filename = 'TODO_' + baseName + '.md';
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Copy path to clipboard
    const downloadPath = '~/Downloads/' + filename;
    navigator.clipboard.writeText(downloadPath).then(() => {
        showNotification(i18n[currentLang].exportDone + ' ' + downloadPath);
    }).catch(() => {
        showNotification(i18n[currentLang].exportDoneSimple + ' ' + filename);
    });
}

function showNotification(msg) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) toast.remove();
    }, 3000);
}

// Tab switching
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Update buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            const targetContent = document.getElementById('tab-' + tabId);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}

// Transcript drawer toggle
function toggleDrawer() {
    const drawer = document.getElementById('transcriptDrawer');
    if (drawer) {
        drawer.classList.toggle('open');
        const arrow = drawer.querySelector('.drawer-toggle');
        if (arrow) {
            arrow.textContent = drawer.classList.contains('open') ? '▲' : '▼';
        }
    }
}

// i18n translations
const i18n = {
    pl: {
        summary: 'Podsumowanie',
        findings: 'Znaleziska',
        stats: 'Statystyki',
        transcript: 'Transkrypcja',
        searchTranscript: 'Szukaj w transkrypcji...',
        noSubtitle: 'Brak napisu',
        total: 'Razem',
        critical: 'Krytyczne',
        high: 'Wysokie',
        medium: 'Srednie',
        low: 'Niskie',
        executiveSummary: 'Streszczenie',
        noSummary: 'Brak podsumowania AI',
        pipelineErrors: 'Bledy Pipeline',
        review: 'Recenzja',
        confirmed: 'Potwierdzone?',
        yes: 'Tak',
        noFalseAlarm: 'Nie / Falszy alarm',
        changePriority: 'Zmien priorytet',
        noChange: '-- Bez zmian --',
        notes: 'Notatki / Akcje',
        notesPlaceholder: 'Twoje uwagi, akcje do podjęcia...',
        reviewer: 'Recenzent:',
        reviewerPlaceholder: 'Twoje imie',
        embedScreenshots: 'Embeduj screenshoty (audyt zewn.)',
        exportJson: 'Eksportuj JSON',
        exportTodo: 'Eksportuj TODO',
        exportDone: 'Eksport ukonczony. Sciezka skopiowana:',
        exportDoneSimple: 'Eksport ukonczony:',
        enterName: 'Podaj swoje imie przed eksportem',
        noReviewed: 'Nie przejrzano zadnych znalezisk. Eksportowac mimo to?',
        draftRestored: 'Przywrocono wersje robocza',
        draftSaved: 'Zapisano wersje robocza',
        affectedComponents: 'Dotknięte komponenty',
        suggestedFix: 'Sugerowana poprawka',
        visualIssues: 'Wizualne problemy',
        clickToSeek: 'Kliknij aby przejsc do tego momentu',
        aiSuggestions: 'Sugestie AI:',
        exportZip: 'Eksportuj ZIP',
        exportZipTitle: 'ZIP z adnotowanymi zdjeciami',
        generatingZip: 'Generowanie ZIP...',
        zipExported: 'ZIP wyeksportowany:',
        zipError: 'Blad eksportu ZIP:'
    },
    en: {
        summary: 'Summary',
        findings: 'Findings',
        stats: 'Statistics',
        transcript: 'Transcript',
        searchTranscript: 'Search transcript...',
        noSubtitle: 'No subtitle',
        total: 'Total',
        critical: 'Critical',
        high: 'High',
        medium: 'Medium',
        low: 'Low',
        executiveSummary: 'Executive Summary',
        noSummary: 'No AI summary available',
        pipelineErrors: 'Pipeline Errors',
        review: 'Review',
        confirmed: 'Confirmed?',
        yes: 'Yes',
        noFalseAlarm: 'No / False alarm',
        changePriority: 'Change priority',
        noChange: '-- No change --',
        notes: 'Notes / Actions',
        notesPlaceholder: 'Your notes, actions to take...',
        reviewer: 'Reviewer:',
        reviewerPlaceholder: 'Your name',
        embedScreenshots: 'Embed screenshots (external audit)',
        exportJson: 'Export JSON',
        exportTodo: 'Export TODO',
        exportDone: 'Export complete. Path copied:',
        exportDoneSimple: 'Export complete:',
        enterName: 'Enter your name before export',
        noReviewed: 'No findings reviewed. Export anyway?',
        draftRestored: 'Draft restored',
        draftSaved: 'Draft saved',
        affectedComponents: 'Affected components',
        suggestedFix: 'Suggested fix',
        visualIssues: 'Visual issues',
        clickToSeek: 'Click to jump to this moment',
        aiSuggestions: 'AI Suggestions:',
        exportZip: 'Export ZIP',
        exportZipTitle: 'ZIP with annotated screenshots',
        generatingZip: 'Generating ZIP...',
        zipExported: 'ZIP exported:',
        zipError: 'ZIP export error:'
    }
};

let currentLang = 'pl';

function setLanguage(lang) {
    if (!i18n[lang]) return;
    currentLang = lang;

    // Update toggle buttons
    document.querySelectorAll('.lang-toggle button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    // Update all i18n elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (i18n[lang][key]) {
            if (el.tagName === 'INPUT' && el.placeholder) {
                el.placeholder = i18n[lang][key];
            } else {
                el.textContent = i18n[lang][key];
            }
        }
        // Handle title attribute
        const titleKey = el.dataset.i18nTitle;
        if (titleKey && i18n[lang][titleKey]) {
            el.title = i18n[lang][titleKey];
        }
    });

    // Update tab buttons with count preservation
    document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
        const tab = btn.dataset.tab;
        if (tab === 'summary') btn.textContent = i18n[lang].summary;
        if (tab === 'stats') btn.textContent = i18n[lang].stats;
        if (tab === 'findings') {
            const count = btn.textContent.match(/\((\d+)\)/);
            btn.textContent = i18n[lang].findings + (count ? ` (${count[1]})` : '');
        }
    });

    // Save preference
    try { localStorage.setItem('screenscribe_lang', lang); } catch(e) {}
}

function initLanguage() {
    // Check saved preference
    try {
        const saved = localStorage.getItem('screenscribe_lang');
        if (saved && i18n[saved]) {
            setLanguage(saved);
        }
    } catch(e) {}

    // Setup toggle buttons
    document.querySelectorAll('.lang-toggle button').forEach(btn => {
        btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
    });
}

// =============================================================================
// LIGHTBOX ANNOTATION TOOL (for fullscreen drawing)
// =============================================================================

const SVG_NS = 'http://www.w3.org/2000/svg';

function createSvgElement(tag, attrs = {}) {
    const el = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
            el.setAttribute(key, value);
        }
    });
    el.classList.add('annotation-shape');
    return el;
}

// Calculate actual visible image rect accounting for object-fit: contain
// Returns the rect of the actual image content, not the IMG element box
function getActualImageRect(img) {
    const elemRect = img.getBoundingClientRect();
    const naturalW = img.naturalWidth || img.width;
    const naturalH = img.naturalHeight || img.height;

    if (!naturalW || !naturalH || !elemRect.width || !elemRect.height) {
        return elemRect;
    }

    const elemAspect = elemRect.width / elemRect.height;
    const imgAspect = naturalW / naturalH;

    let actualWidth, actualHeight, offsetX, offsetY;

    if (imgAspect > elemAspect) {
        // Image is wider than container - letterboxing (bars top/bottom)
        actualWidth = elemRect.width;
        actualHeight = elemRect.width / imgAspect;
        offsetX = 0;
        offsetY = (elemRect.height - actualHeight) / 2;
    } else {
        // Image is taller than container - pillarboxing (bars left/right)
        actualHeight = elemRect.height;
        actualWidth = elemRect.height * imgAspect;
        offsetX = (elemRect.width - actualWidth) / 2;
        offsetY = 0;
    }

    return {
        left: elemRect.left + offsetX,
        top: elemRect.top + offsetY,
        width: actualWidth,
        height: actualHeight,
        right: elemRect.left + offsetX + actualWidth,
        bottom: elemRect.top + offsetY + actualHeight
    };
}

function normalizeRect(ann) {
    const x1 = ann.x;
    const y1 = ann.y;
    const x2 = ann.x + ann.width;
    const y2 = ann.y + ann.height;
    const left = Math.min(x1, x2);
    const top = Math.min(y1, y2);
    const right = Math.max(x1, x2);
    const bottom = Math.max(y1, y2);
    return {
        x: left,
        y: top,
        width: right - left,
        height: bottom - top
    };
}

function createAnnotationElement(ann) {
    if (!ann) return null;
    const stroke = ann.color || '#ff0066';
    // Use strokeWidthPx for export (denormalized) or strokeWidthRel for live rendering
    const strokeWidth = ann.strokeWidthPx || Math.max(0.0005, ann.strokeWidthRel || 0.003);
    // Arrow head length: use pixels if available, otherwise normalized
    const headLenNorm = ann.strokeWidthPx ? Math.max(20, ann.strokeWidthPx * 3) : 0.02;

    if (ann.type === 'rect') {
        const rectData = normalizeRect(ann);
        return createSvgElement('rect', {
            x: rectData.x,
            y: rectData.y,
            width: rectData.width,
            height: rectData.height,
            stroke,
            'stroke-width': strokeWidth,
            fill: 'none'
        });
    }

    if (ann.type === 'pen' && Array.isArray(ann.points) && ann.points.length >= 1) {
        const d = ann.points.map((p, idx) => `${idx === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
        return createSvgElement('path', {
            d,
            stroke,
            'stroke-width': strokeWidth,
            fill: 'none'
        });
    }

    if (ann.type === 'arrow') {
        const dx = ann.endX - ann.startX;
        const dy = ann.endY - ann.startY;
        const len = Math.sqrt(dx * dx + dy * dy) || 0.001;
        // Head length: 15-25% of arrow length, minimum based on stroke width
        const minHead = strokeWidth * 3;
        const headLength = Math.max(minHead, Math.min(len * 0.25, len * 0.15 + minHead));
        const angle = Math.atan2(dy, dx);
        const hx1 = ann.endX - headLength * Math.cos(angle - Math.PI / 7);
        const hy1 = ann.endY - headLength * Math.sin(angle - Math.PI / 7);
        const hx2 = ann.endX - headLength * Math.cos(angle + Math.PI / 7);
        const hy2 = ann.endY - headLength * Math.sin(angle + Math.PI / 7);

        const group = document.createElementNS(SVG_NS, 'g');
        const line = createSvgElement('line', {
            x1: ann.startX,
            y1: ann.startY,
            x2: ann.endX,
            y2: ann.endY,
            stroke,
            'stroke-width': strokeWidth,
            fill: 'none'
        });
        const head = createSvgElement('path', {
            d: `M${ann.endX},${ann.endY} L${hx1},${hy1} M${ann.endX},${ann.endY} L${hx2},${hy2}`,
            stroke,
            'stroke-width': strokeWidth,
            fill: 'none'
        });
        group.appendChild(line);
        group.appendChild(head);
        return group;
    }

    return null;
}

function renderAnnotationsToSvg(svg, annotations, renderWidth = 1, renderHeight = 1) {
    if (!svg || !renderWidth || !renderHeight) return;
    while (svg.firstChild) {
        svg.firstChild.remove();
    }
    svg.setAttribute('viewBox', `0 0 ${renderWidth} ${renderHeight}`);
    // Use 'none' to stretch normalized (0-1) coordinates to full container dimensions
    // 'meet' would preserve aspect ratio causing position drift on resize
    svg.setAttribute('preserveAspectRatio', 'none');

    const group = document.createElementNS(SVG_NS, 'g');
    (annotations || []).forEach(ann => {
        const el = createAnnotationElement(ann);
        if (el) group.appendChild(el);
    });
    svg.appendChild(group);
}

function serializeAnnotationsToSvg(annotations, baseWidth, baseHeight) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('xmlns', SVG_NS);
    svg.setAttribute('viewBox', `0 0 ${baseWidth} ${baseHeight}`);
    svg.setAttribute('width', baseWidth);
    svg.setAttribute('height', baseHeight);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    renderAnnotationsToSvg(svg, annotations, baseWidth, baseHeight);
    const serializer = new XMLSerializer();
    return serializer.serializeToString(svg);
}

function denormalizeAnnotations(annotations, targetWidth, targetHeight) {
    if (!annotations || !targetWidth || !targetHeight) return [];
    const scale = Math.max(targetWidth, targetHeight);
    return annotations.map(ann => {
        const strokeWidthPx = (ann.strokeWidthRel || 0.003) * scale;
        if (ann.type === 'rect') {
            return {
                ...ann,
                x: (ann.x || 0) * targetWidth,
                y: (ann.y || 0) * targetHeight,
                width: (ann.width || 0) * targetWidth,
                height: (ann.height || 0) * targetHeight,
                strokeWidthPx
            };
        }
        if (ann.type === 'arrow') {
            return {
                ...ann,
                startX: (ann.startX || 0) * targetWidth,
                startY: (ann.startY || 0) * targetHeight,
                endX: (ann.endX || 0) * targetWidth,
                endY: (ann.endY || 0) * targetHeight,
                strokeWidthPx
            };
        }
        if (ann.type === 'pen' && Array.isArray(ann.points)) {
            return {
                ...ann,
                points: ann.points.map(p => ({
                    x: (p.x || 0) * targetWidth,
                    y: (p.y || 0) * targetHeight
                })),
                strokeWidthPx
            };
        }
        return { ...ann, strokeWidthPx };
    });
}

function drawSvgMarkupOnCanvas(ctx, svgMarkup, width, height) {
    return new Promise((resolve, reject) => {
        const blob = new Blob([svgMarkup], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
            try {
                ctx.drawImage(img, 0, 0, width, height);
                URL.revokeObjectURL(url);
                resolve();
            } catch (e) {
                URL.revokeObjectURL(url);
                reject(e);
            }
        };
        img.onerror = (e) => {
            URL.revokeObjectURL(url);
            reject(e);
        };
        img.src = url;
    });
}

async function annotationsToPng(annotations, baseWidth, baseHeight) {
    if (!baseWidth || !baseHeight) return null;
    const canvas = document.createElement('canvas');
    canvas.width = baseWidth;
    canvas.height = baseHeight;
    const ctx = canvas.getContext('2d');
    try {
        const annPx = denormalizeAnnotations(annotations, baseWidth, baseHeight);
        const svgMarkup = serializeAnnotationsToSvg(annPx, baseWidth, baseHeight);
        await drawSvgMarkupOnCanvas(ctx, svgMarkup, baseWidth, baseHeight);
        return canvas.toDataURL('image/png');
    } catch (e) {
        console.warn('annotationsToPng failed:', e);
        return null;
    }
}

async function mergeImageAndAnnotations(imgEl, annotations) {
    if (!imgEl || !annotations || annotations.length === 0) return null;
    const baseWidth = imgEl.naturalWidth || imgEl.videoWidth || imgEl.width || 1920;
    const baseHeight = imgEl.naturalHeight || imgEl.videoHeight || imgEl.height || 1080;
    const annPixels = denormalizeAnnotations(annotations, baseWidth, baseHeight);

    const canvas = document.createElement('canvas');
    canvas.width = baseWidth;
    canvas.height = baseHeight;
    const ctx = canvas.getContext('2d');

    try {
        if (!imgEl.complete && imgEl.decode) {
            await imgEl.decode();
        }
        ctx.drawImage(imgEl, 0, 0, baseWidth, baseHeight);
    } catch (e) {
        console.warn('mergeImageAndAnnotations: base image draw failed, using annotations only', e);
        return await annotationsToPng(annotations, baseWidth, baseHeight);
    }

    try {
        const svgMarkup = serializeAnnotationsToSvg(annPixels, baseWidth, baseHeight);
        await drawSvgMarkupOnCanvas(ctx, svgMarkup, baseWidth, baseHeight);
    } catch (e) {
        console.warn('mergeImageAndAnnotations: overlay draw failed', e);
    }

    try {
        return canvas.toDataURL('image/png');
    } catch (e) {
        console.warn('mergeImageAndAnnotations: toDataURL failed, fallback to annotations-only', e);
        return await annotationsToPng(annotations, baseWidth, baseHeight);
    }
}

class LightboxAnnotationTool {
    constructor(svg, img, toolbar, findingId) {
        this.svg = svg;
        this.img = img;
        this.toolbar = toolbar;
        this.findingId = findingId;

        this.tool = null;
        this.color = '#ff0066';
        // Stroke width in viewBox units (0-1), ~0.8% of image dimension
        this.strokeWidth = 0.008;
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.annotations = [];
        this.currentPath = [];
        this.draftEl = null;
        this.baseWidth = img.naturalWidth || img.width || 1920;
        this.baseHeight = img.naturalHeight || img.height || 1080;
        this.resizeObserver = null;
        this.boundHandlers = [];

        this.init();
    }

    init() {
        this.syncOverlaySize();
        this.bindEvents();
        this.loadAnnotations();
        renderAnnotationsToSvg(this.svg, this.annotations, 1, 1);
        // Don't auto-select tool - user must click toolbar to start drawing
        // This prevents accidental annotations when just viewing
    }

    bindEvents() {
        // Tool selection
        this.toolbar.querySelectorAll('.tool-btn').forEach(btn => {
            const handler = (e) => {
                e.stopPropagation();
                this.selectTool(btn.dataset.tool);
            };
            btn.addEventListener('click', handler);
            this.boundHandlers.push({ target: btn, event: 'click', handler });
        });

        // Color picker
        const colorPicker = this.toolbar.querySelector('.color-picker');
        const colorClick = (e) => e.stopPropagation();
        const colorInput = (e) => { this.color = e.target.value; };
        colorPicker.addEventListener('click', colorClick);
        colorPicker.addEventListener('input', colorInput);
        this.boundHandlers.push({ target: colorPicker, event: 'click', handler: colorClick });
        this.boundHandlers.push({ target: colorPicker, event: 'input', handler: colorInput });

        // Undo/Clear
        const undoBtn = this.toolbar.querySelector('.undo-btn');
        const clearBtn = this.toolbar.querySelector('.clear-btn');
        const undoHandler = (e) => { e.stopPropagation(); this.undo(); };
        const clearHandler = (e) => { e.stopPropagation(); this.clear(); };
        undoBtn.addEventListener('click', undoHandler);
        clearBtn.addEventListener('click', clearHandler);
        this.boundHandlers.push({ target: undoBtn, event: 'click', handler: undoHandler });
        this.boundHandlers.push({ target: clearBtn, event: 'click', handler: clearHandler });

        // Drawing events (pointer)
        const start = (e) => this.startDraw(e);
        const move = (e) => this.draw(e);
        const end = (e) => this.endDraw(e);
        this.svg.addEventListener('pointerdown', start);
        this.svg.addEventListener('pointermove', move);
        window.addEventListener('pointerup', end);
        this.boundHandlers.push({ target: this.svg, event: 'pointerdown', handler: start });
        this.boundHandlers.push({ target: this.svg, event: 'pointermove', handler: move });
        this.boundHandlers.push({ target: window, event: 'pointerup', handler: end });

        // Resize observer to keep overlay in sync with image size
        this.resizeObserver = new ResizeObserver(() => {
            this.syncOverlaySize();
            // Always render with normalized coordinates (1, 1) - CSS transform handles scaling
            renderAnnotationsToSvg(this.svg, this.annotations, 1, 1);
        });
        this.resizeObserver.observe(this.img);
    }

    selectTool(tool) {
        this.tool = this.tool === tool ? null : tool;
        this.toolbar.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === this.tool);
        });
        this.svg.classList.toggle('drawing', this.tool !== null);
    }

    syncOverlaySize() {
        // Use actual image rect to account for object-fit: contain
        const imgRect = getActualImageRect(this.img);
        const containerRect = this.img.parentElement.getBoundingClientRect();
        const offsetX = imgRect.left - containerRect.left;
        const offsetY = imgRect.top - containerRect.top;
        // Position SVG over the actual visible image area
        // viewBox is set by renderAnnotationsToSvg to 0 0 1 1 (normalized coordinates)
        this.svg.style.width = `${this.baseWidth}px`;
        this.svg.style.height = `${this.baseHeight}px`;
        this.svg.style.left = `${offsetX}px`;
        this.svg.style.top = `${offsetY}px`;
        const scaleX = imgRect.width / this.baseWidth;
        const scaleY = imgRect.height / this.baseHeight;
        this.svg.style.transformOrigin = 'top left';
        this.svg.style.transform = `scale(${scaleX}, ${scaleY})`;
    }

    getPosPct(e) {
        // Use actual image rect to account for object-fit: contain
        const rect = getActualImageRect(this.img);
        // Clamp to 0-1 range to prevent out-of-bounds annotations
        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
        return { x, y, w: rect.width, h: rect.height };
    }

    startDraw(e) {
        if (!this.tool) return;
        e.stopPropagation();
        this.isDrawing = true;
        this.svg.setPointerCapture(e.pointerId);
        const pos = this.getPosPct(e);
        this.startX = pos.x;
        this.startY = pos.y;
        this.startRectWidth = pos.w;
        this.startRectHeight = pos.h;
        if (this.tool === 'pen') {
            this.currentPath = [pos];
            this.draftEl = createAnnotationElement({
                type: 'pen',
                points: [{ x: pos.x, y: pos.y }],
                color: this.color,
                strokeWidthRel: this.strokeWidth
            });
        } else if (this.tool === 'rect') {
            this.draftEl = createAnnotationElement({
                type: 'rect',
                x: this.startX,
                y: this.startY,
                width: 0,
                height: 0,
                color: this.color,
                strokeWidthRel: this.strokeWidth
            });
        } else if (this.tool === 'arrow') {
            this.draftEl = createAnnotationElement({
                type: 'arrow',
                startX: this.startX,
                startY: this.startY,
                endX: this.startX,
                endY: this.startY,
                color: this.color,
                strokeWidthRel: this.strokeWidth
            });
        }
        if (this.draftEl) {
            this.draftEl.classList.add('draft');
            this.svg.appendChild(this.draftEl);
        }
    }

    draw(e) {
        if (!this.isDrawing || !this.tool || !this.draftEl) return;
        e.stopPropagation();
        const pos = this.getPosPct(e);
        const w = 1;
        const h = 1;

        if (this.tool === 'pen') {
            this.currentPath.push(pos);
            const pathAbs = this.currentPath.map(p => ({ x: p.x * w, y: p.y * h }));
            this.draftEl.setAttribute('d', pathAbs.map((p, idx) => `${idx === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' '));
            this.draftEl.setAttribute('stroke', this.color);
            this.draftEl.setAttribute('stroke-width', this.strokeWidth);
        } else if (this.tool === 'rect') {
            const rectData = normalizeRect({
                x: this.startX,
                y: this.startY,
                width: pos.x - this.startX,
                height: pos.y - this.startY
            });
            this.draftEl.setAttribute('x', rectData.x * w);
            this.draftEl.setAttribute('y', rectData.y * h);
            this.draftEl.setAttribute('width', rectData.width * w);
            this.draftEl.setAttribute('height', rectData.height * h);
            this.draftEl.setAttribute('stroke', this.color);
            this.draftEl.setAttribute('stroke-width', this.strokeWidth);
        } else if (this.tool === 'arrow') {
            const headLength = Math.max(0.02, this.strokeWidth * 0.002);
            const angle = Math.atan2((pos.y - this.startY) * h, (pos.x - this.startX) * w);
            const endXAbs = pos.x * w;
            const endYAbs = pos.y * h;
            const hx1 = endXAbs - headLength * Math.cos(angle - Math.PI / 7);
            const hy1 = endYAbs - headLength * Math.sin(angle - Math.PI / 7);
            const hx2 = endXAbs - headLength * Math.cos(angle + Math.PI / 7);
            const hy2 = endYAbs - headLength * Math.sin(angle + Math.PI / 7);
            const headPath = `M${endXAbs},${endYAbs} L${hx1},${hy1} M${endXAbs},${endYAbs} L${hx2},${hy2}`;
            const [line, head] = this.draftEl.children;
            if (line) {
                line.setAttribute('x1', this.startX * w);
                line.setAttribute('y1', this.startY * h);
                line.setAttribute('x2', endXAbs);
                line.setAttribute('y2', endYAbs);
                line.setAttribute('stroke', this.color);
                line.setAttribute('stroke-width', this.strokeWidth);
            }
            if (head) {
                head.setAttribute('d', headPath);
                head.setAttribute('stroke', this.color);
                head.setAttribute('stroke-width', this.strokeWidth);
            }
        }
    }

    endDraw(e) {
        if (!this.isDrawing || !this.tool) return;
        if (e) {
            e.stopPropagation();
            if (e.pointerId) {
                this.svg.releasePointerCapture(e.pointerId);
            }
        }

        const pos = e ? this.getPosPct(e) : { x: this.startX, y: this.startY, w: this.startRectWidth, h: this.startRectHeight };
        const strokeWidthRel = this.strokeWidth;

        if (this.tool === 'pen' && this.currentPath.length > 1) {
            const normPoints = this.currentPath.map(p => ({ x: p.x, y: p.y }));
            this.annotations.push({
                type: 'pen',
                points: normPoints,
                color: this.color,
                strokeWidthRel
            });
        } else if (this.tool === 'rect') {
            const w = pos.x - this.startX;
            const h = pos.y - this.startY;
            // Minimum size: 1% of image dimension (coordinates are normalized 0-1)
            if (Math.abs(w) > 0.01 && Math.abs(h) > 0.01) {
                this.annotations.push({
                    type: 'rect',
                    x: this.startX,
                    y: this.startY,
                    width: w,
                    height: h,
                    color: this.color,
                    strokeWidthRel
                });
            }
        } else if (this.tool === 'arrow') {
            const dx = pos.x - this.startX;
            const dy = pos.y - this.startY;
            // Minimum length: 2% of image diagonal (coordinates are normalized 0-1)
            if (Math.sqrt(dx*dx + dy*dy) > 0.02) {
                this.annotations.push({
                    type: 'arrow',
                    startX: this.startX,
                    startY: this.startY,
                    endX: pos.x,
                    endY: pos.y,
                    color: this.color,
                    strokeWidthRel
                });
            }
        }

        this.isDrawing = false;
        this.currentPath = [];
        if (this.draftEl && this.draftEl.parentNode) {
            this.draftEl.parentNode.removeChild(this.draftEl);
        }
        this.draftEl = null;
        renderAnnotationsToSvg(this.svg, this.annotations, 1, 1);
    }

    undo() {
        this.annotations.pop();
        renderAnnotationsToSvg(this.svg, this.annotations, 1, 1);
    }

    clear() {
        this.annotations = [];
        renderAnnotationsToSvg(this.svg, [], 1, 1);
    }

    saveAnnotations() {
        if (!this.findingId) return;
        if (!reportState.findings[this.findingId]) {
            reportState.findings[this.findingId] = {};
        }
        reportState.findings[this.findingId].annotations = [...this.annotations];
        reportState.modified = true;
    }

    loadAnnotations() {
        if (!this.findingId) return;
        const state = reportState.findings[this.findingId];
        if (state && state.annotations) {
            this.annotations = [...state.annotations];
        }
    }

    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        this.boundHandlers.forEach(({ target, event, handler }) => {
            target.removeEventListener(event, handler);
        });
        this.boundHandlers = [];
        if (this.svg) {
            while (this.svg.firstChild) {
                this.svg.firstChild.remove();
            }
            this.svg.classList.remove('drawing');
        }
    }
}

// =============================================================================
// THUMBNAIL ANNOTATION TOOL (display-only, drawing happens in lightbox)
// =============================================================================

class AnnotationPreview {
    constructor(container) {
        this.container = container;
        this.findingId = container.dataset.findingId;
        this.img = container.querySelector('.thumbnail');
        this.svg = container.querySelector('.annotation-svg');
        this.annotations = [];
        this.baseWidth = 0;
        this.baseHeight = 0;
        this.resizeObserver = null;

        this.init();
    }

    init() {
        const onReady = () => {
            this.baseWidth = this.img.naturalWidth || this.img.width || 1920;
            this.baseHeight = this.img.naturalHeight || this.img.height || 1080;
            this.syncSvgSize();
            this.loadAnnotations();
            this.render();
            this.observe();
        };

        if (this.img.complete) {
            onReady();
        } else {
            this.img.onload = onReady;
        }
    }

    observe() {
        this.resizeObserver = new ResizeObserver(() => {
            this.syncSvgSize();
            this.render();
        });
        this.resizeObserver.observe(this.img);
    }

    syncSvgSize() {
        // Use actual image rect to account for object-fit: contain
        const imgRect = getActualImageRect(this.img);
        const containerRect = this.img.parentElement.getBoundingClientRect();
        const offsetX = imgRect.left - containerRect.left;
        const offsetY = imgRect.top - containerRect.top;
        // Position SVG over the actual visible image area
        // viewBox is set by render() to 0 0 1 1 (normalized coordinates)
        this.svg.style.width = `${this.baseWidth}px`;
        this.svg.style.height = `${this.baseHeight}px`;
        this.svg.style.left = `${offsetX}px`;
        this.svg.style.top = `${offsetY}px`;
        const scaleX = imgRect.width / this.baseWidth;
        const scaleY = imgRect.height / this.baseHeight;
        this.svg.style.transformOrigin = 'top left';
        this.svg.style.transform = `scale(${scaleX}, ${scaleY})`;
    }

    loadAnnotations() {
        const review = reportState.findings[this.findingId];
        if (review && review.annotations && review.annotations.length > 0) {
            this.annotations = review.annotations;
            this.container.classList.add('has-annotations');
        } else {
            this.annotations = [];
            this.container.classList.remove('has-annotations');
        }
    }

    render() {
        if (!this.baseWidth || !this.baseHeight) return;
        renderAnnotationsToSvg(this.svg, this.annotations, 1, 1);
    }

    async getMergedDataURL() {
        this.loadAnnotations();
        return await mergeImageAndAnnotations(this.img, this.annotations);
    }
}

// Global annotation tools map
const annotationTools = new Map();

function initAnnotationTools() {
    document.querySelectorAll('.annotation-container').forEach(container => {
        const findingId = container.dataset.findingId;
        if (!annotationTools.has(findingId)) {
            annotationTools.set(findingId, new AnnotationPreview(container));
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initReviewState();
    initTabs();
    initLanguage();
    initAnnotationTools();
});
