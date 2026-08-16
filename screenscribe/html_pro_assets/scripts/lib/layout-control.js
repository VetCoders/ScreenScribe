(function attachLayoutControl(root) {
    const namespace = root.ScreenScribeLib || {};

    function initShellLayout() {
        const header = root.document?.querySelector('.app-header');
        const documentElement = root.document?.documentElement;
        if (!header || !documentElement) return null;

        const syncHeaderHeight = () => {
            const height = Math.ceil(header.getBoundingClientRect().height);
            if (height > 0) {
                documentElement.style.setProperty('--header-height', `${height}px`);
            }
        };

        syncHeaderHeight();
        const observer = typeof root.ResizeObserver === 'function'
            ? new root.ResizeObserver(syncHeaderHeight)
            : null;
        observer?.observe(header);
        root.addEventListener?.('resize', syncHeaderHeight);

        return {
            refresh: syncHeaderHeight,
            destroy() {
                observer?.disconnect();
                root.removeEventListener?.('resize', syncHeaderHeight);
            },
        };
    }

    namespace.initShellLayout = initShellLayout;
    root.ScreenScribeLib = namespace;

    if (root.document?.querySelector('.app-header')) {
        initShellLayout();
    } else {
        root.document?.addEventListener('DOMContentLoaded', initShellLayout, { once: true });
    }
})(typeof window !== 'undefined' ? window : globalThis);
