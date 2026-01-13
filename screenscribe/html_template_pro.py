"""HTML Pro report template with video player and synchronized subtitles.

This module generates standalone HTML reports with:
- Hybrid Quantum/DOS + Vista design system
- Embedded video player with VTT subtitles
- Timestamp anchoring (click subtitle -> jump to video)
- CRT retro effects with professional accessibility
- Interactive human review functionality
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .transcribe import Segment

# =============================================================================
# HYBRID QUANTUM + VISTA CSS DESIGN SYSTEM
# =============================================================================

CSS_QUANTUM_VISTA = """
/* ==========================================================================
   QUANTUM/VISTA HYBRID DESIGN SYSTEM
   CRT retro aesthetics + Vista professional accessibility
   ========================================================================== */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    /* Quantum CRT Palette */
    --crt-black: #0a0a0a;
    --crt-dark: #121212;
    --phosphor-gray: #a8a8a8;
    --phosphor-green: #00ff64;
    --quantum-green: #00ff9d;
    --quantum-cyan: #00ffff;
    --quantum-purple: #c084fc;
    --quantum-amber: #f59e0b;

    /* Vista Brand Colors */
    --vista-mint: #a6c5bc;
    --vista-mint-light: #b7d6ce;
    --vista-mint-dark: #7da396;

    /* Semantic Colors (Vista) */
    --color-critical: #dc2626;
    --color-high: #ea580c;
    --color-medium: #ca8a04;
    --color-low: #16a34a;
    --color-success: #059669;
    --color-error: rgb(220 65 38 / 72%);

    /* Surface Colors */
    --surface-primary: #0d1117;
    --surface-elevated: #161b22;
    --surface-card: #1c2128;
    --surface-hover: #21262d;

    /* Text Hierarchy */
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --text-accent: var(--quantum-green);

    /* Border Colors */
    --border-default: #30363d;
    --border-accent: var(--vista-mint);
    --border-glow: color-mix(in srgb, var(--quantum-green) 40%, transparent);

    /* Typography */
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'JetBrains Mono', ui-monospace, monospace;

    /* Spacing */
    --space-xs: 0.25rem;
    --space-sm: 0.5rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;

    /* Radius */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-full: 9999px;

    /* Shadows with glow */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
    --shadow-md: 0 4px 8px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.5);
    --shadow-glow: 0 0 20px color-mix(in srgb, var(--quantum-green) 25%, transparent);

    /* Motion */
    --motion-fast: 150ms;
    --motion-medium: 250ms;
    --motion-slow: 400ms;
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

/* Reset */
*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; }

/* Base */
html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

body {
    font-family: var(--font-sans);
    background: var(--surface-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}

/* CRT Scanlines overlay */
body::before {
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.08) 50%);
    background-size: 100% 3px;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.4;
}

/* Subtle CRT flicker */
body::after {
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(18,16,16,0.03);
    pointer-events: none;
    z-index: 9998;
    animation: crtFlicker 0.15s infinite;
}

@keyframes crtFlicker {
    0%, 100% { opacity: 0.02; }
    50% { opacity: 0.04; }
}

/* ==========================================================================
   LAYOUT - Video left, Findings right (sticky with tabs)
   ========================================================================== */

.app-container {
    display: block;
    max-width: calc(100vw - 480px - 3 * var(--space-lg));  /* Leave space for fixed sidebar */
    margin: 0;
    margin-left: var(--space-lg);
    padding-top: 80px;  /* Space for fixed header */
    padding-bottom: 80px;  /* Space for fixed footer */
    min-height: 100vh;
    box-sizing: border-box;
}

@media (max-width: 1200px) {
    .app-container {
        max-width: 100%;
        margin: 0;
        padding: var(--space-md);
        padding-top: 80px;
        padding-bottom: 80px;
    }
    .sidebar {
        position: static !important;
        width: 100% !important;
        max-height: none !important;
        right: auto !important;
        top: auto !important;
        bottom: auto !important;
        margin-top: var(--space-lg);
    }
}

/* ==========================================================================
   TAB CONTENT (controlled by header tabs)
   ========================================================================== */

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

/* ==========================================================================
   TRANSCRIPT DRAWER (collapsible under video)
   ========================================================================== */

.transcript-drawer {
    background: var(--surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-top: var(--space-md);
}

.drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm) var(--space-md);
    background: var(--surface-card);
    cursor: pointer;
    user-select: none;
    transition: background var(--motion-fast);
}

.drawer-header:hover {
    background: var(--surface-hover);
}

.drawer-header h3 {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}

.drawer-toggle {
    color: var(--text-muted);
    transition: transform var(--motion-fast);
}

.transcript-drawer.open .drawer-toggle {
    transform: rotate(180deg);
}

.drawer-content {
    max-height: 0;
    overflow: hidden;
    transition: max-height var(--motion-medium) var(--ease-out);
}

.transcript-drawer.open .drawer-content {
    max-height: 400px;
}

.drawer-search {
    padding: var(--space-sm) var(--space-md);
    border-bottom: 1px solid var(--border-default);
}

.drawer-list {
    max-height: 350px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border-default) transparent;
}

/* ==========================================================================
   HEADER WITH INTEGRATED TABS
   ========================================================================== */

.app-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm) var(--space-lg);
    background: var(--surface-elevated);
    border-bottom: 1px solid var(--border-default);
    box-shadow: var(--shadow-md);
    gap: var(--space-lg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
}

.header-left {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    flex-shrink: 0;
}

.app-header h1 {
    font-size: 1.125rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    white-space: nowrap;
}

.app-header h1::before {
    content: ">";
    color: var(--quantum-green);
    font-family: var(--font-mono);
    animation: blink 1.2s step-end infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

.header-tabs {
    display: flex;
    gap: 2px;
    background: var(--surface-primary);
    padding: 3px;
    border-radius: var(--radius-sm);
    flex: 1;
    max-width: 400px;
    justify-content: center;
}

.header-tabs .tab-btn {
    flex: 1;
    padding: var(--space-xs) var(--space-md);
    background: transparent;
    border: none;
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    font-family: var(--font-sans);
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--motion-fast) var(--ease-out);
    white-space: nowrap;
}

.header-tabs .tab-btn:hover {
    color: var(--text-secondary);
    background: var(--surface-hover);
}

.header-tabs .tab-btn.active {
    background: var(--surface-card);
    color: var(--quantum-green);
    box-shadow: var(--shadow-sm);
}

.app-header .meta {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    flex-shrink: 0;
    text-align: right;
}

@media (max-width: 900px) {
    .app-header {
        flex-wrap: wrap;
    }
    .header-tabs {
        order: 3;
        max-width: none;
        width: 100%;
    }
}

/* Language toggle */
.lang-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    padding: 2px;
    margin-left: var(--space-md);
}

.lang-toggle button {
    padding: 4px 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.6875rem;
    font-weight: 600;
    cursor: pointer;
    border-radius: 4px;
    transition: all var(--motion-fast);
}

.lang-toggle button:hover {
    color: var(--text-secondary);
}

.lang-toggle button.active {
    background: var(--quantum-green);
    color: var(--crt-black);
}

/* ==========================================================================
   VIDEO PLAYER SECTION
   ========================================================================== */

.video-section {
    position: sticky;
    top: calc(var(--space-lg) + 60px); /* Below sticky header */
    align-self: start;
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    contain: layout;
    overflow: hidden;
    max-height: calc(100vh - 180px); /* Leave room for header + export bar */
}

.video-container {
    position: relative;
    background: var(--crt-black);
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border-default);
    box-shadow: var(--shadow-lg), var(--shadow-glow);
}

.video-container video {
    width: 100%;
    display: block;
    aspect-ratio: 16 / 9;
    object-fit: contain;
}

/* Current subtitle display below video */
.subtitle-display {
    padding: var(--space-md) var(--space-lg);
    background: var(--surface-elevated);
    border: 1px solid var(--border-default);
    border-top: none;
    border-radius: 0 0 var(--radius-lg) var(--radius-lg);
    min-height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.subtitle-display .current-text {
    font-size: 1rem;
    color: var(--text-primary);
    text-align: center;
    max-width: 80%;
    line-height: 1.4;
}

.subtitle-display .current-text.empty {
    color: var(--text-muted);
    font-style: italic;
}

/* ==========================================================================
   FINDINGS SECTION (Below video on main column)
   ========================================================================== */

.findings-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
}

.findings-section h2 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding-bottom: var(--space-sm);
    border-bottom: 1px solid var(--border-default);
}

/* ==========================================================================
   SIDEBAR - STICKY FINDINGS PANEL WITH TABS
   ========================================================================== */

.sidebar {
    position: fixed;
    top: 80px;  /* Below fixed header */
    right: var(--space-lg);
    bottom: 80px;  /* Above fixed footer */
    width: 480px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.sidebar-panel {
    background: var(--surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    flex: 1;
    max-height: 100%;
}

.sidebar-scroll {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: var(--space-md);
    scrollbar-width: thin;
    scrollbar-color: var(--border-default) transparent;
    contain: layout;
}

.sidebar-scroll::-webkit-scrollbar {
    width: 6px;
}

.sidebar-scroll::-webkit-scrollbar-track {
    background: transparent;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 3px;
}

.search-box {
    width: 100%;
    padding: var(--space-sm) var(--space-md);
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 0.875rem;
    transition: border-color var(--motion-fast) var(--ease-out);
}

.search-box:focus {
    outline: none;
    border-color: var(--vista-mint);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--vista-mint) 25%, transparent);
}

.search-box::placeholder {
    color: var(--text-muted);
}

/* Subtitle list */
.subtitle-list {
    max-height: 500px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border-default) transparent;
}

.subtitle-list::-webkit-scrollbar {
    width: 6px;
}

.subtitle-list::-webkit-scrollbar-track {
    background: transparent;
}

.subtitle-list::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 3px;
}

.subtitle-item {
    padding: var(--space-sm) var(--space-md);
    border-left: 3px solid transparent;
    cursor: pointer;
    transition: all var(--motion-fast) var(--ease-out);
    border-bottom: 1px solid color-mix(in srgb, var(--border-default) 50%, transparent);
}

.subtitle-item:hover {
    background: var(--surface-hover);
    border-left-color: var(--vista-mint);
}

.subtitle-item.active {
    background: color-mix(in srgb, var(--quantum-green) 10%, var(--surface-card));
    border-left-color: var(--quantum-green);
}

.subtitle-item .timestamp {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--quantum-green);
    margin-bottom: 2px;
}

.subtitle-item .text {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.3;
}

.subtitle-item.active .text {
    color: var(--text-primary);
}

/* ==========================================================================
   FINDING CARD
   ========================================================================== */

.finding {
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    border-left: 4px solid var(--border-default);
    transition: all var(--motion-fast) var(--ease-out);
}

.finding:hover {
    box-shadow: var(--shadow-md);
}

.finding[data-confirmed="true"] {
    border-left-color: var(--color-success);
}

.finding[data-confirmed="false"] {
    opacity: 0.6;
    border-left-color: var(--text-muted);
}

.finding-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-md);
    flex-wrap: wrap;
    gap: var(--space-sm);
}

.finding-title {
    font-weight: 600;
    font-size: 1rem;
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}

.finding-title .index {
    font-family: var(--font-mono);
    color: var(--quantum-green);
}

.finding-meta {
    font-size: 0.8125rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
    cursor: pointer;
    transition: color var(--motion-fast);
}

.finding-meta:hover {
    color: var(--quantum-cyan);
    text-decoration: underline;
}

/* Severity Badge */
.severity-badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    padding: var(--space-xs) var(--space-sm);
    border-radius: var(--radius-full);
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.severity-critical {
    background: color-mix(in srgb, var(--color-critical) 20%, transparent);
    color: #fca5a5;
    border: 1px solid color-mix(in srgb, var(--color-critical) 40%, transparent);
}

.severity-high {
    background: color-mix(in srgb, var(--color-high) 20%, transparent);
    color: #fdba74;
    border: 1px solid color-mix(in srgb, var(--color-high) 40%, transparent);
}

.severity-medium {
    background: color-mix(in srgb, var(--color-medium) 20%, transparent);
    color: #fde047;
    border: 1px solid color-mix(in srgb, var(--color-medium) 40%, transparent);
}

.severity-low {
    background: color-mix(in srgb, var(--color-low) 20%, transparent);
    color: #86efac;
    border: 1px solid color-mix(in srgb, var(--color-low) 40%, transparent);
}

.severity-none {
    background: var(--surface-hover);
    color: var(--text-secondary);
    border: 1px solid var(--border-default);
}

/* Finding content */
.finding-transcript {
    background: var(--surface-primary);
    border-radius: var(--radius-sm);
    padding: var(--space-md);
    margin-bottom: var(--space-md);
    font-style: italic;
    color: var(--text-secondary);
    border-left: 3px solid var(--border-accent);
    font-size: 0.9375rem;
}

.finding-summary {
    margin-bottom: var(--space-md);
    color: var(--text-primary);
}

.finding-details {
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.finding-details dt {
    font-weight: 600;
    color: var(--text-primary);
    margin-top: var(--space-sm);
}

.finding-details dd {
    margin: var(--space-xs) 0 0 0;
}

/* Screenshot thumbnail */
.finding-screenshot {
    margin-top: var(--space-md);
}

.thumbnail {
    max-width: 280px;
    border-radius: var(--radius-md);
    cursor: zoom-in;
    transition: all var(--motion-fast) var(--ease-out);
    border: 1px solid var(--border-default);
}

.thumbnail:hover {
    transform: scale(1.03);
    box-shadow: var(--shadow-lg), var(--shadow-glow);
    border-color: var(--vista-mint);
}

/* ==========================================================================
   ANNOTATION TOOL (Thumbnail - preview only)
   ========================================================================== */

.annotation-container {
    position: relative;
    display: inline-block;
    margin-top: var(--space-md);
    transform-origin: top left;
}

.annotation-container .thumbnail {
    display: block;
    margin-top: 0;
}

.annotation-svg {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
    border-radius: var(--radius-md);
}

.annotation-svg .annotation-shape,
.lightbox-annotation-svg .annotation-shape {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.annotation-hint {
    position: absolute;
    bottom: 8px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.7);
    color: var(--text-secondary);
    font-size: 0.7rem;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
    white-space: nowrap;
}

.annotation-container:hover .annotation-hint {
    opacity: 1;
}

/* Show indicator when annotations exist */
.annotation-container.has-annotations::after {
    content: '';
    position: absolute;
    top: 8px;
    right: 8px;
    width: 12px;
    height: 12px;
    background: var(--vista-mint);
    border-radius: 50%;
    border: 2px solid var(--bg-base);
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

/* ==========================================================================
   HUMAN REVIEW SECTION
   ========================================================================== */

.human-review {
    border-top: 1px dashed var(--border-default);
    margin-top: var(--space-lg);
    padding-top: var(--space-lg);
}

.human-review h4 {
    margin: 0 0 var(--space-md) 0;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
}

.review-row {
    display: flex;
    gap: var(--space-lg);
    flex-wrap: wrap;
    margin-bottom: var(--space-md);
}

.review-field {
    flex: 1;
    min-width: 200px;
}

.review-field label {
    display: block;
    font-size: 0.75rem;
    font-weight: 500;
    margin-bottom: var(--space-xs);
    color: var(--text-secondary);
}

.review-field select,
.review-field input[type="text"],
.review-field textarea {
    width: 100%;
    padding: var(--space-sm);
    background: var(--surface-primary);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 0.875rem;
    transition: border-color var(--motion-fast);
}

.review-field select:focus,
.review-field input[type="text"]:focus,
.review-field textarea:focus {
    outline: none;
    border-color: var(--vista-mint);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--vista-mint) 20%, transparent);
}

.review-field textarea {
    min-height: 80px;
    resize: vertical;
}

.ai-suggestions {
    font-size: 0.8rem;
    color: var(--text-secondary);
    background: var(--glass-subtle);
    padding: var(--space-sm);
    border-radius: var(--radius-sm);
    margin-bottom: var(--space-sm);
    border-left: 3px solid var(--vista-mint);
}

.radio-group {
    display: flex;
    gap: var(--space-md);
    padding-top: var(--space-xs);
}

.radio-group label {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.radio-group input[type="radio"] {
    accent-color: var(--vista-mint);
}

/* ==========================================================================
   LIGHTBOX
   ========================================================================== */

.lightbox {
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0, 0, 0, 0.95);
    z-index: 10000;
    justify-content: center;
    align-items: center;
    cursor: pointer;
}

.lightbox.active {
    display: flex;
}

.lightbox-content {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    max-width: 95%;
    max-height: 85%;
}

.lightbox img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: var(--radius-md);
}

.lightbox-annotation-svg {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
    border-radius: var(--radius-md);
}

.lightbox-annotation-svg.drawing {
    pointer-events: auto;
    cursor: crosshair;
    touch-action: none;
}

.lightbox-toolbar {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: var(--space-sm);
    align-items: center;
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-sm) var(--space-md);
    z-index: 10001;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.lightbox-toolbar .tool-btn {
    padding: var(--space-xs) var(--space-sm);
    background: var(--surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.15s ease;
}

.lightbox-toolbar .tool-btn:hover {
    background: var(--vista-mint-soft);
    border-color: var(--vista-mint);
}

.lightbox-toolbar .tool-btn.active {
    background: var(--vista-mint);
    color: var(--bg-base);
    border-color: var(--vista-mint);
}

.lightbox-toolbar .color-picker {
    width: 32px;
    height: 32px;
    padding: 0;
    border: 2px solid var(--border-default);
    border-radius: var(--radius-sm);
    cursor: pointer;
}

.lightbox-toolbar .undo-btn,
.lightbox-toolbar .clear-btn {
    padding: var(--space-xs) var(--space-sm);
    background: var(--surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.875rem;
}

.lightbox-toolbar .clear-btn {
    color: var(--severity-high);
}

.lightbox-toolbar .done-btn {
    padding: var(--space-xs) var(--space-md);
    background: var(--vista-mint);
    border: 1px solid var(--vista-mint);
    border-radius: var(--radius-sm);
    color: var(--bg-base);
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 600;
    margin-left: var(--space-sm);
}

.lightbox-toolbar .done-btn:hover {
    background: var(--vista-mint-dark);
}

.lightbox-close {
    position: fixed;
    top: 20px;
    right: 20px;
    width: 44px;
    height: 44px;
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid var(--border-default);
    border-radius: 50%;
    color: var(--text-primary);
    font-size: 28px;
    line-height: 1;
    cursor: pointer;
    z-index: 10002;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
}

.lightbox-close:hover {
    background: var(--severity-high);
    border-color: var(--severity-high);
    color: white;
}

/* ==========================================================================
   STATS CARDS
   ========================================================================== */

.stats {
    display: flex;
    gap: var(--space-md);
    flex-wrap: wrap;
    margin-bottom: var(--space-lg);
}

.stat-card {
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: var(--space-md) var(--space-lg);
    flex: 1;
    min-width: 120px;
}

.stat-card .label {
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: var(--space-xs);
}

.stat-card .value {
    font-size: 1.75rem;
    font-weight: 700;
    font-family: var(--font-mono);
}

.stat-card.critical .value { color: var(--color-critical); }
.stat-card.high .value { color: var(--color-high); }
.stat-card.medium .value { color: var(--color-medium); }
.stat-card.low .value { color: var(--color-low); }

/* ==========================================================================
   EXPORT BAR
   ========================================================================== */

.export-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--surface-elevated);
    border-top: 1px solid var(--border-default);
    padding: var(--space-md) var(--space-lg);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--space-md);
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
    z-index: 100;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
}

.export-options {
    display: flex;
    align-items: center;
    gap: var(--space-lg);
    flex-wrap: wrap;
}

.export-bar input[type="text"] {
    padding: var(--space-sm) var(--space-md);
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-family: var(--font-sans);
    width: 200px;
}

.export-bar input[type="text"]:focus {
    outline: none;
    border-color: var(--vista-mint);
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    font-size: 0.8125rem;
    color: var(--text-secondary);
    cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
    accent-color: var(--vista-mint);
    width: 16px;
    height: 16px;
}

.export-buttons {
    display: flex;
    gap: var(--space-sm);
}

.export-bar button {
    padding: var(--space-sm) var(--space-lg);
    background: var(--vista-mint);
    color: var(--crt-black);
    border: none;
    border-radius: var(--radius-sm);
    font-weight: 600;
    cursor: pointer;
    transition: all var(--motion-fast) var(--ease-out);
}

.export-bar button:hover {
    background: var(--vista-mint-light);
    box-shadow: var(--shadow-glow);
}

.export-bar button.btn-secondary {
    background: var(--surface-card);
    color: var(--text-primary);
    border: 1px solid var(--border-default);
}

.export-bar button.btn-secondary:hover {
    background: var(--surface-hover);
    border-color: var(--vista-mint);
}

/* ==========================================================================
   TOAST NOTIFICATIONS
   ========================================================================== */

.toast {
    position: fixed;
    bottom: 6rem;
    right: var(--space-lg);
    background: var(--surface-card);
    color: var(--text-primary);
    padding: var(--space-sm) var(--space-lg);
    border-radius: var(--radius-md);
    border: 1px solid var(--quantum-green);
    box-shadow: var(--shadow-lg), var(--shadow-glow);
    animation: toastSlide 3s ease forwards;
    z-index: 10001;
    font-size: 0.875rem;
}

@keyframes toastSlide {
    0% { opacity: 0; transform: translateX(100%); }
    10% { opacity: 1; transform: translateX(0); }
    90% { opacity: 1; transform: translateX(0); }
    100% { opacity: 0; transform: translateX(100%); }
}

/* ==========================================================================
   EXECUTIVE SUMMARY
   ========================================================================== */

.executive-summary {
    background: var(--surface-card);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
    border-left: 4px solid var(--vista-mint);
}

.executive-summary h3 {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-md);
}

.executive-summary p {
    color: var(--text-secondary);
    line-height: 1.7;
}

/* ==========================================================================
   ERRORS SECTION
   ========================================================================== */

.errors-section {
    background: color-mix(in srgb, var(--color-critical) 10%, var(--surface-card));
    border: 1px solid color-mix(in srgb, var(--color-critical) 30%, transparent);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
}

.errors-section h3 {
    color: #fca5a5;
    margin-bottom: var(--space-md);
    font-size: 1rem;
}

.errors-section ul {
    margin: 0;
    padding-left: var(--space-lg);
    color: var(--text-secondary);
}

/* ==========================================================================
   FOOTER
   ========================================================================== */

footer {
    grid-column: 1 / -1;
    text-align: center;
    padding: var(--space-lg) 0;
    color: var(--text-muted);
    font-size: 0.8125rem;
    font-family: var(--font-mono);
}

footer::before {
    content: "// ";
    color: var(--quantum-green);
}
"""

# =============================================================================
# JAVASCRIPT FOR VIDEO PLAYER WITH SUBTITLE SYNC
# =============================================================================

JS_VIDEO_PLAYER = """
class ScreenScribePlayer {
    constructor() {
        this.video = document.getElementById('videoPlayer');
        this.subtitleDisplay = document.getElementById('currentSubtitle');
        this.subtitleList = document.getElementById('subtitleList');
        this.searchBox = document.getElementById('subtitleSearch');

        this.segments = window.TRANSCRIPT_SEGMENTS || [];
        this.currentSegmentId = null;

        this.init();
    }

    init() {
        if (!this.video) return;

        // Video time update handler
        this.video.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.video.addEventListener('loadedmetadata', () => this.onMetadataLoaded());

        // Render subtitle list
        this.renderSubtitleList(this.segments);

        // Search functionality
        if (this.searchBox) {
            this.searchBox.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                const filtered = this.segments.filter(s =>
                    s.text.toLowerCase().includes(query)
                );
                this.renderSubtitleList(filtered);
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            if (e.code === 'Space') {
                e.preventDefault();
                this.video.paused ? this.video.play() : this.video.pause();
            }
            if (e.code === 'ArrowLeft') {
                e.preventDefault();
                this.video.currentTime -= 5;
            }
            if (e.code === 'ArrowRight') {
                e.preventDefault();
                this.video.currentTime += 5;
            }
        });
    }

    onMetadataLoaded() {
        console.log('Video loaded, duration:', this.video.duration);
    }

    onTimeUpdate() {
        const currentTime = this.video.currentTime;
        let activeSegment = null;

        for (const segment of this.segments) {
            if (currentTime >= segment.start && currentTime < segment.end) {
                activeSegment = segment;
                break;
            }
        }

        if (activeSegment && activeSegment.id !== this.currentSegmentId) {
            this.currentSegmentId = activeSegment.id;
            this.updateActiveHighlight(activeSegment.id);
            this.updateSubtitleDisplay(activeSegment.text);
        } else if (!activeSegment && this.currentSegmentId !== null) {
            this.currentSegmentId = null;
            this.clearActiveHighlight();
            this.updateSubtitleDisplay(null);
        }
    }

    updateSubtitleDisplay(text) {
        if (!this.subtitleDisplay) return;

        if (text) {
            this.subtitleDisplay.textContent = text;
            this.subtitleDisplay.classList.remove('empty');
        } else {
            this.subtitleDisplay.textContent = i18n[currentLang].noSubtitle;
            this.subtitleDisplay.classList.add('empty');
        }
    }

    updateActiveHighlight(segmentId) {
        document.querySelectorAll('.subtitle-item').forEach(item => {
            item.classList.remove('active');
        });

        const activeItem = document.querySelector(`[data-segment-id="${segmentId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
            activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    clearActiveHighlight() {
        document.querySelectorAll('.subtitle-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    renderSubtitleList(segments) {
        if (!this.subtitleList) return;

        this.subtitleList.innerHTML = segments.map(s => `
            <div class="subtitle-item" data-segment-id="${s.id}" onclick="player.seekTo(${s.start})">
                <div class="timestamp">${this.formatTime(s.start)} - ${this.formatTime(s.end)}</div>
                <div class="text">${this.escapeHtml(s.text)}</div>
            </div>
        `).join('');
    }

    seekTo(time) {
        if (!this.video) return;
        this.video.currentTime = time;
        this.video.play();
    }

    formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        return h > 0
            ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
            : `${m}:${String(s).padStart(2, '0')}`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global player instance
let player;
document.addEventListener('DOMContentLoaded', () => {
    player = new ScreenScribePlayer();
});
"""

JS_REVIEW_SCRIPT = """
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
                const combined = [state.notes, state.actionItems].filter(Boolean).join('\\n');
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
    const filename = 'report_reviewed.json';
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
                        const filename = f.timestamp_formatted.replace(':', '-') + '_' + f.category + '_annotated.png';
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

        // Add JSON to zip
        zip.file('report_reviewed.json', JSON.stringify(output, null, 2));

        // Generate and download ZIP
        const videoName = document.body.dataset.videoName || 'report';
        const zipFilename = videoName.replace(/\\.[^.]+$/, '') + '_review.zip';

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

    // Build markdown TODO list
    let md = `# TODO: ${videoName}\\n`;
    md += `> Recenzent: ${reviewer} | Data: ${new Date().toISOString().split('T')[0]}\\n\\n`;

    // Group by severity
    const bySeverity = { critical: [], high: [], medium: [], low: [] };

    originalFindings.forEach((f, idx) => {
        const review = reportState.findings[f.id] || {};
        const unified = f.unified_analysis || {};
        const severity = review.severity_override || unified.severity || 'medium';
        const confirmed = review.confirmed;

        // Skip if explicitly marked as false alarm
        if (confirmed === false) return;

        const checkbox = '[ ]';  // Always unchecked - these are TODOs to complete
        const summary = unified.summary || f.text || 'No description';
        const notes = review.notes || '';
        const actionItems = unified.action_items || [];

        let item = `- ${checkbox} **#${idx + 1}** [${severity.toUpperCase()}] ${summary}`;
        if (notes) item += `\\n  - 📝 ${notes}`;
        if (actionItems.length > 0) {
            item += `\\n  - Actions: ${actionItems.slice(0, 3).join(', ')}`;
        }

        if (bySeverity[severity]) {
            bySeverity[severity].push(item);
        } else {
            bySeverity.medium.push(item);
        }
    });

    // Output by severity
    if (bySeverity.critical.length > 0) {
        md += `## 🔴 Critical\\n${bySeverity.critical.join('\\n')}\\n\\n`;
    }
    if (bySeverity.high.length > 0) {
        md += `## 🟠 High\\n${bySeverity.high.join('\\n')}\\n\\n`;
    }
    if (bySeverity.medium.length > 0) {
        md += `## 🟡 Medium\\n${bySeverity.medium.join('\\n')}\\n\\n`;
    }
    if (bySeverity.low.length > 0) {
        md += `## 🟢 Low\\n${bySeverity.low.join('\\n')}\\n\\n`;
    }

    md += `---\\n_Generated by ScreenScribe Pro_\\n`;

    // Download
    const filename = 'TODO_' + videoName.replace(/\\.[^.]+$/, '') + '.md';
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
            const count = btn.textContent.match(/\\((\\d+)\\)/);
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
"""


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================


def _render_stats(findings: list[dict[str, Any]]) -> str:
    """Render severity statistics cards."""
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for f in findings:
        unified = f.get("unified_analysis", {})
        if unified.get("is_issue", True):
            severity = unified.get("severity", "medium")
            if severity in severity_counts:
                severity_counts[severity] += 1

    total = sum(severity_counts.values())

    return f"""
    <div class="stats">
        <div class="stat-card">
            <div class="label" data-i18n="total">Razem</div>
            <div class="value">{total}</div>
        </div>
        <div class="stat-card critical">
            <div class="label" data-i18n="critical">Krytyczne</div>
            <div class="value">{severity_counts["critical"]}</div>
        </div>
        <div class="stat-card high">
            <div class="label" data-i18n="high">Wysokie</div>
            <div class="value">{severity_counts["high"]}</div>
        </div>
        <div class="stat-card medium">
            <div class="label" data-i18n="medium">Srednie</div>
            <div class="value">{severity_counts["medium"]}</div>
        </div>
        <div class="stat-card low">
            <div class="label" data-i18n="low">Niskie</div>
            <div class="value">{severity_counts["low"]}</div>
        </div>
    </div>
    """


def _render_errors(errors: list[dict[str, str]]) -> str:
    """Render pipeline errors section."""
    if not errors:
        return ""

    lines = [
        '<div class="errors-section">',
        '<h3 data-i18n="pipelineErrors">Bledy Pipeline</h3>',
        "<ul>",
    ]

    for error in errors:
        stage = html.escape(error.get("stage", "unknown"))
        message = html.escape(error.get("message", ""))
        lines.append(f"<li><strong>{stage}:</strong> {message}</li>")

    lines.extend(["</ul>", "</div>"])
    return "\n".join(lines)


def _render_finding(f: dict[str, Any], index: int) -> str:
    """Render a single finding as an article element."""
    finding_id = f.get("id", index)
    category = f.get("category", "unknown")
    timestamp = f.get("timestamp_formatted", "00:00")
    timestamp_seconds = f.get("timestamp", 0)
    text = html.escape(f.get("text", ""))
    screenshot = f.get("screenshot", "")

    unified = f.get("unified_analysis", {})
    severity = unified.get("severity", "medium")
    summary = html.escape(unified.get("summary", ""))
    suggested_fix = html.escape(unified.get("suggested_fix", ""))
    affected_components = unified.get("affected_components", [])
    issues_detected = unified.get("issues_detected", [])
    action_items = unified.get("action_items", [])

    severity_class = f"severity-{severity}" if severity else "severity-none"

    details_html = ""
    if affected_components:
        components = ", ".join(html.escape(c) for c in affected_components)
        details_html += f"<dt>Dotknięte komponenty</dt><dd>{components}</dd>"
    if suggested_fix:
        details_html += f"<dt>Sugerowana poprawka</dt><dd>{suggested_fix}</dd>"
    if issues_detected:
        issues = "; ".join(html.escape(i) for i in issues_detected)
        details_html += f"<dt>Wizualne problemy</dt><dd>{issues}</dd>"

    screenshot_html = ""
    if screenshot:
        escaped_src = html.escape(screenshot)
        screenshot_html = f"""
        <div class="finding-screenshot">
            <div class="annotation-container" data-finding-id="{finding_id}">
                <img class="thumbnail" src="{escaped_src}" data-full="{escaped_src}"
                     alt="Screenshot @ {timestamp}" title="Kliknij aby powiekszye i adnotowac">
                <svg class="annotation-svg"></svg>
                <div class="annotation-hint">Kliknij aby adnotowac</div>
            </div>
        </div>
        """

    action_items_display = ", ".join(action_items) if action_items else ""

    return f"""
    <article class="finding" data-finding-id="{finding_id}" data-confirmed="">
        <div class="finding-header">
            <div>
                <span class="finding-title">
                    <span class="index">#{index}</span>
                    {html.escape(category.upper())}
                </span>
                <span class="finding-meta" onclick="seekToTimestamp({timestamp_seconds})"
                      title="Kliknij aby przejsc do tego momentu">@ {html.escape(timestamp)}</span>
            </div>
            <span class="severity-badge {severity_class}">{html.escape(severity)}</span>
        </div>

        <div class="finding-content">
            <div class="finding-transcript">{text}</div>
            {f'<div class="finding-summary"><strong>Podsumowanie:</strong> {summary}</div>' if summary else ""}
            <dl class="finding-details">
                {details_html}
            </dl>
            {screenshot_html}
        </div>

        <div class="human-review">
            <h4 data-i18n="review">Recenzja</h4>
            <div class="review-row">
                <div class="review-field">
                    <label data-i18n="confirmed">Potwierdzone?</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="confirmed-{finding_id}" value="true">
                            <span data-i18n="yes">Tak</span>
                        </label>
                        <label>
                            <input type="radio" name="confirmed-{finding_id}" value="false">
                            <span data-i18n="noFalseAlarm">Nie / Falszy alarm</span>
                        </label>
                    </div>
                </div>
                <div class="review-field">
                    <label data-i18n="changePriority">Zmien priorytet</label>
                    <select class="severity-select">
                        <option value="" data-i18n="noChange">-- Bez zmian --</option>
                        <option value="critical" data-i18n="critical">Krytyczny</option>
                        <option value="high" data-i18n="high">Wysoki</option>
                        <option value="medium" data-i18n="medium">Sredni</option>
                        <option value="low" data-i18n="low">Niski</option>
                    </select>
                </div>
            </div>
            <div class="review-field notes">
                <label data-i18n="notes">Notatki / Akcje</label>
                {f'<div class="ai-suggestions"><strong data-i18n="aiSuggestions">Sugestie AI:</strong> {html.escape(action_items_display)}</div>' if action_items_display else ''}
                <textarea placeholder="Twoje uwagi, akcje do podjęcia..." data-i18n="notesPlaceholder"></textarea>
            </div>
        </div>
    </article>
    """


def render_html_report_pro(
    video_name: str,
    video_path: str | None,
    generated_at: str,
    executive_summary: str,
    findings: list[dict[str, Any]],
    segments: list[Segment] | None = None,
    errors: list[dict[str, str]] | None = None,
    embed_video: bool = False,
) -> str:
    """Render complete HTML Pro report with video player and synchronized subtitles.

    Args:
        video_name: Name of the source video file
        video_path: Path to the video file (for embedding or reference)
        generated_at: ISO timestamp of report generation
        executive_summary: Executive summary text
        findings: List of finding dictionaries
        segments: Optional list of transcript segments for subtitle sync
        errors: Optional list of pipeline error dictionaries
        embed_video: Whether to embed video as base64 (for smaller files)

    Returns:
        Complete HTML document as string
    """
    errors = errors or []
    segments = segments or []

    # Generate unique report ID
    report_id = hashlib.sha256(f"{video_name}:{generated_at}".encode()).hexdigest()[:12]

    # Format timestamp
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        display_time = dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        display_time = generated_at

    # Video source handling
    # Use absolute path with file:// protocol for local files so browser can find them
    video_src = ""
    if video_path:
        video_path_obj = Path(video_path)
        if embed_video and video_path_obj.exists():
            size_mb = video_path_obj.stat().st_size / (1024 * 1024)
            if size_mb < 50:  # Only embed if < 50MB
                with open(video_path_obj, "rb") as vf:
                    video_b64 = base64.b64encode(vf.read()).decode("ascii")
                video_src = f"data:video/mp4;base64,{video_b64}"
            else:
                # Use absolute path for large files
                video_src = f"file://{video_path_obj.resolve()}"
        else:
            # Use absolute path so browser can locate the file
            if video_path_obj.exists():
                video_src = f"file://{video_path_obj.resolve()}"
            else:
                video_src = video_path

    # Generate VTT data URL for subtitles
    vtt_data_url = ""
    if segments:
        from .vtt_generator import generate_vtt_data_url

        vtt_data_url = generate_vtt_data_url(segments)

    # Segments as JSON for JavaScript
    segments_json = json.dumps(
        [{"id": s.id, "start": s.start, "end": s.end, "text": s.text} for s in segments],
        ensure_ascii=False,
    )

    # Build findings HTML
    findings_html = "\n".join(_render_finding(f, i + 1) for i, f in enumerate(findings))

    # Embed findings as JSON for export
    findings_json = json.dumps(findings, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScreenScribe Pro - {html.escape(video_name)}</title>
    <style>
{CSS_QUANTUM_VISTA}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
</head>
<body data-report-id="{report_id}" data-video-name="{html.escape(video_name)}">

    <div class="app-container">

        <header class="app-header">
            <div class="header-left">
                <h1>ScreenScribe Pro</h1>
            </div>
            <nav class="header-tabs">
                <button class="tab-btn active" data-tab="summary">Podsumowanie</button>
                <button class="tab-btn" data-tab="findings">Znaleziska ({len(findings)})</button>
                <button class="tab-btn" data-tab="stats">Statystyki</button>
            </nav>
            <div class="meta">
                {html.escape(video_name)} | {html.escape(display_time)}
                <div class="lang-toggle">
                    <button data-lang="pl" class="active">PL</button>
                    <button data-lang="en">EN</button>
                </div>
            </div>
        </header>

        <main class="video-section">
            <div class="video-container">
                <video id="videoPlayer" controls preload="metadata"
                       {f'src="{html.escape(video_src)}"' if video_src else ''}>
                    {f'<track kind="subtitles" src="{vtt_data_url}" srclang="pl" label="Polski" default>' if vtt_data_url else ''}
                    Twoja przegladarka nie obsluguje wideo HTML5.
                </video>
            </div>
            <div class="subtitle-display">
                <div id="currentSubtitle" class="current-text empty">Brak napisu</div>
            </div>

            <div class="transcript-drawer open" id="transcriptDrawer">
                <div class="drawer-header" onclick="toggleDrawer()">
                    <h3 data-i18n="transcript">Transkrypcja</h3>
                    <span class="drawer-toggle">▲</span>
                </div>
                <div class="drawer-content">
                    <div class="drawer-search">
                        <input type="text" id="subtitleSearch" class="search-box" placeholder="Szukaj w transkrypcji..." data-i18n="searchTranscript">
                    </div>
                    <div id="subtitleList" class="drawer-list"></div>
                </div>
            </div>
        </main>

        <aside class="sidebar">
            <div class="sidebar-panel">
                <div class="sidebar-scroll">
                    <div id="tab-summary" class="tab-content active">
                        {_render_errors(errors)}
                        {f'<div class="executive-summary"><h3 data-i18n="executiveSummary">Streszczenie</h3><p>{html.escape(executive_summary)}</p></div>' if executive_summary else '<p class="text-muted" data-i18n="noSummary">Brak podsumowania AI</p>'}
                    </div>
                    <div id="tab-findings" class="tab-content">
                        <section class="findings-section">
                            {findings_html}
                        </section>
                    </div>
                    <div id="tab-stats" class="tab-content">
                        {_render_stats(findings)}
                    </div>
                </div>
            </div>
        </aside>

        <div class="export-bar">
            <div class="export-options">
                <label><span data-i18n="reviewer">Recenzent:</span>
                    <input type="text" id="reviewer-name" placeholder="Twoje imie" data-i18n="reviewerPlaceholder">
                </label>
            </div>
            <div class="export-buttons">
                <button onclick="exportTodoList()" class="btn-secondary" data-i18n="exportTodo">Eksportuj TODO</button>
                <button onclick="exportReviewedJSON()" data-i18n="exportJson">Eksportuj JSON</button>
                <button onclick="exportReviewedZIP()" class="btn-primary" data-i18n="exportZip" data-i18n-title="exportZipTitle">Eksportuj ZIP</button>
            </div>
        </div>

    </div>

    <div id="lightbox" class="lightbox">
        <button type="button" class="lightbox-close" onclick="closeLightbox()" title="Zamknij (ESC)">&times;</button>
        <div class="lightbox-content" onclick="event.stopPropagation()">
            <img id="lightbox-img" src="" alt="Pelny rozmiar">
            <svg id="lightbox-svg" class="lightbox-annotation-svg"></svg>
        </div>
        <div id="lightbox-toolbar" class="lightbox-toolbar" style="display: none;" onclick="event.stopPropagation()">
            <button type="button" class="tool-btn" data-tool="pen">Pen</button>
            <button type="button" class="tool-btn" data-tool="rect">Rect</button>
            <button type="button" class="tool-btn" data-tool="arrow">Arrow</button>
            <input type="color" class="color-picker" value="#ff0066">
            <button type="button" class="undo-btn">Undo</button>
            <button type="button" class="clear-btn">Clear</button>
            <button type="button" class="done-btn" onclick="closeLightbox()">Done</button>
        </div>
    </div>

    <script id="original-findings" type="application/json">
{findings_json}
    </script>

    <script>
        window.TRANSCRIPT_SEGMENTS = {segments_json};
    </script>

    <script>
{JS_VIDEO_PLAYER}
    </script>

    <script>
{JS_REVIEW_SCRIPT}
    </script>

    <footer>
        Generated by ScreenScribe Pro | VetCoders 2025
    </footer>

</body>
</html>
"""
