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

        // Click on video to toggle play/pause
        this.video.addEventListener('click', () => {
            this.video.paused ? this.video.play() : this.video.pause();
        });

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

        // Text is escaped via escapeHtml(), IDs and timestamps are numbers from trusted data
        // nosemgrep: insecure-document-method
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
