function resizeIframe(iframe) {
    const adjustIframeHeight = () => {
        // Calculate the new height of the iframe
        const newHeight = iframe.contentWindow.document.body.scrollHeight;
        
        // Set the iframe height
        iframe.style.height = newHeight + 'px';
    };

    // Initial height adjustment
    adjustIframeHeight();

    // Set up a MutationObserver to detect changes in the content
    const observer = new iframe.contentWindow.MutationObserver(() => {
        adjustIframeHeight();
    });

    // Observe changes in the entire document
    observer.observe(iframe.contentWindow.document.body, { childList: true, subtree: true });

    // Also listen for window resize events
    window.addEventListener('resize', adjustIframeHeight);

    // Clean up observer on iframe unload
    iframe.contentWindow.addEventListener('beforeunload', () => {
        observer.disconnect();
        window.removeEventListener('resize', adjustIframeHeight);
    });
}

// Ensure the script executes when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
        resizeIframe(iframe);
    });
});
