function resizeIframe(iframe) {
    const adjustIframeHeight = () => {
        try {
            // Accessing the iframe's content document
            const body = iframe.contentWindow.document.body;
            // Get the total height of the body including all content
            const newHeight = body.scrollHeight;

            // Set the iframe height
            iframe.style.height = newHeight + 'px';
        } catch (e) {
            console.error("Error accessing iframe content:", e);
        }
    };

    // Adjust height when the iframe loads
    iframe.addEventListener('load', adjustIframeHeight);

    // Also adjust height on window resize
    window.addEventListener('resize', adjustIframeHeight);
}

// Ensure the script executes when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
        resizeIframe(iframe);
    });
});
